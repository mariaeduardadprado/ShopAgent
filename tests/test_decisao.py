# tests/test_decisaopython tests/test_dia3.py.py
"""
Testa o pipeline completo de roteamento e consulta.
"""

from services.context_builder import ContextBuilder


def testar_pipeline():
    builder = ContextBuilder()

    perguntas = [
        # Deve ir para SQL
        "Qual o faturamento total do mês?",

        # Deve ir para semântico
        "Os clientes estão reclamando de alguma coisa?",

        # Deve ir para híbrido
        "Como estão as vendas de eletrônicos e o que os clientes acham deles?",
    ]

    for pergunta in perguntas:
        print("\n" + "="*60)
        contexto = builder.construir(pergunta)

        if contexto.dados_sql:
            m = contexto.dados_sql["metricas_gerais"]
            print(f"\n📊 SQL — Faturamento: R$ {m['faturamento_total']:,.2f}")
            print(f"         Pedidos: {m['total_pedidos']} | Ticket médio: R$ {m['ticket_medio']:,.2f}")

        if contexto.dados_semanticos:
            d = contexto.dados_semanticos
            print(f"\n💬 Semântico — Nota média: {d['nota_media']}")
            print(f"   Sentimentos: {d['distribuicao_sentimento']}")
            print(f"   Insight: {d['insights'][:200]}...")

        if contexto.erro:
            print(f"\n⚠️  {contexto.erro}")


if __name__ == "__main__":
    testar_pipeline()