# agents/analyst_agent.py

from crewai import Agent
from crewai_tools import tool
from services.mcp_supabase import MCPSupabase

# Instância compartilhada — não recria a conexão a cada chamada
_supabase = MCPSupabase()


@tool("consultar_metricas")
def consultar_metricas(tipo: str) -> str:
    """
    Consulta métricas do e-commerce no banco SQL.
    Valores válidos para tipo: 'geral', 'regiao', 'produtos', 'evolucao'.
    """
    if tipo == "geral":
        m = _supabase.get_metricas_gerais()
        return (
            f"Faturamento total: R$ {m.faturamento_total:,.2f}\n"
            f"Total de pedidos: {m.total_pedidos}\n"
            f"Ticket médio: R$ {m.ticket_medio:,.2f}\n"
            f"Taxa de cancelamento: {m.taxa_cancelamento}%"
        )
    elif tipo == "regiao":
        regioes = _supabase.get_vendas_por_regiao()
        return "\n".join(
            f"{r.regiao}: R$ {r.faturamento:,.2f} ({r.total_pedidos} pedidos)"
            for r in regioes
        )
    elif tipo == "produtos":
        prods = _supabase.get_top_produtos(5)
        return "\n".join(
            f"{p['nome']} ({p['categoria']}): R$ {float(p['faturamento']):,.2f}"
            for p in prods
        )
    elif tipo == "evolucao":
        meses = _supabase.get_evolucao_mensal()
        return "\n".join(
            f"{m['mes']}: R$ {float(m['faturamento']):,.2f} ({m['total_pedidos']} pedidos)"
            for m in meses
        )
    else:
        return "Tipo inválido. Use: geral, regiao, produtos ou evolucao."


def criar_analyst_agent() -> Agent:
    return Agent(
        role="Analista de Dados de E-commerce",
        goal=(
            "Consultar e interpretar métricas de vendas, faturamento "
            "e performance por região e produto."
        ),
        backstory=(
            "Você é um analista de dados sênior especializado em e-commerce. "
            "Tem profundo conhecimento em SQL e métricas de negócio. "
            "Sempre apresenta números com contexto e comparações."
        ),
        tools=[consultar_metricas],
        verbose=True,
        allow_delegation=False,
    )