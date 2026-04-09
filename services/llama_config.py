# services/llama_config.py
"""
Configuração central do LlamaIndex.

Por que centralizar aqui?
Em produção você pode querer trocar o modelo de embedding
(ex: de OpenAI para um modelo local como nomic-embed-text)
e isso impacta TODO o sistema. Centralizar significa mudar
em um único lugar.
"""

import os
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

load_dotenv()


def configurar_llama():
    """
    Configura os modelos globais do LlamaIndex.
    Deve ser chamado UMA VEZ antes de qualquer operação RAG.
    """

    # Modelo de embedding: transforma texto em vetor numérico
    # text-embedding-3-small: 1536 dimensões, rápido e barato
    # Em produção: considere text-embedding-3-large para mais precisão
    Settings.embed_model = OpenAIEmbedding(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    # LLM: responsável por gerar a resposta final
    # gpt-4o-mini: bom custo-benefício para RAG
    Settings.llm = OpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.1,  # baixo = respostas mais factuais e consistentes
    )

    # Tamanho do chunk: quantos caracteres por pedaço de texto
    # Reviews são curtos, então 512 é suficiente
    # Para documentos longos (PDFs), use 1024-2048
    Settings.chunk_size = 512
    Settings.chunk_overlap = 50  # sobreposição evita perder contexto nas bordas

    print("✅ LlamaIndex configurado")
    print(f"   Embedding: text-embedding-3-small (1536d)")
    print(f"   LLM: gpt-4o-mini")
    print(f"   Chunk size: {Settings.chunk_size}")