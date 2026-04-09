# services/query_router.py
"""
QueryRouter: decide qual fonte de dados usar para cada pergunta.

Esta é a lógica mais crítica do sistema. Uma classificação errada
significa dar uma resposta errada ou incompleta ao usuário.

Estratégia em duas camadas:
1. Regras baseadas em palavras-chave (rápido, sem custo de API)
2. Fallback para o LLM classificar (mais inteligente, custa tokens)

Em produção: você pode treinar um classificador próprio (fine-tuning)
para reduzir custo e latência eliminando o fallback ao LLM.
"""

import re
from enum import Enum
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()


class TipoQuery(str, Enum):
    SQL        = "sql"         # dados estruturados: métricas, números
    SEMANTICO  = "semantico"   # texto livre: reviews, sentimentos
    HIBRIDO    = "hibrido"     # precisa dos dois
    INDEFINIDO = "indefinido"  # não entendeu — pede clarificação


class ResultadoClassificacao(BaseModel):
    tipo: TipoQuery
    confianca: float          # 0.0 a 1.0
    justificativa: str
    metodo: str               # "keywords" ou "llm"


# ── Palavras-chave por categoria ──────────────────────────────
# Quanto mais específico o termo, maior a confiança.
# Ordem importa: termos mais específicos primeiro.

KEYWORDS_SQL = [
    "faturamento", "receita", "vendas", "pedidos", "quantidade",
    "ticket médio", "ticket medio", "região", "regiao",
    "produto mais vendido", "top produto", "cancelamento",
    "evolução", "crescimento", "mensal", "comparar meses",
    "estoque", "quanto", "total", "média", "media",
    "percentual", "porcentagem", "%", "R$",
]

KEYWORDS_SEMANTICO = [
    "review", "avaliação", "avaliacao", "opinião", "opiniao",
    "reclamação", "reclamacao", "elogio", "feedback",
    "clientes dizem", "clientes falam", "clientes acham",  
    "clientes pensam", "o que acham", "o que dizem",        
    "satisfação", "satisfacao", "sentimento",
    "experiência", "experiencia", "prazo",
    "entrega", "qualidade", "atendimento", "suporte",
    "problema", "defeito", "insatisfeito", "feliz", "amei",
]

KEYWORDS_HIBRIDO = [
    "e também", "e tambem", "além disso", "alem disso",
    "combinar", "junto", "ao mesmo tempo",
    "vendas e reviews", "números e opinião",
    "desempenho e satisfação",
]


class QueryRouter:
    """
    Classifica perguntas e direciona para a fonte de dados correta.
    """

    def __init__(self):
        self.llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def classificar(self, pergunta: str) -> ResultadoClassificacao:
        """
        Ponto de entrada principal.
        Tenta classificar por keywords primeiro; usa LLM como fallback.
        """
        resultado = self._classificar_por_keywords(pergunta)

        # Se confiança alta → usa direto
        if resultado.confianca >= 0.7:
            return resultado

        # Confiança baixa → confirma com o LLM
        return self._classificar_com_llm(pergunta)

    def _classificar_por_keywords(self, pergunta: str) -> ResultadoClassificacao:
        """
        Classificação rápida por palavras-chave.
        Custo: zero. Latência: <1ms.
        """
        texto = pergunta.lower()

        # Remove pontuação para matching mais robusto
        texto_limpo = re.sub(r"[^\w\s]", " ", texto)

        hits_sql       = sum(1 for k in KEYWORDS_SQL       if k in texto_limpo)
        hits_semantico = sum(1 for k in KEYWORDS_SEMANTICO if k in texto_limpo)
        hits_hibrido   = sum(1 for k in KEYWORDS_HIBRIDO   if k in texto_limpo)

        total_hits = hits_sql + hits_semantico + hits_hibrido

        # Sem hits claros → confiança baixa, vai pro LLM
        if total_hits == 0:
            return ResultadoClassificacao(
                tipo=TipoQuery.INDEFINIDO,
                confianca=0.0,
                justificativa="Nenhuma palavra-chave identificada",
                metodo="keywords",
            )

        # Hibrido explícito
        if hits_hibrido > 0:
            return ResultadoClassificacao(
                tipo=TipoQuery.HIBRIDO,
                confianca=0.85,
                justificativa=f"Conectivos híbridos detectados ({hits_hibrido} hits)",
                metodo="keywords",
            )

        # Ambos os tipos presentes → híbrido implícito
        if hits_sql > 0 and hits_semantico > 0:
            return ResultadoClassificacao(
                tipo=TipoQuery.HIBRIDO,
                confianca=0.75,
                justificativa=f"SQL ({hits_sql} hits) + semântico ({hits_semantico} hits)",
                metodo="keywords",
            )

        # Predominância SQL
        if hits_sql > hits_semantico:
            confianca = min(0.95, 0.6 + hits_sql * 0.1)
            return ResultadoClassificacao(
                tipo=TipoQuery.SQL,
                confianca=confianca,
                justificativa=f"Termos SQL detectados: {hits_sql} hits",
                metodo="keywords",
            )

        # Predominância semântica
        confianca = min(0.95, 0.6 + hits_semantico * 0.1)
        return ResultadoClassificacao(
            tipo=TipoQuery.SEMANTICO,
            confianca=confianca,
            justificativa=f"Termos semânticos detectados: {hits_semantico} hits",
            metodo="keywords",
        )

    def _classificar_com_llm(self, pergunta: str) -> ResultadoClassificacao:
        """
        Classificação inteligente via LLM.
        Usada quando keywords não dão confiança suficiente.
        Custo: ~100 tokens. Latência: ~500ms.
        """
        prompt = f"""Você é um classificador de perguntas de e-commerce.

Classifique a pergunta abaixo em UMA das categorias:
- sql: pergunta sobre números, métricas, faturamento, pedidos, quantidade, regiões
- semantico: pergunta sobre reviews, opiniões, satisfação, reclamações, sentimentos
- hibrido: pergunta que precisa de dados numéricos E de reviews/opiniões
- indefinido: pergunta que não se encaixa ou é muito vaga

Responda APENAS com um JSON no formato:
{{"tipo": "sql|semantico|hibrido|indefinido", "justificativa": "motivo em uma frase"}}

Pergunta: {pergunta}"""

        try:
            resposta = self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,           # determinístico para classificação
                max_tokens=100,
                response_format={"type": "json_object"},
            )

            import json
            dados = json.loads(resposta.choices[0].message.content)
            tipo_str = dados.get("tipo", "indefinido")

            return ResultadoClassificacao(
                tipo=TipoQuery(tipo_str),
                confianca=0.90,          # LLM tem alta confiança
                justificativa=dados.get("justificativa", "Classificado pelo LLM"),
                metodo="llm",
            )

        except Exception as e:
            # Fallback seguro: trata como híbrido para não perder informação
            return ResultadoClassificacao(
                tipo=TipoQuery.HIBRIDO,
                confianca=0.5,
                justificativa=f"Erro na classificação LLM: {e} — usando híbrido como fallback",
                metodo="llm_fallback",
            )