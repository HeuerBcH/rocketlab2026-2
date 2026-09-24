# RocketLab Filmes

Sistema de avaliação de filmes inspirado no Letterboxd, desenvolvido para a
atividade de desenvolvimento do **RocketLab 2026.2**. O administrador navega por
um catálogo de ~95 mil filmes, vê detalhes e o histórico de avaliações de cada
um, gerencia o catálogo e publica notas e resenhas.

**Stack:** Vite + React + TypeScript · FastAPI (Python) · SQLite (SQLAlchemy +
Alembic)

---

## Sumário

- [Requisitos atendidos](#requisitos-atendidos)
- [Extras implementados](#extras-implementados)
- [Como executar](#como-executar)
- [Testes e qualidade](#testes-e-qualidade)
- [API](#api)
- [Decisões técnicas](#decisões-técnicas)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Banco de dados e migrações](#banco-de-dados-e-migrações)
- [Solução de problemas](#solução-de-problemas)

---

## Requisitos atendidos

| Requisito da atividade | Como foi atendido |
|---|---|
| Cadastrar filmes (título, diretor, ano, gênero, sinopse) | Tela **+ Novo filme**, com sugestões de gêneros e diretores já existentes · `POST /movies` |
| Catálogo paginado | Grade responsiva com paginação · `GET /movies?page=&page_size=` |
| Detalhes + lista de avaliações | Página do filme com ficha técnica completa e histórico paginado de avaliações |
| Buscar filmes por barra de pesquisa | Busca por **título ou diretor**, sem diferenciar acentos nem maiúsculas (`pokemon` encontra `Pokémon`) |
| Remover e atualizar filmes | Edição com formulário pré-preenchido; exclusão com confirmação · `PATCH` / `DELETE /movies/{id}` |
| Adicionar avaliação (nota + resenha) | Formulário no detalhe do filme; **nota de 0 a 10**, conforme os models |
| Média geral de cada filme | Nos cards do catálogo e em destaque no detalhe; atualizada na hora ao publicar uma avaliação |

## Extras implementados

- **Autenticação do administrador (JWT).** Leitura pública, escrita só com
  login. O botão **Authorize** do Swagger funciona com usuário e senha.
- **Filtros e ordenação:** gênero, faixa de ano; mais populares, maior média,
  mais avaliados, mais recentes, título. O estado fica na URL, então
  voltar/avançar e links compartilhados preservam a busca.
- **Caching de consultas** com TanStack Query. Páginas já visitadas abrem na
  hora, e cada escrita atualiza só o que mudou.
- **Testes automatizados:** 125 no backend (pytest) e 57 no frontend (Vitest +
  Testing Library).
- **Responsividade:** a grade vai de 2 colunas no celular a 6 no desktop.
- **Tratamento dos dados de origem:** limpeza dos CSVs, correção das médias e
  mesclagem de duplicatas (detalhes em
  [Decisões técnicas](#decisões-técnicas)).
- **Cliente de API tipado** a partir do OpenAPI do backend: frontend e backend
  compartilham o mesmo contrato, verificado pelo compilador.

---

## Como executar

**Pré-requisitos:** Python 3.11+ e Node.js 20+.

Rode o **backend** e o **frontend** em **dois terminais separados**. Os CSVs da
atividade já acompanham o repositório em [`data/`](data/README.md).

### 1. Backend (terminal 1)

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

A carga só é necessária na primeira vez. Nas próximas, basta o último comando
(`uvicorn`).

### 2. Frontend (terminal 2)

```bash
cd frontend
npm install
cp .env.example .env          # Windows: Copy-Item .env.example .env
npm run dev
```

### 3. Acessar

| O quê | Endereço |
|---|---|
| Aplicação | http://localhost:5173 |
| Documentação da API (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

**Login do administrador** (credenciais de desenvolvimento do `.env.example`):

| Usuário | Senha |
|---|---|
| `admin` | `rocketlab123` |

Sem login dá para navegar, buscar e ver detalhes e avaliações. Para cadastrar,
editar, excluir ou avaliar, clique em **Entrar** no topo da página. No Swagger,
use o botão **Authorize**.

Para trocar a senha, gere um novo hash e cole em `ADMIN_PASSWORD_HASH` no
`backend/.env`, entre aspas simples:

```bash
.venv/bin/python -m app.auth.hash_password     # Windows: .venv\Scripts\python -m app.auth.hash_password
```

---

## Testes e qualidade

| Onde | Comando | O que roda |
|---|---|---|
| `backend/` | `.venv/bin/pytest` (Windows: `.venv\Scripts\pytest`) | 125 testes: carga, API de leitura e escrita, autenticação |
| `backend/` | `.venv/bin/ruff check .` | Lint |
| `backend/` | `.venv/bin/alembic check` | Confere se os models e as migrações estão em sincronia |
| `frontend/` | `npm test` | 57 testes: telas, fluxos, formulários, sessão |
| `frontend/` | `npm run typecheck` · `npm run lint` | TypeScript estrito · oxlint |
| `frontend/` | `npm run build` | Build de produção em `dist/` |

Os testes do backend usam um banco temporário criado pelas próprias migrações
do Alembic, então também validam o schema. Os do frontend simulam a API e
percorrem os fluxos como um usuário: buscar, avaliar, cadastrar, editar,
excluir, entrar e sair.

---

## API

Base: `http://localhost:8000/api/v1`. A documentação interativa completa está
em `/docs`.

| Método | Rota | Descrição | Login |
|---|---|---|---|
| `GET` | `/movies` | Catálogo paginado. Parâmetros: `page`, `page_size` (≤100), `q`, `genre`, `year_from`, `year_to`, `sort` | — |
| `GET` | `/movies/{id}` | Detalhe completo: gêneros, direção, roteiro, elenco, produtoras, desempenho, média | — |
| `GET` | `/movies/{id}/reviews` | Avaliações do filme, mais recentes primeiro (paginado) | — |
| `GET` | `/genres` | Gêneros disponíveis | — |
| `GET` | `/people?tipo=Diretor&q=` | Busca de pessoas (autocomplete) | — |
| `POST` | `/movies` | Cadastra um filme | ✅ |
| `PATCH` | `/movies/{id}` | Atualiza só os campos enviados | ✅ |
| `DELETE` | `/movies/{id}` | Remove o filme e suas avaliações | ✅ |
| `POST` | `/movies/{id}/reviews` | Nova avaliação (0 a 10); devolve a média recalculada | ✅ |
| `POST` | `/auth/token` | Login (formulário OAuth2: `username`, `password`) → JWT | — |
| `GET` | `/auth/me` | Usuário da sessão atual | ✅ |

Respostas de erro seguem o padrão do FastAPI (`{"detail": ...}`):

- `404` para filme inexistente;
- `422` para dados inválidos, com a mensagem do campo;
- `401` para escrita sem login ou com token expirado.

---

## Decisões técnicas

**Escala de notas: 0 a 10.** O enunciado fala em 1 a 5 estrelas, mas a
observação da atividade manda seguir os models, que definem 0 a 10. O formulário
aceita meio ponto e mostra estrelas como atalho visual, em que cada estrela vale
2 pontos.

**Campos obrigatórios seguem o modelo de dados.** No cadastro, só o **título** é
obrigatório, porque é a única coluna `NOT NULL` em `dim_movies`. Os demais
campos são validados quando preenchidos. O "(ex: título, diretor, ano, gênero,
sinopse)" do enunciado lista os campos que o cadastro oferece, e todos estão
disponíveis. Os dados reais confirmam a escolha: cerca de 20 mil filmes
importados não têm gênero e 16 mil não têm diretor. A avaliação exige nome, nota
e comentário, as três colunas `NOT NULL` de `movie_reviews`.

**Gêneros e diretores sem duplicatas.** Os dois são informados pelo nome e
reaproveitados quando já existem, sem diferenciar acentos nem maiúsculas:
`jose padilha` usa o `José Padilha` existente e `drama` usa `Drama`. Um registro
novo só é criado se o nome realmente não existir. Os gêneros do dataset estão em
inglês; a tela os mostra em português, e digitar `Ação` reaproveita `Action` em
vez de criar outro gênero.

**Edição parcial.** O formulário de edição envia só os campos alterados. Assim,
filmes importados sem gênero ou diretor continuam editáveis, e nenhum dado que o
administrador não tocou é sobrescrito.

**Tratamento dos CSVs** ([`app/movies/seed.py`](backend/app/movies/seed.py)):

- **Carga atômica.** Qualquer linha inválida desfaz tudo, e o erro indica
  `arquivo:linha`.
- **Escape duplo desfeito.** Cerca de 4,8 mil sinopses, além de alguns títulos,
  pessoas e produtoras, vieram escapadas duas vezes como CSV
  (`"Julia vê um ""filme""…`). A carga corrige isso, e os 3 registros que
  viraram duplicatas após a limpeza são mesclados.
- **Médias recalculadas.** O `dim_reviews.csv` estava inconsistente com as
  avaliações: o resumo não batia com as notas em 630 dos primeiros 1.923 filmes
  com avaliações conferidos, e cerca de 13 mil filmes avaliados não tinham linha
  de resumo. Por isso o resumo é **recalculado** a partir de `movie_reviews`, a
  fonte de verdade.

**Média sempre correta.** Cada nova avaliação recalcula quantidade e média no
banco, na mesma transação da gravação. O valor é recalculado, não somado aos
poucos, então nunca acumula erro.

**Desempenho com 95 mil filmes.** Todo filme tem exatamente uma linha de resumo
de avaliações e uma de desempenho, e há índices compostos (migração `0002`) nas
colunas de ordenação. Com isso, o catálogo ordenado por popularidade ou por
média responde em **~5 ms**, contra ~700 ms sem os índices. A busca, que ignora
acentos, responde em ~150 ms. No frontend, a busca espera 300 ms sem digitação
antes de consultar a API, e o cache evita repetir consultas.

**Autenticação.** O sistema tem um único usuário, o administrador, configurado
pelo `.env`, sem tabela de usuários:

- a senha é guardada só como hash **Argon2**;
- o login segue o **OAuth2 password flow** do FastAPI e devolve um JWT com
  expiração;
- usuário errado e senha errada recebem a mesma resposta, sem revelar qual
  falhou;
- no frontend, o token expirado ou recusado encerra a sessão automaticamente, e
  as rotas de cadastro e edição redirecionam para o login.

---

## Estrutura do projeto

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/        # composição dos routers
│   │   ├── auth/          # login JWT, hash de senha, dependência de admin
│   │   ├── core/          # configurações, logging, normalização de texto
│   │   ├── db/            # Base ORM, engine e sessões
│   │   └── movies/        # models, schemas, repository (consultas),
│   │                      # service (regras de escrita), router e carga (seed)
│   ├── migrations/        # revisões Alembic (schema + índices)
│   └── tests/
├── data/                  # CSVs da atividade
└── frontend/
    └── src/
        ├── api/           # cliente tipado (OpenAPI) e hooks do TanStack Query
        ├── app/           # providers e rotas
        ├── auth/          # sessão, login, rotas protegidas
        ├── components/    # componentes de interface
        ├── hooks/         # hooks utilitários
        ├── lib/           # formatação, gêneros, regras do formulário
        └── pages/         # telas
```

---

## Banco de dados e migrações

O modelo usa um **esquema estrela**:

- dimensões de filmes, gêneros, pessoas, produtoras e resumo de avaliações;
- fato de desempenho financeiro e de engajamento;
- tabelas-ponte N:N entre filmes e gêneros, produtoras e pessoas;
- `movie_reviews`, com uma avaliação por linha.

As tabelas são criadas **exclusivamente pelo Alembic**. Para evoluir os models:

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "descreva a alteração"
.venv/bin/alembic upgrade head
```

O banco padrão é `backend/rocketlab.db`. Para outro banco SQLite, ajuste
`DATABASE_URL` no `backend/.env`.

---

## Solução de problemas

| Sintoma | Causa e solução |
|---|---|
| "Não foi possível conectar à API" no frontend | O backend não está rodando. Suba-o no terminal 1 (`uvicorn`) e recarregue a página. |
| Erro de CORS no console do navegador | Acesse o frontend por `http://localhost:5173` (não `127.0.0.1`). Para outra origem, ajuste `BACKEND_CORS_ORIGINS` no `backend/.env`. |
| "O banco já contém filmes" ao rodar a carga | A carga já foi feita. Para recarregar do zero: `python -m app.movies.seed --data-dir ../data --reset`. |
| "Banco sem as tabelas do catálogo" | Rode `alembic upgrade head` antes da carga. |
| `ModuleNotFoundError` (jwt, pwdlib…) após atualizar o projeto | Reinstale as dependências do backend: `pip install -e ".[dev]"`. |
| Login responde "Autenticação não configurada" | Faltam `ADMIN_PASSWORD_HASH` ou `AUTH_SECRET_KEY` no `backend/.env`. Copie-os do `.env.example`. |
