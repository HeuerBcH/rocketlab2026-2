# RocketLab 2026.2 — repositório base

Base inicial para evoluir a atividade do RocketLab 2026.2. Ela preserva a organização do backend,
o modelo relacional do catálogo de filmes em SQLAlchemy 2.0 e o histórico de
migrações com Alembic, sem incluir interface, dados CSV, endpoints de negócio
ou rotinas de carga.

> **Nota:** `RocketLab` é apenas o nome de referência desta base. O diretório,
> nome do pacote, título da API e arquivo do banco podem ser renomeados para o
> que preferirem; eles não representam uma exigência da
> estrutura-base.

## Estrutura

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/        # ponto de composição dos futuros routers
│   │   ├── core/          # configurações e logging
│   │   ├── db/            # Base ORM, engine e sessões
│   │   └── movies/        # modelos SQLAlchemy do domínio de filmes
│   ├── migrations/        # ambiente e revisões Alembic
│   └── tests/
├── data/                  # CSVs da atividade (carga inicial)
├── frontend/
│   └── src/
│       ├── api/           # cliente tipado (OpenAPI), hooks do TanStack Query
│       ├── app/           # providers e rotas
│       ├── components/    # componentes de interface
│       ├── lib/           # formatação e tradução de gêneros
│       └── pages/         # telas
└── README.md
```

## Execução

Rode o **backend** e o **frontend** em terminais separados.

### Backend

Requer Python 3.11 ou superior.

**Linux/macOS**

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/python -m app.movies.seed --data-dir ../data   # carga dos CSVs (~1 min)
.venv/bin/uvicorn app.main:app --reload
```

**Windows (PowerShell)**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
Copy-Item .env.example .env
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m app.movies.seed --data-dir ..\data   # carga dos CSVs (~1 min)
.venv\Scripts\uvicorn app.main:app --reload
```

Os CSVs da atividade já acompanham o repositório em `data/` (veja
[data/README.md](data/README.md)).

A API ficará disponível em `http://localhost:8000`; use
`http://localhost:8000/docs` para a documentação automática. O endpoint
`GET /health` permite conferir se a aplicação iniciou corretamente.

### Autenticação do administrador

A leitura (catálogo, detalhes, avaliações) é pública. **Toda escrita** —
cadastrar, editar e excluir filmes e publicar avaliações — exige login.

O `.env.example` já traz credenciais de **desenvolvimento**:

| Usuário | Senha |
|---|---|
| `admin` | `rocketlab123` |

- No frontend, use **Entrar** no topo da página.
- No Swagger (`/docs`), use o botão **Authorize** com o mesmo usuário e senha.
- Para trocar a senha, gere um novo hash e cole em `ADMIN_PASSWORD_HASH` no
  `backend/.env` (entre aspas simples):

  ```bash
  .venv/bin/python -m app.auth.hash_password     # Windows: .venv\Scripts\python -m app.auth.hash_password
  ```

A senha é guardada apenas como hash (Argon2) e o login devolve um JWT válido
por `ACCESS_TOKEN_MINUTES` (padrão: 60). Se você já tinha o backend instalado,
rode `pip install -e ".[dev]"` de novo para instalar as dependências da
autenticação.

### Frontend

Requer Node.js 20 ou superior.

```bash
cd frontend
npm install
cp .env.example .env          # Windows: Copy-Item .env.example .env
npm run dev
```

A aplicação ficará disponível em `http://localhost:5173` (a porta liberada no
CORS do backend). Outros comandos:

| Comando | Função |
|---|---|
| `npm test` | Testes (Vitest + Testing Library) |
| `npm run typecheck` | Checagem de tipos |
| `npm run lint` | Lint (oxlint) |
| `npm run build` | Build de produção em `dist/` |
| `npm run gen:api` | Regenera `src/api/schema.d.ts` a partir do OpenAPI (backend rodando) |

## Banco de dados e migrações

O modelo usa um esquema estrela para o catálogo de filmes:

- dimensões de filmes, gêneros, pessoas, produtoras e resumo de avaliações;
- fato de desempenho financeiro e de engajamento;
- tabelas de associação N:N entre filmes, gêneros, produtoras e pessoas;

O schema corresponde aos nove arquivos CSV atuais da camada Diamond, com a
adição de `movie_reviews`: uma avaliação individual por linha, na escala 0–10.
A tabela aceita diretamente as colunas `sk_movie_review_id`, `sk_movie_id`,
`nome`, `nota` e `comentario` do CSV enviado separadamente. `created_at` é
gerado pelo banco. O contexto generativo não faz parte desta base.

### Carga inicial (`app/movies/seed.py`)

- Transação única: qualquer linha inválida desfaz a carga inteira e o erro
  indica `arquivo:linha`. Com o banco já populado, a carga é recusada; use
  `--reset` para recarregar do zero.
- As colunas esperadas vêm dos modelos ORM, e cada valor é convertido pelo tipo
  da coluna (inteiros serializados como `2375.0`, datas ISO, vazios → `NULL`).
- Parte dos textos (≈4,8 mil sinopses, além de alguns títulos, pessoas e
  produtoras) veio escapada duas vezes como CSV (`"Julia vê um ""filme""…`);
  a carga desfaz esse escape. Os 3 registros que viraram duplicatas depois da
  limpeza são mesclados, e as tabelas-ponte passam a apontar para o registro
  mantido.
- `dim_reviews.csv` **não é importado**: o resumo estava inconsistente com
  `movies_reviews.csv`. `dim_reviews` é recalculada a partir de `movie_reviews`,
  a fonte de verdade das avaliações (escala 0–10).
- Todo filme tem exatamente uma linha em `dim_reviews` (quantidade 0 quando não
  há avaliações) e em `fact_movies_performance`. Essa invariante permite
  ordenar o catálogo por popularidade e por nota direto pelos índices
  (migração `0002`), em poucos milissegundos.

As tabelas são criadas exclusivamente pelo Alembic. Para evoluir os modelos,
crie uma revisão e aplique-a:

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "descreva a alteração"
.venv/bin/alembic upgrade head
```

O banco padrão é SQLite local em `backend/rocketlab.db`. Ajuste
`DATABASE_URL` no arquivo `.env` para usar outro banco compatível.
