"""Consultas ao banco do domínio de filmes.

Relações são sempre carregadas explicitamente (``selectinload``): com
SQLAlchemy assíncrono, acessar uma relação não carregada gera erro.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Select, func, select, union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.text import escape_like, normalize_text
from app.movies.models import (
    DimGenre,
    DimMovie,
    DimPerson,
    DimReview,
    FactMoviePerformance,
    MovieReview,
    bridge_movie_genre,
    bridge_movie_person,
)
from app.movies.schemas import MovieSort


@dataclass(frozen=True)
class MovieFilters:
    q: str | None = None
    genre_id: str | None = None
    year_from: int | None = None
    year_to: int | None = None


def contains_normalized(column: ColumnElement[str], term: str) -> ColumnElement[bool]:
    """Busca por substring ignorando acentos e maiúsculas."""

    pattern = f"%{escape_like(normalize_text(term) or '')}%"
    return func.normalize_text(column).like(pattern, escape="\\")


def has_search(filters: MovieFilters) -> bool:
    return bool(filters.q and filters.q.strip())


def movie_conditions(filters: MovieFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []

    if has_search(filters):
        term = filters.q.strip()
        # O conjunto de filmes encontrados (por título ou diretor) é calculado uma
        # única vez como subconsulta não correlacionada. Assim o SQLite ordena só os
        # resultados, em vez de testar a busca linha a linha enquanto percorre o
        # índice de ordenação.
        by_title = select(DimMovie.sk_movie_id).where(contains_normalized(DimMovie.titulo, term))
        by_director = (
            select(bridge_movie_person.c.sk_movie_id)
            .join(DimPerson, DimPerson.sk_person_id == bridge_movie_person.c.sk_person_id)
            .where(
                DimPerson.tipo_pessoa == "Diretor",
                contains_normalized(DimPerson.nome_pessoa, term),
            )
        )
        conditions.append(DimMovie.sk_movie_id.in_(union(by_title, by_director)))

    if filters.genre_id:
        conditions.append(
            DimMovie.sk_movie_id.in_(
                select(bridge_movie_genre.c.sk_movie_id).where(
                    bridge_movie_genre.c.sk_genre_id == filters.genre_id
                )
            )
        )
    if filters.year_from is not None:
        conditions.append(DimMovie.ano_lancamento >= filters.year_from)
    if filters.year_to is not None:
        conditions.append(DimMovie.ano_lancamento <= filters.year_to)

    return conditions


def apply_sort(statement: Select, sort: MovieSort) -> Select:
    """Aplica a ordenação sempre com desempate pela chave, deixando a paginação estável.

    Todo filme tem exatamente uma linha em ``fact_movies_performance`` e em
    ``dim_reviews`` (garantido pela carga e pelo cadastro). Com INNER JOIN e
    desempate por colunas da mesma tabela, o SQLite percorre o índice composto
    e para no LIMIT, sem ordenar o catálogo inteiro. Em ordem DESC o SQLite já
    coloca NULL por último.
    """

    match sort:
        case MovieSort.POPULARIDADE:
            return statement.join(DimMovie.performance).order_by(
                FactMoviePerformance.popularidade.desc(),
                FactMoviePerformance.sk_movie_id.desc(),
            )
        case MovieSort.MEDIA:
            return statement.join(DimMovie.reviews_summary).order_by(
                DimReview.nota_media_usuarios.desc(),
                DimReview.qtd_avaliacoes_usuarios.desc(),
                DimReview.sk_movie_id.desc(),
            )
        case MovieSort.AVALIACOES:
            return statement.join(DimMovie.reviews_summary).order_by(
                DimReview.qtd_avaliacoes_usuarios.desc(),
                DimReview.nota_media_usuarios.desc(),
                DimReview.sk_movie_id.desc(),
            )
        case MovieSort.TITULO:
            return statement.order_by(DimMovie.titulo, DimMovie.sk_movie_id)
        case MovieSort.ANO_DESC:
            return statement.order_by(
                DimMovie.ano_lancamento.desc(), DimMovie.titulo, DimMovie.sk_movie_id
            )
        case MovieSort.ANO_ASC:
            return statement.order_by(
                DimMovie.ano_lancamento.asc().nulls_last(), DimMovie.titulo, DimMovie.sk_movie_id
            )


async def list_movies(
    db: AsyncSession,
    filters: MovieFilters,
    sort: MovieSort,
    page: int,
    page_size: int,
) -> tuple[Sequence[DimMovie], int]:
    conditions = movie_conditions(filters)
    count_statement = select(func.count()).select_from(DimMovie).where(*conditions)
    options = (selectinload(DimMovie.genres), selectinload(DimMovie.reviews_summary))
    offset = (page - 1) * page_size

    if not has_search(filters):
        # Sem busca, a contagem é barata e a página sai direto do índice de ordenação.
        total = await db.scalar(count_statement) or 0
        statement = apply_sort(select(DimMovie).where(*conditions), sort)
        movies = await db.scalars(statement.options(*options).offset(offset).limit(page_size))
        return movies.all(), total

    # Com busca, a parte cara é encontrar os filmes. COUNT(*) OVER () devolve o
    # total junto com a página, sem repetir a busca numa segunda consulta.
    statement = apply_sort(
        select(DimMovie, func.count().over().label("total")).where(*conditions), sort
    )
    rows = (await db.execute(statement.options(*options).offset(offset).limit(page_size))).all()
    if rows:
        return [row[0] for row in rows], rows[0].total
    # Página além do fim: não há linhas para carregar o total, então conta à parte.
    return [], await db.scalar(count_statement) or 0


async def get_movie(db: AsyncSession, movie_id: str, *, refresh: bool = False) -> DimMovie | None:
    """Carrega o filme com todas as relações exibidas no detalhe.

    ``refresh=True`` sobrescreve o que a sessão já tiver em memória; é usado
    depois de uma escrita para devolver o estado gravado no banco.
    """

    statement = (
        select(DimMovie)
        .where(DimMovie.sk_movie_id == movie_id)
        .options(
            selectinload(DimMovie.genres),
            selectinload(DimMovie.companies),
            selectinload(DimMovie.people),
            selectinload(DimMovie.performance),
            selectinload(DimMovie.reviews_summary),
        )
    )
    if refresh:
        statement = statement.execution_options(populate_existing=True)
    return await db.scalar(statement)


async def movie_exists(db: AsyncSession, movie_id: str) -> bool:
    return bool(
        await db.scalar(select(select(DimMovie).where(DimMovie.sk_movie_id == movie_id).exists()))
    )


async def list_reviews(
    db: AsyncSession, movie_id: str, page: int, page_size: int
) -> tuple[Sequence[MovieReview], int]:
    condition = MovieReview.sk_movie_id == movie_id
    total = await db.scalar(select(func.count()).select_from(MovieReview).where(condition))
    reviews = await db.scalars(
        select(MovieReview)
        .where(condition)
        .order_by(MovieReview.created_at.desc(), MovieReview.sk_movie_review_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return reviews.all(), total or 0


async def list_genres(db: AsyncSession) -> Sequence[DimGenre]:
    return (await db.scalars(select(DimGenre).order_by(DimGenre.nome_genero))).all()


async def search_people(
    db: AsyncSession, tipo: str | None, q: str | None, limit: int
) -> Sequence[DimPerson]:
    statement = select(DimPerson)
    if tipo:
        statement = statement.where(DimPerson.tipo_pessoa == tipo)
    if q and q.strip():
        statement = statement.where(contains_normalized(DimPerson.nome_pessoa, q.strip()))
    return (await db.scalars(statement.order_by(DimPerson.nome_pessoa).limit(limit))).all()
