# rag/setup_qdrant.py
"""
Cria a coleção de reviews no Qdrant.

O que é uma coleção no Qdrant?
É como uma tabela no SQL — um namespace isolado para um tipo
de dado. Cada coleção tem suas próprias configurações de vetor.

Por que rodar separado?
Porque setup é feito UMA VEZ. Separar evita recriar a coleção
acidentalmente e perder os dados já indexados.
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from dotenv import load_dotenv

load_dotenv()

# Deve bater EXATAMENTE com o modelo de embedding
# text-embedding-3-small → 1536 dimensões
VECTOR_SIZE = 1536
COLLECTION_NAME = "reviews"


def criar_colecao():
    client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))

    # Verifica se já existe para não recriar
    colecoes = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME in colecoes:
        print(f"⚠️  Coleção '{COLLECTION_NAME}' já existe — pulando criação")
        info = client.get_collection(COLLECTION_NAME)
        print(f"   Vetores armazenados: {info.vectors_count}")
        return client

    # Cria a coleção com configuração de similaridade
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            # Cosine similarity: mede ângulo entre vetores
            # Melhor para similaridade semântica de texto
            # Alternativas: EUCLID (distância), DOT (produto escalar)
            distance=Distance.COSINE,
        ),
    )

    print(f"✅ Coleção '{COLLECTION_NAME}' criada no Qdrant")
    print(f"   Dimensão dos vetores: {VECTOR_SIZE}")
    print(f"   Métrica: Cosine Similarity")
    return client


if __name__ == "__main__":
    criar_colecao()