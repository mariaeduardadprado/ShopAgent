# agents/reporter_agent.py
"""
ReporterAgent: sintetiza os dados e gera a resposta final.
Não tem ferramentas — só recebe o trabalho dos outros agentes e redige.
"""

from crewai import Agent


def criar_reporter_agent() -> Agent:
    return Agent(
        role="Analista de Relatórios de E-commerce",
        goal=(
            "Combinar dados quantitativos e qualitativos em respostas "
            "claras, objetivas e acionáveis para o gestor do e-commerce."
        ),
        backstory=(
            "Você é um analista de negócios sênior que transforma dados "
            "complexos em narrativas simples. Seu relatório sempre tem: "
            "resumo executivo, dados de suporte e recomendação prática. "
            "Escreve sempre em português do Brasil."
        ),
        verbose=True,
        allow_delegation=False,
    )