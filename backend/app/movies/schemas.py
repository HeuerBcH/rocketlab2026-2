"""Contratos de entrada e saída da API do catálogo de filmes."""

from datetime import date, datetime
from enum import StrEnum
from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.movies.models import DimMovie, DimReview, FactMoviePerformance, MovieReview

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Envelope padrão de respostas paginadas."""

    items: list[T]
    total: int = Field(description="Total de registros que atendem aos filtros")
    page: int
    page_size: int
    pages: int = Field(description="Total de páginas")

    @classmethod
    def build(cls, items: list[T], total: int, page: int, page_size: int) -> "Page[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )


class MovieSort(StrEnum):
    """Ordenações disponíveis no catálogo."""

    POPULARIDADE = "popularidade"
    TITULO = "titulo"
    ANO_DESC = "-ano"
    ANO_ASC = "ano"
    MEDIA = "-media"
    AVALIACOES = "-avaliacoes"


class GenreOut(BaseModel):
    id: str
    nome: str


class PersonOut(BaseModel):
    id: str
    nome: str
    tipo: str


class RatingSummary(BaseModel):
    """Média geral (escala 0–10) e total de avaliações de um filme."""

    media: float | None = Field(description="Média das notas, arredondada em 2 casas")
    qtd_avaliacoes: int

    @classmethod
    def from_model(cls, summary: DimReview | None) -> "RatingSummary":
        if summary is None or not summary.qtd_avaliacoes_usuarios:
            return cls(media=None, qtd_avaliacoes=0)
        media = summary.nota_media_usuarios
        return cls(
            media=round(media, 2) if media is not None else None,
            qtd_avaliacoes=summary.qtd_avaliacoes_usuarios,
        )


class MovieListItem(BaseModel):
    """Resumo de um filme para cards do catálogo."""

    id: str
    titulo: str
    ano_lancamento: int | None
    url_poster: str | None
    generos: list[str]
    avaliacao: RatingSummary

    @classmethod
    def from_model(cls, movie: DimMovie) -> "MovieListItem":
        return cls(
            id=movie.sk_movie_id,
            titulo=movie.titulo,
            ano_lancamento=movie.ano_lancamento,
            url_poster=movie.url_poster,
            generos=[genre.nome_genero for genre in movie.genres],
            avaliacao=RatingSummary.from_model(movie.reviews_summary),
        )


class PerformanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    orcamento_usd: float | None
    receita_usd: float | None
    lucro_usd: float | None
    orcamento_brl: float | None
    receita_brl: float | None
    lucro_brl: float | None
    popularidade: float | None
    nota_tmdb: float | None
    qtd_tmdb: int | None
    nota_imdb: float | None
    qtd_imdb: int | None


class MovieDetail(BaseModel):
    """Informações completas de um filme."""

    id: str
    id_filme: str
    titulo: str
    data_lancamento: date | None
    ano_lancamento: int | None
    duracao_minutos: int | None
    status_filme: str | None
    sinopse: str | None
    url_poster: str | None
    url_backdrop: str | None
    generos: list[GenreOut]
    diretores: list[PersonOut]
    roteiristas: list[PersonOut]
    elenco: list[PersonOut]
    produtoras: list[str]
    desempenho: PerformanceOut | None
    avaliacao: RatingSummary

    @classmethod
    def from_model(cls, movie: DimMovie) -> "MovieDetail":
        def people(tipo: str) -> list[PersonOut]:
            return [
                PersonOut(id=person.sk_person_id, nome=person.nome_pessoa, tipo=tipo)
                for person in sorted(movie.people, key=lambda person: person.nome_pessoa)
                if person.tipo_pessoa == tipo
            ]

        performance: FactMoviePerformance | None = movie.performance
        return cls(
            id=movie.sk_movie_id,
            id_filme=movie.id_filme,
            titulo=movie.titulo,
            data_lancamento=movie.data_lancamento,
            ano_lancamento=movie.ano_lancamento,
            duracao_minutos=movie.duracao_minutos,
            status_filme=movie.status_filme,
            sinopse=movie.sinopse,
            url_poster=movie.url_poster,
            url_backdrop=movie.url_backdrop,
            generos=[GenreOut(id=g.sk_genre_id, nome=g.nome_genero) for g in movie.genres],
            diretores=people("Diretor"),
            roteiristas=people("Roteirista"),
            elenco=people("Ator"),
            produtoras=[company.nome_produtora for company in movie.companies],
            desempenho=PerformanceOut.model_validate(performance) if performance else None,
            avaliacao=RatingSummary.from_model(movie.reviews_summary),
        )


class ReviewOut(BaseModel):
    id: str
    nome: str
    nota: float = Field(ge=0, le=10)
    comentario: str
    created_at: datetime

    @classmethod
    def from_model(cls, review: MovieReview) -> "ReviewOut":
        return cls(
            id=review.sk_movie_review_id,
            nome=review.nome,
            nota=review.nota,
            comentario=review.comentario,
            created_at=review.created_at,
        )
