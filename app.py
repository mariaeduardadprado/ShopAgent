# app.py
"""
Interface de chat com Chainlit.

O Chainlit transforma qualquer função Python assíncrona em um
chat web funcional. É o ponto de entrada do usuário no sistema.

Para rodar: chainlit run app.py
"""

import chainlit as cl
from agents.shop_crew import ShopCrew

# Instancia o crew uma vez — conexões com BD ficam abertas
shop_crew = ShopCrew()


@cl.on_chat_start
async def iniciar():
    """Executado quando o usuário abre o chat."""
    await cl.Message(
        content=(
            "👋 Olá! Sou o **ShopAgent**, seu analista de e-commerce.\n\n"
            "Posso responder sobre:\n"
            "- 📊 **Métricas**: faturamento, ticket médio, vendas por região\n"
            "- 💬 **Reviews**: satisfação, reclamações, sentimento dos clientes\n"
            "- 🔀 **Combinado**: vendas + opinião dos clientes juntos\n\n"
            "O que você quer saber?"
        )
    ).send()


@cl.on_message
async def responder(message: cl.Message):
    """Executado a cada mensagem do usuário."""

    pergunta = message.content.strip()

    if not pergunta:
        return

    # Mostra indicador de digitação enquanto processa
    async with cl.Step(name="🤖 Analisando com agentes...") as step:
        step.input = pergunta

        # Executa o crew (operação síncrona — rodar em thread)
        import asyncio
        resposta = await asyncio.get_event_loop().run_in_executor(
            None,
            shop_crew.responder,
            pergunta,
        )

        step.output = "Análise concluída"

    # Envia a resposta final
    await cl.Message(content=resposta).send()