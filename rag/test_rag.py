# rag/test_rag.py
"""
Teste interativo do sistema RAG.
Rode esse script para validar que a busca semântica funciona.
"""

from rag.search_engine import MotorBuscaSemantica


def testar_buscas():
    motor = MotorBuscaSemantica()

    # ── Teste 1: busca semântica pura ──────────────────────────
    print("\n" + "="*60)
    print("TESTE 1: Reclamações sobre entrega")
    print("="*60)

    resultado = motor.buscar(
        query="clientes reclamando de atraso na entrega",
        top_k=3,
        modo="simples",
    )
    for r in resultado.reviews_encontrados:
        print(f"\n[score: {r.score}] nota {r.nota}/5 — {r.sentimento}")
        print(f"{r.texto[:120]}...")

    # ── Teste 2: RAG com resposta do LLM ───────────────────────
    print("\n" + "="*60)
    print("TESTE 2: RAG — Análise de sentimento")
    print("="*60)

    resultado = motor.buscar(
        query="Qual é a satisfação geral dos clientes? Há padrões de reclamação?",
        top_k=5,
        modo="rag",
    )
    print(f"\nResposta do LLM:\n{resultado.resposta_llm}")

    # ── Teste 3: filtro por sentimento ─────────────────────────
    print("\n" + "="*60)
    print("TESTE 3: Apenas reviews negativos sobre qualidade")
    print("="*60)

    resultado = motor.buscar(
        query="problemas com qualidade do produto",
        top_k=3,
        filtro_sentimento="negativo",
        modo="simples",
    )
    print(f"Encontrados: {resultado.total_encontrados} reviews negativos")
    for r in resultado.reviews_encontrados:
        print(f"\n  nota {r.nota}/5: {r.texto[:100]}...")


if __name__ == "__main__":
    testar_buscas()