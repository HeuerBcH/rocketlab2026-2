import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.movies.models import DimPerson, MovieReview

MOVIES_URL = "/api/v1/movies"

pytestmark = pytest.mark.usefixtures("catalog")


@pytest.fixture
def client(admin_client: httpx.AsyncClient) -> httpx.AsyncClient:
    """Toda escrita exige login: os testes deste módulo usam o cliente autenticado."""

    return admin_client


def new_movie(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "titulo": "Ainda Estou Aqui",
        "ano_lancamento": 2024,
        "generos": ["Drama"],
        "diretores": ["Walter Salles"],
        "sinopse": "Uma mulher reconstrói a vida após o desaparecimento do marido.",
        "data_lancamento": "2024-11-07",
        "duracao_minutos": 137,
        "status_filme": "Lançado",
        "url_poster": "https://image.tmdb.org/t/p/w500/poster.jpg",
    }
    payload.update(overrides)
    return payload


async def count_rows(sessions: async_sessionmaker[AsyncSession], sql: str) -> int:
    async with sessions() as db:
        return (await db.execute(text(sql))).scalar_one()


# --------------------------------------------------------------------------- #
# Cadastro
# --------------------------------------------------------------------------- #


async def test_create_movie_returns_full_detail(client: httpx.AsyncClient) -> None:
    response = await client.post(MOVIES_URL, json=new_movie())

    assert response.status_code == 201, response.text
    movie = response.json()
    assert response.headers["location"].endswith(f"{MOVIES_URL}/{movie['id']}")
    assert movie["id_filme"].startswith("local-")
    assert movie["titulo"] == "Ainda Estou Aqui"
    assert movie["data_lancamento"] == "2024-11-07"
    assert movie["duracao_minutos"] == 137
    assert movie["status_filme"] == "Lançado"
    assert movie["generos"] == [{"id": "g-Drama", "nome": "Drama"}]
    assert [person["nome"] for person in movie["diretores"]] == ["Walter Salles"]
    assert movie["avaliacao"] == {"media": None, "qtd_avaliacoes": 0}
    assert (await client.get(f"{MOVIES_URL}/{movie['id']}")).json() == movie


async def test_created_movie_appears_in_every_catalog_sort(client: httpx.AsyncClient) -> None:
    # Garante a invariante de um resumo por filme: a listagem usa INNER JOIN nos índices.
    await client.post(MOVIES_URL, json=new_movie())

    for sort in ("popularidade", "-media", "-avaliacoes", "titulo"):
        body = (await client.get(MOVIES_URL, params={"sort": sort})).json()
        assert body["total"] == 5
        assert "Ainda Estou Aqui" in [item["titulo"] for item in body["items"]], sort


async def test_create_movie_with_only_title(client: httpx.AsyncClient) -> None:
    # Só o título é NOT NULL no modelo; é o único campo obrigatório.
    response = await client.post(MOVIES_URL, json={"titulo": "  Filme   Mínimo "})

    assert response.status_code == 201, response.text
    movie = response.json()
    assert movie["titulo"] == "Filme Mínimo"
    assert (movie["ano_lancamento"], movie["sinopse"], movie["duracao_minutos"]) == (
        None,
        None,
        None,
    )
    assert (movie["generos"], movie["diretores"]) == ([], [])
    assert movie["desempenho"]["popularidade"] is None
    for sort in ("popularidade", "-ano", "ano", "-media"):
        titles = [
            item["titulo"]
            for item in (await client.get(MOVIES_URL, params={"sort": sort})).json()["items"]
        ]
        assert titles[-1] == "Filme Mínimo", sort  # campos nulos vão para o fim


async def test_create_movie_derives_year_from_release_date(client: httpx.AsyncClient) -> None:
    response = await client.post(
        MOVIES_URL, json={"titulo": "Só com data", "data_lancamento": "2019-03-15"}
    )

    assert (response.json()["ano_lancamento"], response.json()["data_lancamento"]) == (
        2019,
        "2019-03-15",
    )


async def test_create_movie_reuses_existing_director_ignoring_accents(
    client: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    response = await client.post(
        MOVIES_URL, json=new_movie(diretores=["jose padilha", "Nova Diretora", "NOVA DIRETORA"])
    )

    directors = response.json()["diretores"]
    assert [(p["id"], p["nome"]) for p in directors][0] == ("p-tropa", "José Padilha")
    assert [p["nome"] for p in directors] == ["José Padilha", "Nova Diretora"]
    async with sessions() as db:
        total = await db.scalar(
            select(func.count()).where(DimPerson.nome_pessoa.in_(["jose padilha", "José Padilha"]))
        )
    assert total == 1


async def test_create_movie_reuses_existing_genre_ignoring_case_and_accents(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(MOVIES_URL, json=new_movie(generos=["animacao", "DRAMA"]))

    assert response.json()["generos"] == [
        {"id": "g-Animação", "nome": "Animação"},
        {"id": "g-Drama", "nome": "Drama"},
    ]
    genres = (await client.get("/api/v1/genres")).json()
    assert [genre["nome"] for genre in genres] == ["Animação", "Aventura", "Drama"]


async def test_create_movie_creates_new_genre_once(client: httpx.AsyncClient) -> None:
    first = await client.post(MOVIES_URL, json=new_movie(generos=["Biografia", "biografia"]))
    second = await client.post(MOVIES_URL, json=new_movie(titulo="Outro", generos=["  BIOGRAFIA "]))

    created = first.json()["generos"]
    assert [genre["nome"] for genre in created] == ["Biografia"]
    assert second.json()["generos"] == created
    genres = (await client.get("/api/v1/genres")).json()
    assert [genre["nome"] for genre in genres] == ["Animação", "Aventura", "Biografia", "Drama"]
    # O novo gênero já funciona como filtro do catálogo.
    filtered = await client.get(MOVIES_URL, params={"genre": created[0]["id"]})
    assert filtered.json()["total"] == 2


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"titulo": "   "}, "titulo"),
        ({"titulo": None}, "titulo"),
        ({"ano_lancamento": 1800}, "ano_lancamento"),
        ({"titulo": ""}, "titulo"),
        ({"generos": [f"Gênero {i}" for i in range(11)]}, "generos"),
        ({"diretores": None}, "diretores"),
        ({"diretores": ["  "]}, "diretores"),
        ({"generos": ["  "]}, "generos"),
        ({"generos": ["x" * 51]}, "generos"),
        ({"duracao_minutos": 0}, "duracao_minutos"),
        ({"status_filme": "Cancelado"}, "status_filme"),
        ({"url_poster": "ftp://poster.jpg"}, "url_poster"),
        ({"nota": 10}, "nota"),  # campo desconhecido
        ({"data_lancamento": "2023-01-01"}, "mesmo ano"),
    ],
)
async def test_create_movie_validation(
    client: httpx.AsyncClient, overrides: dict[str, object], message: str
) -> None:
    response = await client.post(MOVIES_URL, json=new_movie(**overrides))

    assert response.status_code == 422
    assert message in response.text
    assert (await client.get(MOVIES_URL)).json()["total"] == 4


# --------------------------------------------------------------------------- #
# Edição
# --------------------------------------------------------------------------- #


async def test_update_changes_only_sent_fields(client: httpx.AsyncClient) -> None:
    before = (await client.get(f"{MOVIES_URL}/cidade")).json()

    response = await client.patch(f"{MOVIES_URL}/cidade", json={"titulo": "Cidade de Deus (2002)"})

    assert response.status_code == 200, response.text
    after = response.json()
    assert after["titulo"] == "Cidade de Deus (2002)"
    assert {**after, "titulo": before["titulo"]} == before


async def test_update_replaces_genres_and_directors_keeping_cast(
    client: httpx.AsyncClient,
) -> None:
    response = await client.patch(
        f"{MOVIES_URL}/cidade",
        json={"generos": ["aventura", "Drama"], "diretores": ["Kátia Lund"]},
    )

    movie = response.json()
    assert [genre["nome"] for genre in movie["generos"]] == ["Aventura", "Drama"]
    assert [person["nome"] for person in movie["diretores"]] == ["Kátia Lund"]
    assert [person["nome"] for person in movie["elenco"]] == ["Alice Braga"]
    assert [person["nome"] for person in movie["roteiristas"]] == ["Bráulio Mantovani"]


async def test_update_can_clear_optional_fields(client: httpx.AsyncClient) -> None:
    response = await client.patch(
        f"{MOVIES_URL}/cidade",
        json={
            "sinopse": "  ",
            "ano_lancamento": None,
            "duracao_minutos": None,
            "url_poster": "",
            "generos": [],
            "diretores": [],
        },
    )

    movie = response.json()
    assert response.status_code == 200, response.text
    assert (movie["sinopse"], movie["ano_lancamento"]) == (None, None)
    assert (movie["duracao_minutos"], movie["url_poster"]) == (None, None)
    assert (movie["generos"], movie["diretores"]) == ([], [])
    # Elenco e roteiristas não são afetados ao limpar os diretores.
    assert [person["nome"] for person in movie["elenco"]] == ["Alice Braga"]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"titulo": None}, "titulo não pode ser nulo"),
        ({"generos": None}, "use [] para remover"),
        ({"diretores": None}, "use [] para remover"),
        ({"ano_lancamento": 1500}, "ano_lancamento"),
        ({"data_lancamento": "2010-05-01"}, "mesmo ano"),  # ano atual do filme é 2002
        ({"id_filme": "x"}, "id_filme"),
    ],
)
async def test_update_validation_keeps_movie_unchanged(
    client: httpx.AsyncClient, payload: dict[str, object], message: str
) -> None:
    before = (await client.get(f"{MOVIES_URL}/cidade")).json()

    response = await client.patch(f"{MOVIES_URL}/cidade", json=payload)

    assert response.status_code == 422
    assert message in response.text
    assert (await client.get(f"{MOVIES_URL}/cidade")).json() == before


async def test_update_year_and_date_together(client: httpx.AsyncClient) -> None:
    response = await client.patch(
        f"{MOVIES_URL}/cidade", json={"ano_lancamento": 2003, "data_lancamento": "2003-02-10"}
    )

    assert response.status_code == 200
    assert (response.json()["ano_lancamento"], response.json()["data_lancamento"]) == (
        2003,
        "2003-02-10",
    )


async def test_update_unknown_movie(client: httpx.AsyncClient) -> None:
    response = await client.patch(f"{MOVIES_URL}/nao-existe", json={"titulo": "X"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Filme não encontrado"}


# --------------------------------------------------------------------------- #
# Exclusão
# --------------------------------------------------------------------------- #


async def test_delete_movie_cascades_to_reviews_and_links(
    client: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    response = await client.delete(f"{MOVIES_URL}/cidade")

    assert response.status_code == 204
    assert response.content == b""
    assert (await client.get(f"{MOVIES_URL}/cidade")).status_code == 404
    assert (await client.get(MOVIES_URL)).json()["total"] == 3
    for table in (
        "movie_reviews",
        "dim_reviews",
        "fact_movies_performance",
        "bridge_movie_genre",
        "bridge_movie_person",
        "bridge_movie_company",
    ):
        sql = f"SELECT COUNT(*) FROM {table} WHERE sk_movie_id = 'cidade'"
        assert await count_rows(sessions, sql) == 0, table
    # Dimensões compartilhadas continuam existindo.
    assert await count_rows(sessions, "SELECT COUNT(*) FROM dim_genres") == 3
    assert await count_rows(sessions, "SELECT COUNT(*) FROM dim_people") == 6


async def test_delete_unknown_movie(client: httpx.AsyncClient) -> None:
    assert (await client.delete(f"{MOVIES_URL}/nao-existe")).status_code == 404


# --------------------------------------------------------------------------- #
# Avaliações
# --------------------------------------------------------------------------- #


async def test_add_review_updates_average(client: httpx.AsyncClient) -> None:
    response = await client.post(
        f"{MOVIES_URL}/cidade/reviews",
        json={"nome": "  Ana  Clara ", "nota": 5, "comentario": " Bom, mas longo. "},
    )

    assert response.status_code == 201, response.text
    review = response.json()
    assert review["nome"] == "Ana Clara"
    assert review["comentario"] == "Bom, mas longo."
    assert review["nota"] == 5.0
    assert review["created_at"].endswith("Z")
    # Notas anteriores: 9 e 7. Nova média: (9 + 7 + 5) / 3 = 7.
    assert review["avaliacao"] == {"media": 7.0, "qtd_avaliacoes": 3}

    detail = (await client.get(f"{MOVIES_URL}/cidade")).json()
    assert detail["avaliacao"] == {"media": 7.0, "qtd_avaliacoes": 3}
    history = (await client.get(f"{MOVIES_URL}/cidade/reviews")).json()
    assert history["total"] == 3
    assert history["items"][0]["id"] == review["id"]  # mais recente primeiro


async def test_first_review_of_movie_and_catalog_ranking(client: httpx.AsyncClient) -> None:
    response = await client.post(
        f"{MOVIES_URL}/pokemon/reviews",
        json={"nome": "Leo", "nota": 10, "comentario": "Clássico!"},
    )

    assert response.json()["avaliacao"] == {"media": 10.0, "qtd_avaliacoes": 1}
    ranking = (await client.get(MOVIES_URL, params={"sort": "-media"})).json()["items"]
    assert [item["titulo"] for item in ranking[:2]] == ["Tropa de Elite", "Pokémon: O Filme"]


async def test_review_on_newly_created_movie(client: httpx.AsyncClient) -> None:
    movie_id = (await client.post(MOVIES_URL, json=new_movie())).json()["id"]

    response = await client.post(
        f"{MOVIES_URL}/{movie_id}/reviews", json={"nome": "Bia", "nota": 9.5, "comentario": "Uau"}
    )

    assert response.json()["avaliacao"] == {"media": 9.5, "qtd_avaliacoes": 1}


@pytest.mark.parametrize(("nota", "expected"), [(0, 0.0), (10, 10.0), (7.26, 7.3)])
async def test_review_score_bounds_and_precision(
    client: httpx.AsyncClient, nota: float, expected: float
) -> None:
    response = await client.post(
        f"{MOVIES_URL}/lobo/reviews", json={"nome": "Caio", "nota": nota, "comentario": "Ok"}
    )

    assert response.status_code == 201
    assert response.json()["nota"] == expected


@pytest.mark.parametrize(
    "payload",
    [
        {"nome": "Caio", "nota": -0.1, "comentario": "Ruim"},
        {"nome": "Caio", "nota": 10.1, "comentario": "Ótimo"},
        {"nome": "Caio", "nota": "dez", "comentario": "Ótimo"},
        {"nome": "Caio", "comentario": "Sem nota"},
        {"nome": "   ", "nota": 5, "comentario": "Sem nome"},
        {"nome": "Caio", "nota": 5, "comentario": "   "},
        {"nome": "Caio", "nota": 5, "comentario": "x" * 4001},
        {"nome": "Caio", "nota": 5, "comentario": "Ok", "created_at": "2020-01-01"},
    ],
)
async def test_review_validation(
    client: httpx.AsyncClient,
    sessions: async_sessionmaker[AsyncSession],
    payload: dict[str, object],
) -> None:
    response = await client.post(f"{MOVIES_URL}/lobo/reviews", json=payload)

    assert response.status_code == 422
    async with sessions() as db:
        total = await db.scalar(
            select(func.count()).select_from(MovieReview).where(MovieReview.sk_movie_id == "lobo")
        )
    assert total == 1


async def test_review_for_unknown_movie(client: httpx.AsyncClient) -> None:
    response = await client.post(
        f"{MOVIES_URL}/nao-existe/reviews", json={"nome": "Caio", "nota": 5, "comentario": "Ok"}
    )

    assert response.status_code == 404


async def test_update_imported_movie_without_genre_or_director(
    client: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    # ~20 mil filmes importados não têm gênero/diretor; editar outros campos deve funcionar.
    async with sessions() as db:
        await db.execute(text("DELETE FROM bridge_movie_genre WHERE sk_movie_id = 'lobo'"))
        await db.execute(text("DELETE FROM bridge_movie_person WHERE sk_movie_id = 'lobo'"))
        await db.commit()

    response = await client.patch(f"{MOVIES_URL}/lobo", json={"titulo": "100% Lobo (2020)"})

    assert response.status_code == 200, response.text
    assert (response.json()["generos"], response.json()["diretores"]) == ([], [])
