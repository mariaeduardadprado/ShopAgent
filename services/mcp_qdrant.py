# services/mcp_qdrant.py
"""
MCP Connector para o Qdrant.

Expõe operações de busca semântica como ferramentas
que os agentes podem chamar sem conhecer os detalhes
de embeddings ou da API do Qdrant.
"""

import os
from pydantic import BaseModel
from dotenv import load_dotenv
from rag.search_engine import MotorBuscaSemantica, ResultadoBusca

load_dotenv()


class AnaliseReviews(BaseModel):
    """Resultado estruturado de uma análise de reviews."""
    query_original: str
    total_reviews_analisados: int
    distribuicao_sentimento: dict[str, int]
    nota_media: float
    insights: str               # resposta do LLM
    reviews_de_suporte: list[dict]  # evidências usadas


class MCPQdrant:
    """
    Conector MCP para busca semântica no Qdrant.

    Encapsula o MotorBuscaSemantica e adiciona lógica
    de negócio específica para análise de e-commerce.
    """

    def __init__(self):
        # Motor já configura LlamaIndex internamente
        self.motor = MotorBuscaSemantica()
        print("✅ MCPQdrant conectado ao Qdrant")

    def analisar_reviews(
        self,
        query: str,
        top_k: int = 5,
        filtro_sentimento: str | None = None,
    ) -> AnaliseReviews:
        """
        Análise semântica completa de reviews.
        Retorna insights gerados pelo LLM + evidências.
        """
        resultado: ResultadoBusca = self.motor.buscar(
            query=query,
            top_k=top_k,
            filtro_sentimento=filtro_sentimento,
            modo="rag",
        )

        # Calcula distribuição de sentimento dos reviews retornados
        dist: dict[str, int] = {"positivo": 0, "negativo": 0, "neutro": 0}
        notas = []

        for r in resultado.reviews_encontrados:
            dist[r.sentimento] = dist.get(r.sentimento, 0) + 1
            notas.append(r.nota)

        nota_media = round(sum(notas) / len(notas), 2) if notas else 0.0

        reviews_suporte = [
            {
                "nota": r.nota,
                "sentimento": r.sentimento,
                "trecho": r.texto[:150] + "...",
                "relevancia": r.score,
            }
            for r in resultado.reviews_encontrados
        ]

        return AnaliseReviews(
            query_original=query,
            total_reviews_analisados=resultado.total_encontrados,
            distribuicao_sentimento=dist,
            nota_media=nota_media,
            insights=resultado.resposta_llm or "Sem resposta gerada.",
            reviews_de_suporte=reviews_suporte,
        )

    def buscar_reclamacoes(self, tema: str) -> AnaliseReviews:
        """Atalho para buscar especificamente reclamações sobre um tema."""
        return self.analisar_reviews(
            query=f"reclamações e problemas sobre {tema}",
            filtro_sentimento="negativo",
            top_k=5,
        )

    def buscar_elogios(self, tema: str) -> AnaliseReviews:
        """Atalho para buscar especificamente elogios sobre um tema."""
        return self.analisar_reviews(
            query=f"elogios e pontos positivos sobre {tema}",
            filtro_sentimento="positivo",
            top_k=5,
        )