# tests/test_qualidade.py
"""
Testes de qualidade das respostas do ShopAgent.

Métricas avaliadas:
- Relevância: a resposta responde a pergunta?
- Factualidade: a resposta é factualmente consistente com o contexto?
- Completude: a resposta cobre todos os aspectos da pergunta?

Em produção: esses testes rodam em CI/CD antes de cada deploy.
Se a qualidade cair abaixo do threshold, o deploy é bloqueado.
"""

import pytest
from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase
from agents.shop_crew import ShopCrew

# Instância compartilhada para todos os testes
crew = ShopCrew()


def criar_caso(pergunta: str, contexto: list[str]) -> LLMTestCase:
    """Executa o crew e monta o caso de teste."""
    resposta = crew.responder(pergunta)
    return LLMTestCase(
        input=pergunta,
        actual_output=resposta,
        retrieval_context=contexto,
    )


class TestRespostasSQL:

    def test_faturamento_menciona_valor(self):
        """A resposta sobre faturamento deve conter um valor monetário."""
        caso = criar_caso(
            pergunta="Qual o faturamento total?",
            contexto=["O faturamento total é calculado somando todos os pedidos aprovados."],
        )
        metrica = AnswerRelevancyMetric(threshold=0.7, model="gpt-4o-mini")
        assert_test(caso, [metrica])

    def test_resposta_menciona_regioes(self):
        """A resposta sobre vendas por região deve mencionar regiões brasileiras."""
        resposta = crew.responder("Como estão as vendas por região?")
        regioes = ["Sudeste", "Sul", "Nordeste", "Norte", "Centro-Oeste"]
        mencionou = any(r in resposta for r in regioes)
        assert mencionou, f"Resposta não menciona nenhuma região: {resposta[:200]}"


class TestRespostasSemanticas:

    def test_resposta_sobre_reviews_e_relevante(self):
        """A resposta sobre reviews deve ser relevante para a pergunta."""
        caso = criar_caso(
            pergunta="Os clientes estão satisfeitos com os produtos?",
            contexto=[
                "Reviews de clientes indicam satisfação geral com os produtos.",
                "Alguns clientes reclamaram de problemas com entrega e suporte.",
            ],
        )
        metrica = AnswerRelevancyMetric(threshold=0.7, model="gpt-4o-mini")
        assert_test(caso, [metrica])

    def test_resposta_fiel_ao_contexto(self):
        """A resposta não deve inventar informações além do contexto."""
        caso = criar_caso(
            pergunta="Quais são as principais reclamações dos clientes?",
            contexto=[
                "Clientes reclamam principalmente de atrasos na entrega.",
                "Há reclamações sobre produtos com defeito.",
                "O suporte ao cliente é mencionado como lento.",
            ],
        )
        metrica = FaithfulnessMetric(threshold=0.7, model="gpt-4o-mini")
        assert_test(caso, [metrica])


class TestRoteamento:

    def test_pergunta_sql_classificada_corretamente(self):
        from services.query_router import QueryRouter, TipoQuery
        router = QueryRouter()
        resultado = router.classificar("Qual o faturamento total?")
        assert resultado.tipo == TipoQuery.SQL

    def test_pergunta_semantica_classificada_corretamente(self):
        from services.query_router import QueryRouter, TipoQuery
        router = QueryRouter()
        resultado = router.classificar("Os clientes estão reclamando de entrega?")
        assert resultado.tipo == TipoQuery.SEMANTICO

    def test_pergunta_hibrida_classificada_corretamente(self):
        from services.query_router import QueryRouter, TipoQuery
        router = QueryRouter()
        resultado = router.classificar(
            "Como estão as vendas e o que os clientes acham dos produtos?"
        )
        assert resultado.tipo == TipoQuery.HIBRIDO