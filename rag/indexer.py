# rag/indexer.py
"""
Pipeline de indexação de reviews no Qdrant via LlamaIndex.

Fluxo:
  CSV → Documents → Nodes (chunks) → Embeddings → Qdrant

Por que usar LlamaIndex em vez de chamar a OpenAI direto?
LlamaIndex gerencia chunking, batching, metadados e retry
automaticamente. Chamar a API direto você teria que implementar
tudo isso na mão.
"""

import os
import pandas as pd
from dotenv import load_dotenv

from llama_index.core import Document, VectorStoreIndex, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from services.llama_config import configurar_llama

load_dotenv()


def carregar_reviews_como_documents(caminho_csv: str) -> list[Document]:
    """
    Converte reviews do CSV em objetos Document do LlamaIndex.

    O Document é a unidade básica do LlamaIndex — é um texto
    com metadados. Os metadados são cruciais: permitem filtrar
    a busca depois (ex: buscar só reviews negativos, ou de um produto).
    """
    df = pd.read_csv(caminho_csv)
    documents = []

    for _, row in df.iterrows():
        # O texto principal — o que vai ser vetorizado
        # Incluímos contexto extra no texto para enriquecer o embedding
        texto_enriquecido = f"""
Review de cliente sobre produto ID {row['produto_id']}.
Avaliação: {row['nota']}/5 estrelas.
Sentimento: {row['sentimento']}.
Comentário: {row['texto']}
        """.strip()

        doc = Document(
            text=texto_enriquecido,

            # Metadados: armazenados junto do vetor, não são vetorizados
            # Permitem filtros na busca (WHERE no mundo vetorial)
            metadata={
                "review_id":   int(row["id"]),
                "produto_id":  int(row["produto_id"]),
                "cliente":     str(row["cliente"]),
                "nota":        int(row["nota"]),
                "sentimento":  str(row["sentimento"]),
                "criado_em":   str(row["criado_em"]),
            },

            # ID único para evitar duplicatas ao re-indexar
            doc_id=f"review_{row['id']}",
        )
        documents.append(doc)

    print(f"✅ {len(documents)} reviews carregados como Documents")
    return documents


def indexar_no_qdrant(documents: list[Document]) -> VectorStoreIndex:
    """
    Indexa os Documents no Qdrant.

    O LlamaIndex faz automaticamente:
    1. Divide cada documento em chunks (se necessário)
    2. Chama a API de embedding para cada chunk
    3. Insere os vetores + metadados no Qdrant
    4. Faz retry em caso de erro na API
    """
    # Conecta ao Qdrant
    client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))

    # Adapter do LlamaIndex para o Qdrant
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=os.getenv("QDRANT_COLLECTION", "reviews"),
    )

    # StorageContext: onde o índice vai ser persistido
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print("⏳ Gerando embeddings e indexando no Qdrant...")
    print("   (isso faz chamadas à API da OpenAI — pode levar ~30s)")

    # Aqui acontece a magia: embedding + inserção no Qdrant
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True,  # barra de progresso no terminal
    )

    # Verifica quantos vetores foram inseridos
    info = client.get_collection("reviews")
    print(f"\n✅ Indexação completa!")
    print(f"   Vetores no Qdrant: {info.vectors_count}")

    return index


if __name__ == "__main__":
    # Inicializa os modelos
    configurar_llama()

    # Carrega e indexa
    documents = carregar_reviews_como_documents("data/reviews.csv")
    index = indexar_no_qdrant(documents)

    print("\n🎉 Reviews indexados com sucesso no Qdrant!")
    print("   Acesse: http://localhost:6333/dashboard para visualizar")