from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest

from tests.conftest import ADMIN_USERNAME, AUTH_SECRET_KEY, login

MOVIES_URL = "/api/v1/movies"
REVIEW = {"nome": "Ana", "nota": 8, "comentario": "Ok"}

# Toda operação de escrita, com o corpo mínimo válido.
WRITE_OPERATIONS = [
    ("POST", MOVIES_URL, {"titulo": "Novo"}),
    ("PATCH", f"{MOVIES_URL}/cidade", {"titulo": "Outro"}),
    ("DELETE", f"{MOVIES_URL}/cidade", None),
    ("POST", f"{MOVIES_URL}/cidade/reviews", REVIEW),
]


def token(**overrides: object) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": ADMIN_USERNAME,
        "aud": "rocketlab-admin",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    key = str(overrides.pop("key", AUTH_SECRET_KEY))
    return jwt.encode({**claims, **overrides}, key, algorithm="HS256")


async def test_login_returns_bearer_token_accepted_by_me(client: httpx.AsyncClient) -> None:
    response = await login(client)

    assert response.status_code == 200
    body = response.json()
    assert (body["token_type"], body["expires_in"]) == ("bearer", 3600)
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.json() == {"username": ADMIN_USERNAME}


@pytest.mark.parametrize(
    "data",
    [
        {"username": ADMIN_USERNAME, "password": "errada"},
        {"username": "outro", "password": "senha-de-teste"},
    ],
)
async def test_login_rejects_invalid_credentials_with_same_message(
    client: httpx.AsyncClient, data: dict[str, str]
) -> None:
    response = await client.post("/api/v1/auth/token", data=data)

    assert response.status_code == 401
    assert response.json() == {"detail": "Usuário ou senha inválidos"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_login_requires_form_fields(client: httpx.AsyncClient) -> None:
    assert (await client.post("/api/v1/auth/token", data={})).status_code == 422


@pytest.mark.usefixtures("catalog")
@pytest.mark.parametrize(("method", "url", "body"), WRITE_OPERATIONS)
async def test_writes_require_login(
    client: httpx.AsyncClient, method: str, url: str, body: dict | None
) -> None:
    response = await client.request(method, url, json=body)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    # Nada foi alterado.
    movie = (await client.get(f"{MOVIES_URL}/cidade")).json()
    assert (movie["titulo"], movie["avaliacao"]["qtd_avaliacoes"]) == ("Cidade de Deus", 2)
    assert (await client.get(MOVIES_URL)).json()["total"] == 4


@pytest.mark.usefixtures("catalog")
@pytest.mark.parametrize(("method", "url", "body"), WRITE_OPERATIONS)
async def test_writes_work_with_valid_token(
    client: httpx.AsyncClient, method: str, url: str, body: dict | None
) -> None:
    headers = {"Authorization": f"Bearer {token()}"}

    response = await client.request(method, url, json=body, headers=headers)

    assert response.status_code in (200, 201, 204), response.text


@pytest.mark.usefixtures("catalog")
@pytest.mark.parametrize(
    ("bad_token", "detail"),
    [
        (token(exp=datetime.now(UTC) - timedelta(seconds=1)), "Sessão expirada; entre novamente"),
        (token(key="x" * 32), "Token inválido"),  # assinado com outra chave
        (token(aud="outro-sistema"), "Token inválido"),
        (token(sub="intruso"), "Token inválido"),
        ("nao-e-um-jwt", "Token inválido"),
    ],
)
async def test_rejects_invalid_tokens(
    client: httpx.AsyncClient, bad_token: str, detail: str
) -> None:
    response = await client.post(
        MOVIES_URL, json={"titulo": "X"}, headers={"Authorization": f"Bearer {bad_token}"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": detail}


@pytest.mark.usefixtures("catalog")
async def test_reads_stay_public(client: httpx.AsyncClient) -> None:
    for url in (
        MOVIES_URL,
        f"{MOVIES_URL}/cidade",
        f"{MOVIES_URL}/cidade/reviews",
        "/api/v1/genres",
    ):
        assert (await client.get(url)).status_code == 200, url


async def test_login_reports_missing_server_configuration(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "")
    get_settings.cache_clear()

    response = await login(client)

    assert response.status_code == 503
    assert "ADMIN_PASSWORD_HASH" in response.json()["detail"]
