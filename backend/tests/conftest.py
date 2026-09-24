from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import password_hasher
from app.core.config import get_settings
from app.db.session import configure_sqlite_connection, get_db
from app.main import app
from app.movies.models import (
    DimCompany,
    DimGenre,
    DimMovie,
    DimPerson,
    DimReview,
    FactMoviePerformance,
    MovieReview,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "senha-de-teste"
ADMIN_PASSWORD_HASH = password_hasher().hash(ADMIN_PASSWORD)
AUTH_SECRET_KEY = "k" * 32


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Credenciais fixas de teste, independentes do backend/.env local."""

    monkeypatch.setenv("ADMIN_USERNAME", ADMIN_USERNAME)
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", ADMIN_PASSWORD_HASH)
    monkeypatch.setenv("AUTH_SECRET_KEY", AUTH_SECRET_KEY)
    monkeypatch.setenv("ACCESS_TOKEN_MINUTES", "60")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Banco SQLite temporário com o schema aplicado pelas migrações do Alembic."""

    path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{path.as_posix()}")
    get_settings.cache_clear()
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    yield path
    get_settings.cache_clear()


@pytest.fixture
async def sessions(db_path: Path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Fábrica de sessões ligada ao banco temporário, configurada como a da aplicação."""

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    configure_sqlite_connection(engine)
    yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    await engine.dispose()


@pytest.fixture
async def client(sessions: async_sessionmaker[AsyncSession]) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente HTTP da API usando o banco temporário."""

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.clear()


async def login(client: httpx.AsyncClient, password: str = ADMIN_PASSWORD) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/token", data={"username": ADMIN_USERNAME, "password": password}
    )


@pytest.fixture
async def admin_client(client: httpx.AsyncClient) -> httpx.AsyncClient:
    """Cliente já autenticado como administrador."""

    response = await login(client)
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


@dataclass
class MovieSpec:
    id: str
    titulo: str
    ano: int
    generos: list[str]
    diretor: str
    popularidade: float | None
    notas: list[float] = field(default_factory=list)


SPECS = [
    MovieSpec("cidade", "Cidade de Deus", 2002, ["Drama"], "Fernando Meirelles", 50.0, [9.0, 7.0]),
    MovieSpec(
        "pokemon", "Pokémon: O Filme", 1998, ["Animação", "Aventura"], "Kunihiko Yuyama", 80.0
    ),
    MovieSpec("lobo", "100% Lobo", 2020, ["Animação"], "Alexs Stadermann", 10.0, [4.0]),
    MovieSpec("tropa", "Tropa de Elite", 2007, ["Drama"], "José Padilha", None, [10.0]),
]


@pytest.fixture
async def catalog(sessions: async_sessionmaker[AsyncSession]) -> None:
    """Catálogo pequeno respeitando as invariantes da carga (um resumo por filme)."""

    async with sessions() as db:
        genres = {
            name: DimGenre(sk_genre_id=f"g-{name}", nome_genero=name)
            for name in ("Drama", "Animação", "Aventura")
        }
        extra_people = [
            DimPerson(sk_person_id="p-alice", nome_pessoa="Alice Braga", tipo_pessoa="Ator"),
            DimPerson(
                sk_person_id="p-braulio", nome_pessoa="Bráulio Mantovani", tipo_pessoa="Roteirista"
            ),
        ]
        for spec in SPECS:
            people = [
                DimPerson(
                    sk_person_id=f"p-{spec.id}", nome_pessoa=spec.diretor, tipo_pessoa="Diretor"
                )
            ]
            if spec.id == "cidade":
                people += extra_people
            movie = DimMovie(
                sk_movie_id=spec.id,
                id_filme=f"tmdb-{spec.id}",
                titulo=spec.titulo,
                ano_lancamento=spec.ano,
                sinopse=f"Sinopse de {spec.titulo}",
                genres=[genres[name] for name in spec.generos],
                people=people,
                companies=[DimCompany(sk_company_id="c-o2", nome_produtora="O2 Filmes")]
                if spec.id == "cidade"
                else [],
                performance=FactMoviePerformance(popularidade=spec.popularidade),
                reviews_summary=DimReview(
                    qtd_avaliacoes_usuarios=len(spec.notas),
                    nota_media_usuarios=sum(spec.notas) / len(spec.notas) if spec.notas else None,
                ),
                reviews=[
                    MovieReview(
                        sk_movie_review_id=f"r-{spec.id}-{index}",
                        nome=f"Pessoa {index}",
                        nota=nota,
                        comentario=f"Comentário {index}",
                        created_at=datetime(2026, 1, index + 1),
                    )
                    for index, nota in enumerate(spec.notas)
                ],
            )
            db.add(movie)
        await db.commit()
