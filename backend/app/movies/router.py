from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.movies import repository
from app.movies.models import PersonType
from app.movies.repository import MovieFilters
from app.movies.schemas import (
    GenreOut,
    MovieDetail,
    MovieListItem,
    MovieSort,
    Page,
    PersonOut,
    ReviewOut,
)

movies_router = APIRouter()
genres_router = APIRouter()
people_router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
PageNumber = Annotated[int, Query(ge=1, description="Página, começando em 1")]
PageSize = Annotated[int, Query(ge=1, le=100, description="Itens por página (máx. 100)")]
Year = Annotated[int | None, Query(ge=1800, le=2100)]

MOVIE_NOT_FOUND = {404: {"description": "Filme não encontrado"}}


def movie_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filme não encontrado")


@movies_router.get("", response_model=Page[MovieListItem], summary="Catálogo paginado")
async def list_movies(
    db: DbSession,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: Annotated[
        str | None,
        Query(max_length=200, description="Busca por título ou diretor (ignora acentos)"),
    ] = None,
    genre: Annotated[str | None, Query(description="ID do gênero (GET /genres)")] = None,
    year_from: Year = None,
    year_to: Year = None,
    sort: MovieSort = MovieSort.POPULARIDADE,
) -> Page[MovieListItem]:
    if year_from is not None and year_to is not None and year_from > year_to:
        raise HTTPException(
            status_code=422,  # constante renomeada entre versões do Starlette
            detail="year_from deve ser menor ou igual a year_to",
        )
    filters = MovieFilters(q=q, genre_id=genre, year_from=year_from, year_to=year_to)
    movies, total = await repository.list_movies(db, filters, sort, page, page_size)
    return Page.build([MovieListItem.from_model(m) for m in movies], total, page, page_size)


@movies_router.get(
    "/{movie_id}",
    response_model=MovieDetail,
    responses=MOVIE_NOT_FOUND,
    summary="Detalhes completos de um filme",
)
async def get_movie(movie_id: str, db: DbSession) -> MovieDetail:
    movie = await repository.get_movie(db, movie_id)
    if movie is None:
        raise movie_not_found()
    return MovieDetail.from_model(movie)


@movies_router.get(
    "/{movie_id}/reviews",
    response_model=Page[ReviewOut],
    responses=MOVIE_NOT_FOUND,
    summary="Histórico de avaliações, mais recentes primeiro",
)
async def list_movie_reviews(
    movie_id: str,
    db: DbSession,
    page: PageNumber = 1,
    page_size: PageSize = 10,
) -> Page[ReviewOut]:
    if not await repository.movie_exists(db, movie_id):
        raise movie_not_found()
    reviews, total = await repository.list_reviews(db, movie_id, page, page_size)
    return Page.build([ReviewOut.from_model(r) for r in reviews], total, page, page_size)


@genres_router.get("", response_model=list[GenreOut], summary="Gêneros disponíveis")
async def list_genres(db: DbSession) -> list[GenreOut]:
    return [
        GenreOut(id=g.sk_genre_id, nome=g.nome_genero) for g in await repository.list_genres(db)
    ]


@people_router.get("", response_model=list[PersonOut], summary="Busca de pessoas (autocomplete)")
async def search_people(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=200)] = None,
    tipo: PersonType | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[PersonOut]:
    people = await repository.search_people(db, tipo, q, limit)
    return [PersonOut(id=p.sk_person_id, nome=p.nome_pessoa, tipo=p.tipo_pessoa) for p in people]
