"""Contratos de entrada e saída da API do catálogo de filmes."""

from datetime import UTC, date, datetime
from enum import StrEnum
from math import ceil
from typing import Annotated, Generic, Self, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.text import normalize_text
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
            # O SQLite guarda UTC sem fuso; explicitá-lo evita o front tratar como hora local.
            created_at=review.created_at.replace(tzinfo=UTC),
        )


class ReviewCreated(ReviewOut):
    """Avaliação criada e o resumo do filme já recalculado."""

    avaliacao: RatingSummary


# --------------------------------------------------------------------------- #
# Entradas (escrita)
# --------------------------------------------------------------------------- #

MIN_YEAR = 1888  # Primeiro filme conhecido (Roundhay Garden Scene).
MAX_YEAR = 2100


def collapse_spaces(value: str) -> str:
    return " ".join(value.split())


Title = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
    AfterValidator(collapse_spaces),
]
PersonName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    AfterValidator(collapse_spaces),
]
Synopsis = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
GenreName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
    AfterValidator(collapse_spaces),
]
Url = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=2048, pattern=r"^https?://\S+$"),
]
Year = Annotated[int, Field(ge=MIN_YEAR, le=MAX_YEAR)]
Duration = Annotated[int, Field(ge=1, le=1000, description="Duração em minutos")]
GenreNames = Annotated[
    list[GenreName],
    Field(
        max_length=10,
        description="Nomes; reaproveita gêneros existentes (GET /genres) ou cria novos",
    ),
]
DirectorNames = Annotated[
    list[PersonName],
    Field(max_length=10, description="Nomes; reaproveita diretores existentes"),
]


class MovieStatus(StrEnum):
    """Situações presentes no catálogo original."""

    LANCADO = "Lançado"
    POS_PRODUCAO = "Pós-Produção"
    EM_PRODUCAO = "Em Produção"
    PLANEJADO = "Planejado"


def unique_names(values: list[str]) -> list[str]:
    """Remove nomes repetidos, ignorando acentos e maiúsculas (mantém o primeiro)."""

    seen: dict[str | None, str] = {}
    for value in values:
        seen.setdefault(normalize_text(value), value)
    return list(seen.values())


class MovieWriteBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("generos", "diretores", mode="after", check_fields=False)
    @classmethod
    def _unique_names(cls, value: list[str] | None) -> list[str] | None:
        return unique_names(value) if value is not None else None

    @field_validator("sinopse", "url_poster", "url_backdrop", mode="before", check_fields=False)
    @classmethod
    def _blank_as_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class MovieCreate(MovieWriteBase):
    """Cadastro de filme.

    A obrigatoriedade segue o modelo de dados (como a atividade orienta para a
    escala de notas): só o título é NOT NULL em ``dim_movies``. Os demais campos
    são opcionais, mas validados quando enviados. Informando só a data de
    lançamento, o ano é preenchido a partir dela.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "titulo": "Ainda Estou Aqui",
                    "ano_lancamento": 2024,
                    "generos": ["Drama", "History"],
                    "diretores": ["Walter Salles"],
                    "sinopse": "Uma mulher reconstrói a vida após o desaparecimento do marido.",
                    "duracao_minutos": 137,
                    "status_filme": "Lançado",
                }
            ]
        }
    )

    titulo: Title
    ano_lancamento: Year | None = None
    generos: GenreNames = Field(default_factory=list)
    diretores: DirectorNames = Field(default_factory=list)
    sinopse: Synopsis | None = None
    data_lancamento: date | None = None
    duracao_minutos: Duration | None = None
    status_filme: MovieStatus | None = None
    url_poster: Url | None = None
    url_backdrop: Url | None = None


class MovieUpdate(MovieWriteBase):
    """Atualização parcial: só os campos enviados são alterados.

    Mesmas regras do cadastro: o título não pode ser removido; campos opcionais
    podem ser limpos com ``null`` (ou ``[]`` para gêneros e diretores).
    """

    model_config = ConfigDict(json_schema_extra={"examples": [{"duracao_minutos": 140}]})

    titulo: Title | None = None
    ano_lancamento: Year | None = None
    generos: GenreNames | None = None
    diretores: DirectorNames | None = None
    sinopse: Synopsis | None = None
    data_lancamento: date | None = None
    duracao_minutos: Duration | None = None
    status_filme: MovieStatus | None = None
    url_poster: Url | None = None
    url_backdrop: Url | None = None

    @model_validator(mode="after")
    def _required_fields_not_null(self) -> Self:
        if "titulo" in self.model_fields_set and self.titulo is None:
            raise ValueError("titulo não pode ser nulo")
        for name in ("generos", "diretores"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} não pode ser nulo; use [] para remover todos")
        return self


class ReviewCreate(BaseModel):
    """Nova avaliação: nota de 0 a 10 e resenha em texto."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"nome": "Maria", "nota": 8.5, "comentario": "Atuações excelentes."}]
        },
    )

    nome: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
        AfterValidator(collapse_spaces),
    ]
    nota: float = Field(ge=0, le=10, allow_inf_nan=False, description="Escala de 0 a 10")
    comentario: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]

    @field_validator("nota")
    @classmethod
    def _one_decimal(cls, value: float) -> float:
        # Mesma precisão das notas do catálogo (ex.: 8.5); evita 7.3333333.
        return round(value, 1)
