# database/load_data.py
"""
Carrega os CSVs gerados no PostgreSQL.
Em produção: usaria um pipeline ETL (Airflow, dbt, etc.)
Aqui: script simples e direto para o MVP.
"""

import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def conectar():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def carregar_produtos(conn, df: pd.DataFrame):
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO produtos (id, nome, categoria, preco, estoque)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (row.id, row.nome, row.categoria, row.preco, row.estoque))
    conn.commit()
    print(f"✅ {len(df)} produtos inseridos")

def carregar_pedidos(conn, df: pd.DataFrame):
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO pedidos (id, produto_id, cliente_nome, cliente_email, regiao, quantidade, valor_total, status, criado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (row.id, row.produto_id, row.cliente_nome, row.cliente_email,
              row.regiao, row.quantidade, row.valor_total, row.status, row.criado_em))
    conn.commit()
    print(f"✅ {len(df)} pedidos inseridos")

def carregar_reviews(conn, df: pd.DataFrame):
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO reviews (id, produto_id, cliente, nota, texto, sentimento, criado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (row.id, row.produto_id, row.cliente, row.nota,
              row.texto, row.sentimento, row.criado_em))
    conn.commit()
    print(f"✅ {len(df)} reviews inseridos")

if __name__ == "__main__":
    print("📥 Iniciando carga de dados no PostgreSQL...")

    conn = conectar()

    df_produtos = pd.read_csv("data/produtos.csv")
    df_pedidos  = pd.read_csv("data/pedidos.csv")
    df_reviews  = pd.read_csv("data/reviews.csv")

    carregar_produtos(conn, df_produtos)
    carregar_pedidos(conn, df_pedidos)
    carregar_reviews(conn, df_reviews)

    conn.close()
    print("\n🎉 Dados carregados com sucesso!")