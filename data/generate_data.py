# data/generate_data.py
"""
Pipeline de ingestão de dados fake para o ShopAgent.

Por que Faker? Porque em produção você vai conectar em dados reais,
mas para desenvolver e testar o sistema você precisa de dados controlados
e realistas. Faker gera CPFs, nomes, textos em pt-BR, etc.
"""

import random
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import Literal

# Configurar Faker em português do Brasil
fake = Faker("pt_BR")
random.seed(42)  # Reprodutibilidade


# ─────────────────────────────────────────────────────────────────
# Modelos Pydantic — tipagem forte garante integridade dos dados
# Em produção: esses modelos seriam usados também na validação da API
# ─────────────────────────────────────────────────────────────────

class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float = Field(gt=0)
    estoque: int = Field(ge=0)

class Pedido(BaseModel):
    id: int
    produto_id: int
    cliente_nome: str
    cliente_email: str
    regiao: str
    quantidade: int = Field(ge=1)
    valor_total: float
    status: Literal["aprovado", "cancelado", "pendente"]
    criado_em: datetime

class Review(BaseModel):
    id: int
    produto_id: int
    cliente: str
    nota: int = Field(ge=1, le=5)
    texto: str
    sentimento: Literal["positivo", "negativo", "neutro"]
    criado_em: datetime


# ─────────────────────────────────────────────────────────────────
# Dados de referência — categorias e produtos reais de e-commerce
# ─────────────────────────────────────────────────────────────────

CATEGORIAS = {
    "Eletrônicos":    ["iPhone 15", "Samsung Galaxy S24", "AirPods Pro", "iPad Air", "Kindle"],
    "Casa e Jardim":  ["Panela de Pressão", "Aspirador Robô", "Liquidificador", "Cafeteira", "Faca Chef"],
    "Esportes":       ["Tênis Running", "Esteira Elétrica", "Halteres 10kg", "Bike Spinning", "Raquete Tênis"],
    "Beleza":         ["Perfume Feminino", "Creme Anti-idade", "Sérum Vitamina C", "Protetor Solar", "Base Líquida"],
    "Livros":         ["Clean Code", "O Poder do Hábito", "Sapiens", "Mindset", "Thinking Fast and Slow"],
}

REGIOES = ["Sul", "Sudeste", "Norte", "Nordeste", "Centro-Oeste"]

# Templates de reviews para cada nível de sentimento
REVIEWS_POSITIVOS = [
    "Produto excelente! Superou todas as minhas expectativas. Entrega rápida e embalagem impecável.",
    "Amei o produto! Qualidade incrível pelo preço. Já recomendei para vários amigos.",
    "Compra perfeita. Chegou antes do prazo, funciona muito bem. Com certeza comprarei novamente.",
    "Muito satisfeito com a compra. O produto é exatamente como descrito, ótima qualidade.",
    "Fantástico! Vale cada centavo. Atendimento da loja também foi excelente.",
]

REVIEWS_NEGATIVOS = [
    "Produto veio com defeito. Tive que acionar o suporte, demora muito para resolver.",
    "Decepcionante. A qualidade não é o que estava anunciado, parece falsificado.",
    "Chegou com 10 dias de atraso e ainda veio embalagem amassada. Péssima experiência.",
    "Não recomendo. O produto parou de funcionar após 2 semanas de uso.",
    "Produto veio errado. Serviço de trocas muito lento e sem retorno.",
]

REVIEWS_NEUTROS = [
    "Produto ok, nada além do esperado. Entrega dentro do prazo.",
    "Cumpre o que promete. Qualidade mediana para o preço.",
    "Compra razoável. Esperava um pouco mais mas não tenho do que reclamar.",
    "Produto funcionando normalmente. Tempo de entrega foi o padrão.",
    "Nada especial mas também não tem problemas. Faria a compra novamente.",
]


def gerar_produtos(n: int = 25) -> list[Produto]:
    """Gera catálogo de produtos com preços realistas por categoria."""
    produtos = []
    pid = 1

    for categoria, nomes in CATEGORIAS.items():
        for nome in nomes:
            # Faixas de preço por categoria (mais realistas)
            if categoria == "Eletrônicos":
                preco = round(random.uniform(299.90, 8999.90), 2)
            elif categoria == "Esportes":
                preco = round(random.uniform(49.90, 3999.90), 2)
            elif categoria == "Beleza":
                preco = round(random.uniform(29.90, 499.90), 2)
            elif categoria == "Livros":
                preco = round(random.uniform(29.90, 89.90), 2)
            else:
                preco = round(random.uniform(69.90, 1299.90), 2)

            produtos.append(Produto(
                id=pid,
                nome=nome,
                categoria=categoria,
                preco=preco,
                estoque=random.randint(0, 500),
            ))
            pid += 1

    return produtos


def gerar_pedidos(produtos: list[Produto], n: int = 500) -> list[Pedido]:
    """
    Gera pedidos com distribuição realista:
    - Mais pedidos no Sudeste (maior mercado)
    - Mais cancelamentos em produtos baratos (fraude típica)
    - Datas nos últimos 6 meses
    """
    pedidos = []
    agora = datetime.now()

    # Pesos regionais baseados em dados reais de e-commerce BR
    pesos_regiao = {
        "Sudeste": 0.45,
        "Sul": 0.20,
        "Nordeste": 0.20,
        "Norte": 0.08,
        "Centro-Oeste": 0.07,
    }
    regioes = list(pesos_regiao.keys())
    pesos = list(pesos_regiao.values())

    for i in range(1, n + 1):
        produto = random.choice(produtos)
        quantidade = random.randint(1, 5)
        status = random.choices(
            ["aprovado", "cancelado", "pendente"],
            weights=[0.80, 0.12, 0.08]
        )[0]

        # Data aleatória nos últimos 180 dias
        dias_atras = random.randint(0, 180)
        data = agora - timedelta(days=dias_atras, hours=random.randint(0, 23))

        pedidos.append(Pedido(
            id=i,
            produto_id=produto.id,
            cliente_nome=fake.name(),
            cliente_email=fake.email(),
            regiao=random.choices(regioes, weights=pesos)[0],
            quantidade=quantidade,
            valor_total=round(produto.preco * quantidade, 2),
            status=status,
            criado_em=data,
        ))

    return pedidos


def gerar_reviews(produtos: list[Produto], pedidos: list[Pedido], n: int = 300) -> list[Review]:
    """
    Gera reviews com distribuição de sentimento realista:
    - 60% positivos (clientes satisfeitos)
    - 25% neutros
    - 15% negativos (insatisfeitos ou com problemas)
    """
    reviews = []
    agora = datetime.now()

    # Apenas pedidos aprovados geram reviews
    pedidos_aprovados = [p for p in pedidos if p.status == "aprovado"]

    for i in range(1, n + 1):
        pedido = random.choice(pedidos_aprovados)
        sentimento = random.choices(
            ["positivo", "neutro", "negativo"],
            weights=[0.60, 0.25, 0.15]
        )[0]

        if sentimento == "positivo":
            nota = random.randint(4, 5)
            texto = random.choice(REVIEWS_POSITIVOS)
        elif sentimento == "negativo":
            nota = random.randint(1, 2)
            texto = random.choice(REVIEWS_NEGATIVOS)
        else:
            nota = 3
            texto = random.choice(REVIEWS_NEUTROS)

        reviews.append(Review(
            id=i,
            produto_id=pedido.produto_id,
            cliente=fake.first_name(),
            nota=nota,
            texto=texto,
            sentimento=sentimento,
            criado_em=agora - timedelta(days=random.randint(1, 150)),
        ))

    return reviews


def salvar_csvs(produtos: list[Produto], pedidos: list[Pedido], reviews: list[Review]):
    """Salva os dados em CSV para ingestão posterior no banco."""

    df_produtos = pd.DataFrame([p.model_dump() for p in produtos])
    df_pedidos  = pd.DataFrame([p.model_dump() for p in pedidos])
    df_reviews  = pd.DataFrame([r.model_dump() for r in reviews])

    df_produtos.to_csv("data/produtos.csv",  index=False, encoding="utf-8")
    df_pedidos.to_csv("data/pedidos.csv",    index=False, encoding="utf-8")
    df_reviews.to_csv("data/reviews.csv",    index=False, encoding="utf-8")

    print(f"✅ {len(produtos)} produtos salvos em data/produtos.csv")
    print(f"✅ {len(pedidos)} pedidos salvos em data/pedidos.csv")
    print(f"✅ {len(reviews)} reviews salvos em data/reviews.csv")


if __name__ == "__main__":
    print("🎲 Gerando dados fake de e-commerce...")

    produtos = gerar_produtos(n=25)
    pedidos  = gerar_pedidos(produtos, n=500)
    reviews  = gerar_reviews(produtos, pedidos, n=300)

    salvar_csvs(produtos, pedidos, reviews)

    # Preview dos dados
    print("\n📦 Amostra de produtos:")
    for p in produtos[:3]:
        print(f"   {p.nome} ({p.categoria}) — R$ {p.preco}")

    print("\n🛒 Amostra de pedidos:")
    for p in pedidos[:3]:
        print(f"   Pedido #{p.id} | {p.regiao} | R$ {p.valor_total} | {p.status}")

    print("\n⭐ Amostra de reviews:")
    for r in reviews[:3]:
        print(f"   [{r.sentimento}] nota {r.nota} — \"{r.texto[:60]}...\"")