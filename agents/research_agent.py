# agents/research_agent.py

from crewai import Agent
from crewai_tools import tool
from services.mcp_qdrant import MCPQdrant

_qdrant = MCPQdrant()


@tool("analisar_reviews")
def analisar_reviews(query: str, filtro: str = "") -> str:
    """
    Busca e analisa reviews de clientes semanticamente.
    Use para entender satisfação, reclamações e elogios.
    O parâmetro filtro é opcional: 'positivo', 'negativo' ou 'neutro'.
    """
    filtro_val = filtro if filtro in ["positivo", "negativo", "neutro"] else None
    analise = _qdrant.analisar_reviews(query, filtro_sentimento=filtro_val)

    dist = analise.distribuicao_sentimento
    return (
        f"Nota média: {analise.nota_media}/5\n"
        f"Sentimentos: {dist.get('positivo', 0)} positivos, "
        f"{dist.get('negativo', 0)} negativos, "
        f"{dist.get('neutro', 0)} neutros\n"
        f"Análise: {analise.insights}"
    )


def criar_research_agent() -> Agent:
    return Agent(
        role="Pesquisador de Experiência do Cliente",
        goal=(
            "Analisar reviews e feedback de clientes para identificar "
            "padrões de satisfação, reclamações recorrentes e pontos de melhoria."
        ),
        backstory=(
            "Você é especialista em análise de sentimento e voz do cliente. "
            "Transforma reviews em insights acionáveis para o negócio. "
            "Sempre contextualiza os dados qualitativos com exemplos concretos."
        ),
        tools=[analisar_reviews],
        verbose=True,
        allow_delegation=False,
    )