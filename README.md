# ShopAgent 🛒🤖

> Sistema de inteligência artificial para análise de e-commerce em tempo real.  
> Responde perguntas em linguagem natural sobre vendas, produtos e satisfação de clientes.

---

## O que é o ShopAgent?

Imagine que você é gestor de um e-commerce e quer saber:

- *"Qual região está vendendo mais este mês?"*
- *"Os clientes estão reclamando de alguma coisa?"*
- *"Qual o produto mais caro e o que os clientes acham do preço?"*

Normalmente você precisaria abrir o painel do banco de dados, escrever uma query SQL, depois ir em outra ferramenta analisar os comentários dos clientes, e por fim juntar tudo numa planilha para tomar uma decisão.

O ShopAgent faz tudo isso automaticamente. Você digita a pergunta em português, ele decide sozinho onde buscar a informação — banco de dados, comentários de clientes, ou os dois — e te entrega uma resposta completa com números, análise e recomendação.

---

## Como ele funciona na prática?

Quando você faz uma pergunta, o sistema passa por quatro etapas invisíveis:

**1. Classificação da pergunta**

O sistema lê sua pergunta e decide automaticamente o tipo de resposta que você precisa:

| Sua pergunta | O sistema entende | Onde busca |
|---|---|---|
| "Qual o faturamento do mês?" | Métrica numérica | Banco SQL |
| "Os clientes estão satisfeitos?" | Análise de texto | Reviews vetorizados |
| "Como estão as vendas e o que acham dos produtos?" | Os dois | SQL + Reviews |

**2. Ativação dos agentes especializados**

Dependendo do tipo, um ou mais agentes são ativados. Cada agente tem um papel fixo e não faz o trabalho do outro:

- O **AnalystAgent** só faz consultas SQL e interpreta números
- O **ResearchAgent** só faz busca semântica em reviews
- O **ReporterAgent** só recebe o trabalho dos dois e escreve a resposta final

**3. Consulta nas fontes de dados**

Cada agente consulta a fonte correta. O AnalystAgent fala com o PostgreSQL, o ResearchAgent fala com o Qdrant. Eles não se confundem e não acessam a fonte errada.

**4. Resposta estruturada**

O ReporterAgent sempre entrega a resposta no mesmo formato:
- Resumo executivo (a resposta direta)
- Dados de suporte (os números ou reviews que embasam)
- Recomendação prática (o que fazer com essa informação)


## Arquitetura do sistema

```
┌─────────────────────────────────────────────────────┐
│                    USUÁRIO                          │
│              (digita no Chainlit)                   │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│                 QueryRouter                         │
│    Classifica: SQL / Semântico / Híbrido            │
└──────────┬──────────────────────────┬───────────────┘
           │                          │
           ▼                          ▼
┌──────────────────┐      ┌──────────────────────────┐
│  AnalystAgent    │      │     ResearchAgent         │
│  Consulta SQL    │      │  Busca semântica RAG      │
│  (métricas)      │      │  (reviews, sentimento)    │
└────────┬─────────┘      └─────────────┬────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐      ┌──────────────────────────┐
│   PostgreSQL     │      │         Qdrant            │
│  (The Ledger)    │      │      (The Memory)         │
│  pedidos         │      │  vetores dos reviews      │
│  produtos        │      │  busca por similaridade   │
│  faturamento     │      │  análise de sentimento    │
└────────┬─────────┘      └─────────────┬────────────┘
         │                              │
         └──────────────┬───────────────┘
                        ▼
          ┌─────────────────────────────┐
          │       ReporterAgent         │
          │  Combina dados e escreve    │
          │  resposta em português      │
          └─────────────┬───────────────┘
                        │
                        ▼
          ┌─────────────────────────────┐
          │         LangFuse            │
          │  Registra tudo: tempo,      │
          │  tokens, qualidade          │
          └─────────────────────────────┘
```

---

## Stack tecnológica

| Tecnologia | Papel no sistema | Por que foi escolhida |
|---|---|---|
| **CrewAI** | Orquestra os agentes | Framework multi-agent com suporte nativo a ferramentas e sequenciamento de tarefas |
| **PostgreSQL / Supabase** | Armazena dados estruturados (pedidos, produtos) | Banco relacional robusto, queries SQL rápidas para métricas |
| **Qdrant** | Armazena vetores dos reviews | Banco vetorial especializado em busca por similaridade semântica |
| **LlamaIndex** | Pipeline RAG completo | Gerencia chunking, embeddings, retry e query engine automaticamente |
| **OpenAI** | Embeddings + LLM | text-embedding-3-small para vetores, gpt-4o-mini para respostas |
| **Chainlit** | Interface de chat | Transforma Python em chat web com pouquíssimo código |
| **LangFuse** | Observabilidade | Rastreia cada chamada: custo, tempo, qualidade |
| **DeepEval** | Testes de qualidade | Avalia automaticamente relevância e fidelidade das respostas |
| **Docker** | Ambiente local | Sobe PostgreSQL e Qdrant isolados sem poluir a máquina |
| **Pydantic** | Tipagem e validação | Garante integridade dos dados em todo o sistema |

---

## Por que dois bancos de dados?

Essa é a decisão técnica mais importante do projeto e vale entender o motivo.

**PostgreSQL** é excelente para perguntas como:
- "Qual o faturamento do Sudeste nos últimos 3 meses?"
- "Quais produtos têm estoque abaixo de 10 unidades?"

Ele responde com `SELECT`, `GROUP BY`, `SUM` — lógica matemática e estruturada.

**Qdrant** é necessário para perguntas como:
- "Os clientes mencionam problema com entrega?"
- "Existe reclamação sobre atendimento pós-venda?"

Aqui não existe `SELECT` possível. A palavra "atendimento pós-venda" pode não aparecer em nenhum review — mas o review *"tive que acionar o suporte e demorou muito"* está falando exatamente disso. O Qdrant encontra essa relação por similaridade matemática entre vetores.

Usar só um banco significaria perder metade da inteligência do sistema.

---

## O que é RAG e por que usamos?

RAG significa *Retrieval Augmented Generation* — recuperação aumentada de geração.

O problema: um LLM como o GPT não sabe nada sobre os reviews dos seus clientes. Ele foi treinado com dados da internet, não com os dados do seu e-commerce.

A solução em três etapas:

**Etapa 1 — Indexação** (feita uma vez):
```
Reviews → OpenAI Embeddings → vetores matemáticos → Qdrant
"produto chegou quebrado" → [0.23, -0.87, 0.45, ...]
```

**Etapa 2 — Recuperação** (a cada pergunta):
```
Pergunta do usuário → vetor → Qdrant encontra os 5 reviews mais similares
```

**Etapa 3 — Geração** (a cada pergunta):
```
GPT recebe: pergunta + 5 reviews relevantes → gera resposta contextualizada
```

O resultado: o LLM responde como se tivesse lido todos os seus reviews, mas na prática só viu os 5 mais relevantes para aquela pergunta específica.

---

## Estrutura do projeto

```
shopagent/
│
├── agents/                    # Os três agentes de IA
│   ├── analyst_agent.py       # Especialista em SQL e métricas
│   ├── research_agent.py      # Especialista em reviews e RAG
│   ├── reporter_agent.py      # Sintetiza e escreve a resposta final
│   └── shop_crew.py           # Orquestra os agentes com CrewAI
│
├── services/                  # Conectores e lógica de negócio
│   ├── mcp_supabase.py        # Conector SQL — queries de métricas
│   ├── mcp_qdrant.py          # Conector vetorial — busca semântica
│   ├── query_router.py        # Decide: SQL, semântico ou híbrido
│   ├── context_builder.py     # Monta o contexto completo para os agentes
│   ├── llama_config.py        # Configuração central do LlamaIndex
│   └── observability.py       # Integração com LangFuse
│
├── rag/                       # Pipeline de busca semântica
│   ├── setup_qdrant.py        # Cria a coleção no Qdrant
│   ├── indexer.py             # Indexa reviews como vetores
│   └── search_engine.py       # Motor de busca semântica
│
├── database/                  # Banco de dados relacional
│   ├── init.sql               # Schema: tabelas produtos, pedidos, reviews
│   └── load_data.py           # Carrega CSVs no PostgreSQL
│
├── data/                      # Dados gerados
│   ├── generate_data.py       # Gera dados fake realistas de e-commerce
│   ├── produtos.csv
│   ├── pedidos.csv
│   └── reviews.csv
│
├── tests/                     # Testes automatizados
│   ├── test_qualidade.py      # DeepEval: relevância e fidelidade
│   └── test_decisao.py        # Testa o roteamento de perguntas
│
├── app.py                     # Interface Chainlit (ponto de entrada)
├── docker-compose.yml         # PostgreSQL + Qdrant em containers
├── requirements.txt
└── .env                       # Chaves de API e configurações
```

---

## Como rodar o projeto

### Pré-requisitos

- Python 3.12+
- Docker instalado e rodando
- Conta na OpenAI com créditos (para embeddings e LLM)
- Conta no LangFuse Cloud (gratuita) para observabilidade

### Passo 1 — Clone e configure o ambiente

```bash
git clone https://github.com/seu-usuario/shopagent.git
cd shopagent

python -m venv venv
source venv/bin/activate       # Linux/Mac
# ou: venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### Passo 2 — Configure as variáveis de ambiente

Crie o arquivo `.env` na raiz do projeto:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Banco de dados
DATABASE_URL=postgresql://shopagent:shopagent_pass@localhost:5432/shopagent_db

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=reviews

# LangFuse (opcional — observabilidade)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Passo 3 — Suba a infraestrutura

```bash
docker compose up -d

# Verifique se está rodando:
docker compose ps
# Deve mostrar postgres (healthy) e qdrant (Up)

# Interface do Qdrant disponível em:
# http://localhost:6333/dashboard
```

### Passo 4 — Gere e carregue os dados

```bash
# Gera 25 produtos, 500 pedidos e 300 reviews fake em pt-BR
python data/generate_data.py

# Carrega os CSVs no PostgreSQL
python database/load_data.py
```

### Passo 5 — Indexe os reviews no Qdrant

```bash
# Cria a coleção vetorial
python rag/setup_qdrant.py

# Gera os embeddings e indexa (faz chamadas à API da OpenAI)
python rag/indexer.py
# Após concluir: 300 vetores no Qdrant dashboard
```

### Passo 6 — Inicie o chat

```bash
chainlit run app.py --watch
```

Acesse `http://localhost:8000` e comece a perguntar.

---

## Como a decisão SQL vs Semântico funciona?

O `QueryRouter` classifica cada pergunta em duas etapas:

**Etapa 1 — palavras-chave** (custo zero, latência < 1ms):

Verifica se a pergunta contém termos que indicam claramente o tipo:

```
Termos SQL:      faturamento, vendas, ticket médio, região,
                 mais caro, mais barato, preço, evolução...

Termos Semântico: review, avaliação, reclamação, satisfação,
                  clientes acham, entrega, qualidade, suporte...
```

Se a confiança for alta (≥ 70%), usa direto. Se não, vai para a etapa 2.

**Etapa 2 — LLM como árbitro** (custo de ~100 tokens, latência ~500ms):

Envia a pergunta para o GPT com um prompt de classificação e usa a resposta para decidir. Isso cobre casos ambíguos que as palavras-chave não conseguem resolver.

Exemplo de pergunta ambígua que vai para o LLM:
> *"Está valendo a pena vender na nossa loja?"*

Sem palavras-chave claras — o LLM entende o contexto e classifica como híbrido.

---

## Observabilidade com LangFuse

Cada interação é registrada automaticamente no LangFuse com:

- Pergunta original do usuário
- Tipo de query classificado (sql / semantico / hibrido)
- Resposta gerada
- Tempo total de processamento em milissegundos
- Se houve erro e qual foi

Acesse `cloud.langfuse.com` para ver o dashboard com histórico completo de uso, custo por interação e latência média.

Em produção, isso permite:
- Criar alertas quando a latência passa de um threshold
- Identificar quais perguntas o sistema não consegue responder bem
- Calcular custo mensal por usuário
- Detectar degradação de qualidade ao longo do tempo

---

## Autor: Maria EDuarda Prado

Desenvolvido como projeto de portfólio em arquitetura multi-agent com IA aplicada a e-commerce.

**Stack principal:** Python · CrewAI · LlamaIndex · Qdrant · PostgreSQL · Chainlit · LangFuse · DeepEval · Docker

---