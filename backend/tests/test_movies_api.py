import httpx
import pytest

MOVIES_URL = "/api/v1/movies"


def titles(response: httpx.Response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["titulo"] for item in response.json()["items"]]


# --------------------------------------------------------------------------- #
# Catálogo: paginação e ordenação
# --------------------------------------------------------------------------- #


@pytest.mark.usefixtures("catalog")
async def test_list_movies_defaults_to_popularity_with_nulls_last(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get(MOVIES_URL)

    assert titles(response) == ["Pokémon: O Filme", "Cidade de Deus", "100% Lobo", "Tropa de Elite"]
    body = response.json()
    assert (body["total"], body["page"], body["page_size"], body["pages"]) == (4, 1, 20, 1)


@pytest.mark.usefixtures("catalog")
async def test_list_item_contains_card_data(client: httpx.AsyncClient) -> None:
    items = (await client.get(MOVIES_URL, params={"sort": "titulo"})).json()["items"]

    assert items[1] == {
        "id": "cidade",
        "titulo": "Cidade de Deus",
        "ano_lancamento": 2002,
        "url_poster": None,
        "generos": ["Drama"],
        "avaliacao": {"media": 8.0, "qtd_avaliacoes": 2},
    }
    assert items[2]["avaliacao"] == {"media": None, "qtd_avaliacoes": 0}
    assert items[2]["generos"] == ["Animação", "Aventura"]


@pytest.mark.usefixtures("catalog")
@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("titulo", ["100% Lobo", "Cidade de Deus", "Pokémon: O Filme", "Tropa de Elite"]),
        ("-ano", ["100% Lobo", "Tropa de Elite", "Cidade de Deus", "Pokémon: O Filme"]),
        ("ano", ["Pokémon: O Filme", "Cidade de Deus", "Tropa de Elite", "100% Lobo"]),
        ("-media", ["Tropa de Elite", "Cidade de Deus", "100% Lobo", "Pokémon: O Filme"]),
        ("-avaliacoes", ["Cidade de Deus", "Tropa de Elite", "100% Lobo", "Pokémon: O Filme"]),
    ],
)
async def test_list_movies_sorting(
    client: httpx.AsyncClient, sort: str, expected: list[str]
) -> None:
    assert titles(await client.get(MOVIES_URL, params={"sort": sort})) == expected


@pytest.mark.usefixtures("catalog")
async def test_list_movies_pagination(client: httpx.AsyncClient) -> None:
    first = await client.get(MOVIES_URL, params={"page_size": 3})
    second = await client.get(MOVIES_URL, params={"page_size": 3, "page": 2})
    beyond = await client.get(MOVIES_URL, params={"page_size": 3, "page": 3})

    assert len(titles(first)) == 3
    assert titles(second) == ["Tropa de Elite"]
    assert second.json()["pages"] == 2
    assert titles(beyond) == []
    assert beyond.json()["total"] == 4


@pytest.mark.usefixtures("catalog")
@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 0},
        {"page_size": 101},
        {"sort": "invalido"},
        {"year_from": 2010, "year_to": 2000},
    ],
)
async def test_list_movies_rejects_invalid_params(
    client: httpx.AsyncClient, params: dict[str, object]
) -> None:
    assert (await client.get(MOVIES_URL, params=params)).status_code == 422


# --------------------------------------------------------------------------- #
# Catálogo: busca e filtros
# --------------------------------------------------------------------------- #


@pytest.mark.usefixtures("catalog")
@pytest.mark.parametrize(
    ("q", "expected"),
    [
        ("pokemon", ["Pokémon: O Filme"]),  # ignora acentos
        ("CIDADE", ["Cidade de Deus"]),  # ignora maiúsculas
        ("de", ["100% Lobo", "Cidade de Deus", "Tropa de Elite"]),  # Lobo: diretor Stadermann
        ("padilha", ["Tropa de Elite"]),  # busca pelo diretor
        ("jose", ["Tropa de Elite"]),  # diretor com acento
        ("%", ["100% Lobo"]),  # curinga do LIKE tratado como texto
        ("_", []),
        ("inexistente", []),
        ("   ", ["100% Lobo", "Cidade de Deus", "Pokémon: O Filme", "Tropa de Elite"]),
    ],
)
async def test_search_by_title_or_director(
    client: httpx.AsyncClient, q: str, expected: list[str]
) -> None:
    response = await client.get(MOVIES_URL, params={"q": q, "sort": "titulo"})

    assert titles(response) == expected
    assert response.json()["total"] == len(expected)


@pytest.mark.usefixtures("catalog")
async def test_search_reports_total_across_pages(client: httpx.AsyncClient) -> None:
    params = {"q": "de", "page_size": 1, "sort": "titulo"}

    first = await client.get(MOVIES_URL, params=params)
    beyond = await client.get(MOVIES_URL, params={**params, "page": 5})

    assert titles(first) == ["100% Lobo"]
    assert (first.json()["total"], first.json()["pages"]) == (3, 3)
    assert titles(beyond) == []
    assert beyond.json()["total"] == 3


@pytest.mark.usefixtures("catalog")
async def test_filters_by_genre_and_year_combined_with_search(client: httpx.AsyncClient) -> None:
    by_genre = await client.get(MOVIES_URL, params={"genre": "g-Drama", "sort": "titulo"})
    by_year = await client.get(
        MOVIES_URL, params={"year_from": 2000, "year_to": 2010, "sort": "titulo"}
    )
    combined = await client.get(
        MOVIES_URL, params={"genre": "g-Animação", "year_from": 2000, "q": "lobo"}
    )

    assert titles(by_genre) == ["Cidade de Deus", "Tropa de Elite"]
    assert titles(by_year) == ["Cidade de Deus", "Tropa de Elite"]
    assert titles(combined) == ["100% Lobo"]


# --------------------------------------------------------------------------- #
# Detalhe e avaliações
# --------------------------------------------------------------------------- #


@pytest.mark.usefixtures("catalog")
async def test_get_movie_detail(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{MOVIES_URL}/cidade")

    assert response.status_code == 200
    movie = response.json()
    assert movie["titulo"] == "Cidade de Deus"
    assert movie["id_filme"] == "tmdb-cidade"
    assert movie["sinopse"] == "Sinopse de Cidade de Deus"
    assert movie["generos"] == [{"id": "g-Drama", "nome": "Drama"}]
    assert [p["nome"] for p in movie["diretores"]] == ["Fernando Meirelles"]
    assert [p["nome"] for p in movie["roteiristas"]] == ["Bráulio Mantovani"]
    assert [p["nome"] for p in movie["elenco"]] == ["Alice Braga"]
    assert movie["produtoras"] == ["O2 Filmes"]
    assert movie["desempenho"]["popularidade"] == 50.0
    assert movie["avaliacao"] == {"media": 8.0, "qtd_avaliacoes": 2}


async def test_get_movie_not_found(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{MOVIES_URL}/nao-existe")

    assert response.status_code == 404
    assert response.json() == {"detail": "Filme não encontrado"}


@pytest.mark.usefixtures("catalog")
async def test_list_reviews_newest_first_and_paginated(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{MOVIES_URL}/cidade/reviews", params={"page_size": 1})

    body = response.json()
    assert (body["total"], body["pages"]) == (2, 2)
    assert body["items"] == [
        {
            "id": "r-cidade-1",
            "nome": "Pessoa 1",
            "nota": 7.0,
            "comentario": "Comentário 1",
            "created_at": "2026-01-02T00:00:00Z",
        }
    ]


@pytest.mark.usefixtures("catalog")
async def test_list_reviews_of_movie_without_reviews(client: httpx.AsyncClient) -> None:
    body = (await client.get(f"{MOVIES_URL}/pokemon/reviews")).json()

    assert (body["items"], body["total"], body["pages"]) == ([], 0, 0)


async def test_list_reviews_of_unknown_movie(client: httpx.AsyncClient) -> None:
    assert (await client.get(f"{MOVIES_URL}/nao-existe/reviews")).status_code == 404


# --------------------------------------------------------------------------- #
# Gêneros e pessoas
# --------------------------------------------------------------------------- #


@pytest.mark.usefixtures("catalog")
async def test_list_genres_sorted(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/genres")

    assert [genre["nome"] for genre in response.json()] == ["Animação", "Aventura", "Drama"]


@pytest.mark.usefixtures("catalog")
async def test_search_people_by_type_and_name(client: httpx.AsyncClient) -> None:
    directors = await client.get("/api/v1/people", params={"tipo": "Diretor", "q": "jose"})
    everyone = await client.get("/api/v1/people", params={"q": "a", "limit": 2})

    assert directors.json() == [{"id": "p-tropa", "nome": "José Padilha", "tipo": "Diretor"}]
    assert len(everyone.json()) == 2
    assert (await client.get("/api/v1/people", params={"tipo": "Produtor"})).status_code == 422
