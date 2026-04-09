# services/context_builder.py
"""
ContextBuilder: orquestra as chamadas MCP e monta o contexto
completo para o ReporterAgent gerar a resposta final.

É o único lugar do sistema que conhece TODOS os conectores.
Os agentes individuais não se falam — passam pelo ContextBuilder.
"""

from pydantic import BaseModel
from services.query_router import QueryRouter, TipoQuery
from services.mcp_supabase import MCPSupabase
from services.mcp_qdrant import MCPQdrant


class ContextoCompleto(BaseModel):
    """
    Contexto montado para o ReporterAgent.
    Contém tudo que o LLM precisa para gerar uma resposta completa.
    """
    pergunta_original: str
    tipo_query: str
    dados_sql: dict | None = None          # métricas do PostgreSQL
    dados_semanticos: dict | None = None   # análise de reviews
    erro: str | None = None


class ContextBuilder:
    """
    Orquestra os conectores MCP e monta o contexto para os agentes.
    """

    def __init__(self):
        self.router   = QueryRouter()
        self.supabase = MCPSupabase()
        self.qdrant   = MCPQdrant()
        print("✅ ContextBuilder inicializado")

    def construir(self, pergunta: str) -> ContextoCompleto:
        """
        Ponto de entrada: recebe pergunta, devolve contexto completo.
        """
        # 1. Classifica a pergunta
        classificacao = self.router.classificar(pergunta)

        print(f"\n🧭 Roteamento:")
        print(f"   Pergunta: '{pergunta}'")
        print(f"   Tipo: {classificacao.tipo} (confiança: {classificacao.confianca:.0%})")
        print(f"   Método: {classificacao.metodo}")
        print(f"   Motivo: {classificacao.justificativa}")

        contexto = ContextoCompleto(
            pergunta_original=pergunta,
            tipo_query=classificacao.tipo,
        )

        # 2. Consulta as fontes corretas
        try:
            if classificacao.tipo == TipoQuery.SQL:
                contexto.dados_sql = self._buscar_sql(pergunta)

            elif classificacao.tipo == TipoQuery.SEMANTICO:
                contexto.dados_semanticos = self._buscar_semantico(pergunta)

            elif classificacao.tipo == TipoQuery.HIBRIDO:
                # Busca os dois em sequência
                # Em produção: usar asyncio para buscar em paralelo
                contexto.dados_sql        = self._buscar_sql(pergunta)
                contexto.dados_semanticos = self._buscar_semantico(pergunta)

            else:
                contexto.erro = "Pergunta muito vaga. Tente ser mais específico."

        except Exception as e:
            contexto.erro = str(e)

        return contexto

    def _buscar_sql(self, pergunta: str) -> dict:
        """Busca dados estruturados no PostgreSQL."""
        print("   🗄️  Consultando PostgreSQL...")

        metricas  = self.supabase.get_metricas_gerais()
        por_regiao = self.supabase.get_vendas_por_regiao()
        top_prods  = self.supabase.get_top_produtos(5)
        evolucao   = self.supabase.get_evolucao_mensal()

        return {
            "metricas_gerais": metricas.model_dump(),
            "vendas_por_regiao": [r.model_dump() for r in por_regiao],
            "top_produtos": top_prods,
            "evolucao_mensal": evolucao,
        }

    def _buscar_semantico(self, pergunta: str) -> dict:
        """Busca dados semânticos no Qdrant."""
        print("   🔍 Consultando Qdrant...")

        analise = self.qdrant.analisar_reviews(pergunta, top_k=5)

        return {
            "insights": analise.insights,
            "nota_media": analise.nota_media,
            "distribuicao_sentimento": analise.distribuicao_sentimento,
            "reviews_de_suporte": analise.reviews_de_suporte,
        }