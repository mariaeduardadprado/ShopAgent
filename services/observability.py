# services/observability.py
"""
Wrapper de observabilidade com LangFuse.

O LangFuse rastreia cada interação do sistema:
- Qual pergunta chegou
- Qual agente respondeu
- Quanto tempo levou
- Quantos tokens foram usados
- Se houve erro

Em produção: isso permite criar alertas, dashboards de custo
e detectar degradação de qualidade ao longo do tempo.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()


class ObservabilityService:

    def __init__(self):
        self.client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST"),
        )
        print("✅ LangFuse conectado")

    def registrar_interacao(
        self,
        pergunta: str,
        resposta: str,
        tipo_query: str,
        duracao_ms: int,
        erro: str | None = None,
    ):
        """
        Registra uma interação completa no LangFuse.
        Chame isso após cada resposta do ShopCrew.
        """
        trace = self.client.trace(
            name="shopagent-interacao",
            input=pergunta,
            output=resposta,
            metadata={
                "tipo_query":  tipo_query,
                "duracao_ms":  duracao_ms,
                "timestamp":   datetime.now().isoformat(),
                "teve_erro":   erro is not None,
                "erro":        erro or "",
            },
            tags=[tipo_query, "producao" if not erro else "erro"],
        )
        return trace

    def registrar_span(self, trace, nome: str, input_: str, output: str):
        """
        Registra um passo interno dentro de uma interação.
        Use para rastrear cada agente individualmente.
        """
        return trace.span(
            name=nome,
            input=input_,
            output=output,
        )

    def flush(self):
        """Garante que todos os eventos foram enviados."""
        self.client.flush()