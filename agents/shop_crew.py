# agents/shop_crew.py
"""
ShopCrew: monta e executa o time de agentes para cada pergunta.

Por que criar um Crew novo a cada pergunta?
Porque cada pergunta tem um contexto diferente (tasks diferentes).
O overhead é baixo — os agentes são leves.

Em produção: você pode manter os agentes em memória e só
recriar as tasks, o que reduz latência.
"""

from crewai import Crew, Task, Process
from services.query_router import QueryRouter, TipoQuery
from agents.analyst_agent import criar_analyst_agent
from agents.research_agent import criar_research_agent
from agents.reporter_agent import criar_reporter_agent


class ShopCrew:

    def __init__(self):
        self.router = QueryRouter()

    def responder(self, pergunta: str) -> str:
        """
        Ponto de entrada principal.
        Cria o crew adequado para a pergunta e executa.
        """
        classificacao = self.router.classificar(pergunta)
        tipo = classificacao.tipo

        print(f"\n🤖 ShopCrew ativado")
        print(f"   Tipo detectado: {tipo} ({classificacao.confianca:.0%})")

        # Instancia os agentes necessários
        reporter = criar_reporter_agent()

        if tipo == TipoQuery.SQL:
            return self._executar_sql(pergunta, reporter)

        elif tipo == TipoQuery.SEMANTICO:
            return self._executar_semantico(pergunta, reporter)

        elif tipo == TipoQuery.HIBRIDO:
            return self._executar_hibrido(pergunta, reporter)

        else:
            return (
                "Não consegui entender sua pergunta. Tente algo como:\n"
                "- 'Qual o faturamento do mês?'\n"
                "- 'Os clientes estão satisfeitos?'\n"
                "- 'Como estão as vendas e o que os clientes acham?'"
            )

    def _executar_sql(self, pergunta: str, reporter: any) -> str:
        analyst = criar_analyst_agent()

        task_analise = Task(
            description=(
                f"Responda esta pergunta usando os dados SQL disponíveis: '{pergunta}'\n"
                "Consulte as métricas gerais, por região e top produtos conforme relevante."
            ),
            expected_output="Análise quantitativa com os principais números e contexto.",
            agent=analyst,
        )

        task_relatorio = Task(
            description=(
                "Com base na análise do Analista de Dados, elabore uma resposta "
                f"clara e objetiva para: '{pergunta}'\n"
                "Inclua: resumo dos números, destaques e uma recomendação."
            ),
            expected_output="Relatório em português, claro e acionável.",
            agent=reporter,
            context=[task_analise],
        )

        crew = Crew(
            agents=[analyst, reporter],
            tasks=[task_analise, task_relatorio],
            process=Process.sequential,
            verbose=False,
        )

        resultado = crew.kickoff()
        return str(resultado)

    def _executar_semantico(self, pergunta: str, reporter: any) -> str:
        researcher = criar_research_agent()

        task_pesquisa = Task(
            description=(
                f"Analise os reviews de clientes para responder: '{pergunta}'\n"
                "Busque padrões de satisfação e reclamações relevantes."
            ),
            expected_output="Análise qualitativa com sentimentos, padrões e exemplos.",
            agent=researcher,
        )

        task_relatorio = Task(
            description=(
                "Com base na pesquisa de reviews, elabore uma resposta "
                f"clara para: '{pergunta}'\n"
                "Inclua: sentimento geral, principais padrões e recomendação."
            ),
            expected_output="Relatório em português, claro e acionável.",
            agent=reporter,
            context=[task_pesquisa],
        )

        crew = Crew(
            agents=[researcher, reporter],
            tasks=[task_pesquisa, task_relatorio],
            process=Process.sequential,
            verbose=False,
        )

        resultado = crew.kickoff()
        return str(resultado)

    def _executar_hibrido(self, pergunta: str, reporter: any) -> str:
        analyst    = criar_analyst_agent()
        researcher = criar_research_agent()

        task_analise = Task(
            description=(
                f"Analise os dados de vendas relevantes para: '{pergunta}'\n"
                "Foque nas métricas mais pertinentes à pergunta."
            ),
            expected_output="Análise quantitativa com números e contexto.",
            agent=analyst,
        )

        task_pesquisa = Task(
            description=(
                f"Analise os reviews de clientes relacionados a: '{pergunta}'\n"
                "Identifique sentimentos e padrões relevantes."
            ),
            expected_output="Análise qualitativa com sentimentos e padrões.",
            agent=researcher,
        )

        task_relatorio = Task(
            description=(
                "Combine a análise de dados E a pesquisa de reviews para "
                f"responder de forma completa: '{pergunta}'\n"
                "Estruture como: 1) Números, 2) Opinião dos clientes, 3) Recomendação."
            ),
            expected_output="Relatório completo em português com dados e insights.",
            agent=reporter,
            context=[task_analise, task_pesquisa],
        )

        crew = Crew(
            agents=[analyst, researcher, reporter],
            tasks=[task_analise, task_pesquisa, task_relatorio],
            process=Process.sequential,
            verbose=False,
        )

        resultado = crew.kickoff()
        return str(resultado)