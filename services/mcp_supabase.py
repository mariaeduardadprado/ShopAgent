# services/mcp_supabase.py
"""
MCP Connector para o Supabase (PostgreSQL).

O papel deste módulo é expor operações SQL como ferramentas
que os agentes podem chamar. Em vez de o agente escrever SQL
diretamente, ele chama métodos como get_faturamento() ou
get_vendas_por_regiao() — isso é mais seguro e testável.

Em produção: usaria connection pooling (PgBouncer ou asyncpg)
para não abrir uma conexão nova a cada query.
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Any

load_dotenv()


# ── Modelos de resposta ───────────────────────────────────────

class ResultadoSQL(BaseModel):
    query: str
    colunas: list[str]
    dados: list[dict[str, Any]]
    total_linhas: int
    erro: str | None = None


class MetricasEcommerce(BaseModel):
    faturamento_total: float
    total_pedidos: int
    ticket_medio: float
    pedidos_aprovados: int
    pedidos_cancelados: int
    taxa_cancelamento: float


class VendasRegiao(BaseModel):
    regiao: str
    total_pedidos: int
    faturamento: float
    ticket_medio: float


class MCPSupabase:
    """
    Conector MCP para o PostgreSQL/Supabase.

    Expõe operações de negócio como métodos Python tipados.
    Os agentes chamam esses métodos sem saber SQL.
    """

    def __init__(self):
        self.conn_string = os.getenv("DATABASE_URL")
        self._testar_conexao()

    def _testar_conexao(self):
        try:
            conn = self._conectar()
            conn.close()
            print("✅ MCPSupabase conectado ao PostgreSQL")
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            raise

    def _conectar(self):
        """Abre uma conexão. Em produção: usar pool."""
        return psycopg2.connect(self.conn_string)

    def executar_query(self, sql: str, params: tuple = ()) -> ResultadoSQL:
        """
        Executa SQL arbitrário e retorna resultado tipado.
        Método de baixo nível — use os métodos específicos quando possível.
        """
        try:
            conn = self._conectar()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(sql, params)

            colunas = [desc[0] for desc in cursor.description or []]
            dados = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return ResultadoSQL(
                query=sql,
                colunas=colunas,
                dados=dados,
                total_linhas=len(dados),
            )
        except Exception as e:
            return ResultadoSQL(
                query=sql,
                colunas=[],
                dados=[],
                total_linhas=0,
                erro=str(e),
            )

    def get_metricas_gerais(self) -> MetricasEcommerce:
        """Retorna KPIs principais do e-commerce."""
        resultado = self.executar_query("""
            SELECT
                COALESCE(SUM(valor_total), 0)                           AS faturamento_total,
                COUNT(*)                                                 AS total_pedidos,
                COALESCE(AVG(valor_total), 0)                           AS ticket_medio,
                COUNT(*) FILTER (WHERE status = 'aprovado')             AS pedidos_aprovados,
                COUNT(*) FILTER (WHERE status = 'cancelado')            AS pedidos_cancelados
            FROM pedidos
        """)

        if resultado.erro or not resultado.dados:
            raise ValueError(f"Erro ao buscar métricas: {resultado.erro}")

        row = resultado.dados[0]
        total = row["total_pedidos"] or 1  # evita divisão por zero

        return MetricasEcommerce(
            faturamento_total=float(row["faturamento_total"]),
            total_pedidos=int(row["total_pedidos"]),
            ticket_medio=float(row["ticket_medio"]),
            pedidos_aprovados=int(row["pedidos_aprovados"]),
            pedidos_cancelados=int(row["pedidos_cancelados"]),
            taxa_cancelamento=round(
                int(row["pedidos_cancelados"]) / total * 100, 2
            ),
        )

    def get_vendas_por_regiao(self) -> list[VendasRegiao]:
        """Retorna faturamento e volume por região."""
        resultado = self.executar_query("""
            SELECT
                regiao,
                COUNT(*)            AS total_pedidos,
                SUM(valor_total)    AS faturamento,
                AVG(valor_total)    AS ticket_medio
            FROM pedidos
            WHERE status = 'aprovado'
            GROUP BY regiao
            ORDER BY faturamento DESC
        """)

        return [
            VendasRegiao(
                regiao=row["regiao"],
                total_pedidos=int(row["total_pedidos"]),
                faturamento=round(float(row["faturamento"]), 2),
                ticket_medio=round(float(row["ticket_medio"]), 2),
            )
            for row in resultado.dados
        ]

    def get_top_produtos(self, limite: int = 5) -> list[dict]:
        """Retorna os produtos mais vendidos por faturamento."""
        resultado = self.executar_query("""
            SELECT
                pr.nome,
                pr.categoria,
                COUNT(pe.id)         AS total_vendas,
                SUM(pe.valor_total)  AS faturamento
            FROM pedidos pe
            JOIN produtos pr ON pr.id = pe.produto_id
            WHERE pe.status = 'aprovado'
            GROUP BY pr.id, pr.nome, pr.categoria
            ORDER BY faturamento DESC
            LIMIT %s
        """, (limite,))

        return resultado.dados

    def get_evolucao_mensal(self) -> list[dict]:
        """Retorna faturamento agrupado por mês — últimos 6 meses."""
        resultado = self.executar_query("""
            SELECT
                TO_CHAR(DATE_TRUNC('month', criado_em), 'YYYY-MM') AS mes,
                COUNT(*)                                            AS total_pedidos,
                SUM(valor_total)                                    AS faturamento
            FROM pedidos
            WHERE status = 'aprovado'
              AND criado_em >= NOW() - INTERVAL '6 months'
            GROUP BY DATE_TRUNC('month', criado_em)
            ORDER BY mes
        """)

        return resultado.dados

    def get_produto_mais_caro(self) -> dict:
        """Retorna o produto com maior preço unitário."""
        resultado = self.executar_query("""
            SELECT nome, categoria, preco
            FROM produtos
            ORDER BY preco DESC
            LIMIT 1
        """)
        return resultado.dados[0] if resultado.dados else {}

    def get_produtos_por_preco(self, limite: int = 5) -> list[dict]:
        """Retorna os produtos ordenados por preço decrescente."""
        resultado = self.executar_query("""
            SELECT nome, categoria, preco, estoque
            FROM produtos
            ORDER BY preco DESC
            LIMIT %s
        """, (limite,))
        return resultado.dados