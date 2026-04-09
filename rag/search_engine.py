# rag/search_engine.py
"""
Motor de busca semântica sobre reviews.

Oferece dois modos:
1. Busca simples: retorna os reviews mais similares (recuperação pura)
2. Busca RAG: retorna uma resposta gerada pelo LLM com base nos reviews

Em produção: o modo RAG seria o padrão, mas o modo simples
é útil para debug e para casos onde você quer os dados brutos.
"""

import os
from typing import Literal
from pydantic import BaseModel
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from services.llama_config import configurar_llama

load_dotenv()


# ─────────────────────────────────────────────────────────────
# Modelos de resposta com Pydantic — tipagem forte
# Em produção: esses modelos seriam usados na API REST também
# ─────────────────────────────────────────────────────────────

class ReviewEncontrado(BaseModel):
    review_id: int
    produto_id: int
    nota: int
    sentimento: str
    texto: str
    score: float  # similaridade 0-1

class ResultadoBusca(BaseModel):
    query: str
    modo: Literal["simples", "rag"]
    reviews_encontrados: list[ReviewEncontrado]
    resposta_llm: str | None = None
    total_encontrados: int


class MotorBuscaSemantica:
    """
    Encapsula toda a lógica de busca semântica.

    Por que usar uma classe e não funções soltas?
    A conexão com o Qdrant e o índice são recursos caros de inicializar.
    Com uma classe, inicializamos UMA VEZ e reutilizamos em todas as buscas.
    """

    def __init__(self):
        configurar_llama()

        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333")
        )

        # Reconecta ao índice já existente no Qdrant
        # (não re-indexa — apenas aponta para a coleção existente)
        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=os.getenv("QDRANT_COLLECTION", "reviews"),
        )
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store
        )
        self.index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
        )

        print("✅ MotorBuscaSemantica inicializado")

    def buscar(
        self,
        query: str,
        top_k: int = 5,
        filtro_sentimento: str | None = None,
        modo: Literal["simples", "rag"] = "rag",
    ) -> ResultadoBusca:
        """
        Realiza busca semântica nos reviews.

        Args:
            query: pergunta em linguagem natural
            top_k: quantos reviews recuperar
            filtro_sentimento: "positivo", "negativo" ou "neutro"
            modo: "simples" retorna só os reviews, "rag" gera resposta
        """

        # ── Monta filtro por metadados (se necessário) ──
        # Isso combina busca vetorial + filtro SQL no Qdrant
        filtros = None
        if filtro_sentimento:
            filtros = Filter(
                must=[FieldCondition(
                    key="sentimento",
                    match=MatchValue(value=filtro_sentimento)
                )]
            )

        if modo == "simples":
            return self._busca_simples(query, top_k, filtros)
        else:
            return self._busca_rag(query, top_k, filtros)

    def _busca_simples(self, query, top_k, filtros) -> ResultadoBusca:
        """Retorna os K reviews mais similares sem gerar resposta."""

        retriever = self.index.as_retriever(
            similarity_top_k=top_k,
            vector_store_kwargs={"qdrant_filters": filtros} if filtros else {},
        )

        nodes = retriever.retrieve(query)
        reviews = []

        for node in nodes:
            reviews.append(ReviewEncontrado(
                review_id=node.metadata.get("review_id", 0),
                produto_id=node.metadata.get("produto_id", 0),
                nota=node.metadata.get("nota", 0),
                sentimento=node.metadata.get("sentimento", ""),
                texto=node.node.text,
                score=round(node.score or 0.0, 4),
            ))

        return ResultadoBusca(
            query=query,
            modo="simples",
            reviews_encontrados=reviews,
            total_encontrados=len(reviews),
        )

    def _busca_rag(self, query, top_k, filtros) -> ResultadoBusca:
        """Recupera reviews e gera resposta com o LLM."""

        # Query engine: combina retrieval + LLM em uma pipeline
        query_engine = self.index.as_query_engine(
            similarity_top_k=top_k,
            vector_store_kwargs={"qdrant_filters": filtros} if filtros else {},

            # Instrução para o LLM sobre como usar o contexto
            response_mode="compact",  # condensa múltiplos chunks em uma resposta
        )

        # Envolve a query com contexto do domínio
        query_enriquecida = f"""
        Você é um analista de e-commerce. Com base nos reviews de clientes abaixo,
        responda em português de forma clara e objetiva:

        {query}

        Inclua na resposta:
        - Padrões identificados nos reviews
        - Sentimento geral dos clientes
        - Pontos específicos mencionados
        """

        resposta = query_engine.query(query_enriquecida)

        # Também pega os nós de contexto para exibir as fontes
        retriever = self.index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)

        reviews = [
            ReviewEncontrado(
                review_id=n.metadata.get("review_id", 0),
                produto_id=n.metadata.get("produto_id", 0),
                nota=n.metadata.get("nota", 0),
                sentimento=n.metadata.get("sentimento", ""),
                texto=n.node.text,
                score=round(n.score or 0.0, 4),
            )
            for n in nodes
        ]

        return ResultadoBusca(
            query=query,
            modo="rag",
            reviews_encontrados=reviews,
            resposta_llm=str(resposta),
            total_encontrados=len(reviews),
        )