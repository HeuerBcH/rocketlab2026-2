"""Regras de escrita do catálogo: cadastro, edição, exclusão e avaliações.

Invariante mantida aqui (e pela carga): todo filme tem exatamente uma linha em
``fact_movies_performance`` e uma em ``dim_reviews``. A listagem depende disso
para ordenar direto pelos índices.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text import normalize_text
from app.movies import repository
from app.movies.models import (
    DimGenre,
    DimMovie,
    DimPerson,
    DimReview,
    FactMoviePerformance,
    MovieReview,
)
from app.movies.schemas import MovieCreate, MovieUpdate, ReviewCreate

DIRECTOR = "Diretor"

# Campos escalares copiados diretamente do payload para o filme.
SCALAR_FIELDS = (
    "titulo",
    "ano_lancamento",
    "sinopse",
    "data_lancamento",
    "duracao_minutos",
    "status_filme",
    "url_poster",
    "url_backdrop",
)


class MovieNotFoundError(Exception):
    """O filme informado não existe."""


class InvalidMovieError(Exception):
    """Dados válidos no formato, mas inconsistentes entre si (ex.: data x ano)."""


# --------------------------------------------------------------------------- #
# Resolução de gêneros e diretores
# --------------------------------------------------------------------------- #


async def resolve_genres(db: AsyncSession, names: Sequence[str]) -> list[DimGenre]:
    """Reaproveita gêneros existentes (ignorando acentos e maiúsculas) ou cria novos.

    A comparação normalizada evita duplicatas como "drama" ao lado de "Drama".
    O catálogo de gêneros é pequeno (dezenas), então é carregado inteiro.
    """

    if not names:
        return []
    existing = {
        normalize_text(genre.nome_genero): genre
        for genre in await db.scalars(select(DimGenre).order_by(DimGenre.nome_genero))
    }
    return [existing.get(normalize_text(name)) or DimGenre(nome_genero=name) for name in names]


async def resolve_directors(db: AsyncSession, names: Sequence[str]) -> list[DimPerson]:
    """Reaproveita diretores existentes (ignorando acentos e maiúsculas) ou cria novos."""

    if not names:
        return []

    keys = {normalize_text(name): name for name in names}
    existing: dict[str | None, DimPerson] = {}

    # 1) Nome exato (caso comum, vindo do autocomplete): usa o índice de nome.
    exact = await db.scalars(
        select(DimPerson).where(
            DimPerson.tipo_pessoa == DIRECTOR, DimPerson.nome_pessoa.in_(list(keys.values()))
        )
    )
    for person in exact:
        existing[normalize_text(person.nome_pessoa)] = person

    # 2) Só para o que faltou: comparação sem acentos/maiúsculas (varre as pessoas).
    pending = [key for key in keys if key not in existing]
    if pending:
        similar = await db.scalars(
            select(DimPerson)
            .where(
                DimPerson.tipo_pessoa == DIRECTOR,
                func.normalize_text(DimPerson.nome_pessoa).in_(pending),
            )
            .order_by(DimPerson.nome_pessoa)
        )
        for person in similar:
            existing.setdefault(normalize_text(person.nome_pessoa), person)

    return [
        existing.get(key) or DimPerson(nome_pessoa=name, tipo_pessoa=DIRECTOR)
        for key, name in keys.items()
    ]


def apply_release_date(movie: DimMovie) -> None:
    """Deriva o ano da data quando só ela foi informada; rejeita data e ano divergentes."""

    if movie.data_lancamento is not None and movie.ano_lancamento is None:
        movie.ano_lancamento = movie.data_lancamento.year
    if (
        movie.data_lancamento is not None
        and movie.ano_lancamento is not None
        and movie.data_lancamento.year != movie.ano_lancamento
    ):
        raise InvalidMovieError("data_lancamento deve ser do mesmo ano que ano_lancamento")


# --------------------------------------------------------------------------- #
# Filmes
# --------------------------------------------------------------------------- #


async def create_movie(db: AsyncSession, payload: MovieCreate) -> DimMovie:
    movie = DimMovie(
        # id_filme é o ID do TMDB nos dados importados; cadastros locais ganham prefixo próprio.
        id_filme=f"local-{uuid4().hex}",
        **payload.model_dump(include=set(SCALAR_FIELDS)),
        genres=await resolve_genres(db, payload.generos),
        people=await resolve_directors(db, payload.diretores),
        performance=FactMoviePerformance(),
        reviews_summary=DimReview(qtd_avaliacoes_usuarios=0, nota_media_usuarios=None),
    )
    apply_release_date(movie)
    db.add(movie)
    await db.commit()
    return await reload_movie(db, movie.sk_movie_id)


async def update_movie(db: AsyncSession, movie_id: str, payload: MovieUpdate) -> DimMovie:
    movie = await repository.get_movie(db, movie_id)
    if movie is None:
        raise MovieNotFoundError(movie_id)

    changes = payload.model_dump(include=set(SCALAR_FIELDS), exclude_unset=True)
    for field, value in changes.items():
        setattr(movie, field, value)
    if payload.generos is not None:
        movie.genres = await resolve_genres(db, payload.generos)
    if payload.diretores is not None:
        # Troca só os diretores; elenco e roteiristas continuam vinculados.
        others = [person for person in movie.people if person.tipo_pessoa != DIRECTOR]
        movie.people = others + await resolve_directors(db, payload.diretores)

    apply_release_date(movie)
    await db.commit()
    return await reload_movie(db, movie_id)


async def delete_movie(db: AsyncSession, movie_id: str) -> None:
    # DELETE direto: o ON DELETE CASCADE do banco remove avaliações, resumos e
    # vínculos numa única instrução, sem carregar nada na memória.
    result = await db.execute(delete(DimMovie).where(DimMovie.sk_movie_id == movie_id))
    if result.rowcount == 0:
        await db.rollback()
        raise MovieNotFoundError(movie_id)
    await db.commit()


async def reload_movie(db: AsyncSession, movie_id: str) -> DimMovie:
    movie = await repository.get_movie(db, movie_id, refresh=True)
    if movie is None:  # pragma: no cover - acabou de ser gravado na mesma sessão
        raise MovieNotFoundError(movie_id)
    return movie


# --------------------------------------------------------------------------- #
# Avaliações
# --------------------------------------------------------------------------- #


async def add_review(
    db: AsyncSession, movie_id: str, payload: ReviewCreate
) -> tuple[MovieReview, DimReview]:
    """Grava a avaliação e recalcula o resumo do filme na mesma transação."""

    if not await repository.movie_exists(db, movie_id):
        raise MovieNotFoundError(movie_id)

    review = MovieReview(
        sk_movie_id=movie_id,
        nome=payload.nome,
        nota=payload.nota,
        comentario=payload.comentario,
        # Com microssegundos, avaliações feitas no mesmo segundo mantêm a ordem.
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(review)
    await db.flush()

    # Recalcula a partir das avaliações (fonte de verdade) em vez de somar
    # incrementalmente: o resumo nunca acumula erro nem diverge.
    count, average = (
        await db.execute(
            select(func.count(), func.avg(MovieReview.nota)).where(
                MovieReview.sk_movie_id == movie_id
            )
        )
    ).one()
    updated = await db.execute(
        update(DimReview)
        .where(DimReview.sk_movie_id == movie_id)
        .values(qtd_avaliacoes_usuarios=count, nota_media_usuarios=average)
    )
    if updated.rowcount == 0:
        # Autocorreção caso a invariante tenha sido quebrada fora da aplicação.
        db.add(
            DimReview(
                sk_movie_id=movie_id, qtd_avaliacoes_usuarios=count, nota_media_usuarios=average
            )
        )
    await db.commit()

    summary = await db.scalar(
        select(DimReview)
        .where(DimReview.sk_movie_id == movie_id)
        .execution_options(populate_existing=True)
    )
    assert summary is not None
    return review, summary
