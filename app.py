# app.py — versão final com observabilidade
import time
import chainlit as cl
from agents.shop_crew import ShopCrew
from services.observability import ObservabilityService

shop_crew    = ShopCrew()
observability = ObservabilityService()


@cl.on_chat_start
async def iniciar():
    await cl.Message(
        content=(
            "👋 Olá! Sou o **ShopAgent**, seu analista de e-commerce.\n\n"
            "Posso responder sobre:\n"
            "- 📊 **Métricas**: faturamento, ticket médio, vendas por região\n"
            "- 💬 **Reviews**: satisfação, reclamações, sentimento\n"
            "- 🔀 **Combinado**: vendas + opinião juntos\n\n"
            "O que você quer saber?"
        )
    ).send()


@cl.on_message
async def responder(message: cl.Message):
    pergunta = message.content.strip()
    if not pergunta:
        return

    inicio = time.time()
    erro = None

    async with cl.Step(name="🤖 Analisando com agentes...") as step:
        step.input = pergunta
        try:
            import asyncio
            resposta = await asyncio.get_event_loop().run_in_executor(
                None, shop_crew.responder, pergunta
            )
            step.output = "Concluído"
        except Exception as e:
            erro = str(e)
            resposta = "Desculpe, ocorreu um erro ao processar sua pergunta."
            step.output = f"Erro: {erro}"

    duracao_ms = int((time.time() - inicio) * 1000)

    # Classifica para registrar o tipo no LangFuse
    classificacao = shop_crew.router.classificar(pergunta)

    # Registra no LangFuse (não bloqueia a resposta)
    observability.registrar_interacao(
        pergunta=pergunta,
        resposta=resposta,
        tipo_query=str(classificacao.tipo),
        duracao_ms=duracao_ms,
        erro=erro,
    )
    observability.flush()

    await cl.Message(content=resposta).send()