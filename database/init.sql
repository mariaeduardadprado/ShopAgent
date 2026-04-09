-- database/init.sql
-- Este arquivo é executado automaticamente quando o container sobe.

CREATE TABLE IF NOT EXISTS produtos (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(200) NOT NULL,
    categoria   VARCHAR(100) NOT NULL,
    preco       NUMERIC(10, 2) NOT NULL,
    estoque     INTEGER DEFAULT 0,
    criado_em   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pedidos (
    id              SERIAL PRIMARY KEY,
    produto_id      INTEGER REFERENCES produtos(id),
    cliente_nome    VARCHAR(200) NOT NULL,
    cliente_email   VARCHAR(200),
    regiao          VARCHAR(100) NOT NULL,
    quantidade      INTEGER NOT NULL,
    valor_total     NUMERIC(10, 2) NOT NULL,
    status          VARCHAR(50) DEFAULT 'aprovado',
    criado_em       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reviews (
    id          SERIAL PRIMARY KEY,
    produto_id  INTEGER REFERENCES produtos(id),
    cliente     VARCHAR(200),
    nota        INTEGER CHECK (nota BETWEEN 1 AND 5),
    texto       TEXT NOT NULL,
    sentimento  VARCHAR(20),  -- positivo, negativo, neutro
    criado_em   TIMESTAMP DEFAULT NOW()
);

-- Índices para performance nas queries de métricas
CREATE INDEX IF NOT EXISTS idx_pedidos_regiao    ON pedidos(regiao);
CREATE INDEX IF NOT EXISTS idx_pedidos_criado_em ON pedidos(criado_em);
CREATE INDEX IF NOT EXISTS idx_reviews_produto   ON reviews(produto_id);