"""Modelo ORM do catálogo de filmes do RocketLab 2026.2.

O domínio foi organizado como esquema estrela para suportar consultas
analíticas, mantendo relações de navegação úteis para a futura API.
"""

from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Double,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def generate_surrogate_key() -> str:
    """Gera uma chave substituta textual no formato SHA-256."""

    return sha256(uuid4().bytes).hexdigest()


bridge_movie_genre = Table(
    "bridge_movie_genre",
    Base.metadata,
    Column(
        "sk_movie_id",
        String(64),
        ForeignKey("dim_movies.sk_movie_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "sk_genre_id",
        String(64),
        ForeignKey("dim_genres.sk_genre_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

bridge_movie_company = Table(
    "bridge_movie_company",
    Base.metadata,
    Column(
        "sk_movie_id",
        String(64),
        ForeignKey("dim_movies.sk_movie_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "sk_company_id",
        String(64),
        ForeignKey("dim_companies.sk_company_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

bridge_movie_person = Table(
    "bridge_movie_person",
    Base.metadata,
    Column(
        "sk_movie_id",
        String(64),
        ForeignKey("dim_movies.sk_movie_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "sk_person_id",
        String(64),
        ForeignKey("dim_people.sk_person_id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)


class DimMovie(Base):
    """Metadados descritivos de um filme."""

    __tablename__ = "dim_movies"

    sk_movie_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_surrogate_key
    )
    id_filme: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    titulo: Mapped[str] = mapped_column(String(500), index=True)
    data_lancamento: Mapped[date | None] = mapped_column(Date, default=None)
    ano_lancamento: Mapped[int | None] = mapped_column(Integer, index=True, default=None)
    duracao_minutos: Mapped[int | None] = mapped_column(Integer, default=None)
    status_filme: Mapped[str | None] = mapped_column(String(50), default=None)
    sinopse: Mapped[str | None] = mapped_column(String(4000), default=None)
    url_poster: Mapped[str | None] = mapped_column(String(2048), default=None)
    url_backdrop: Mapped[str | None] = mapped_column(String(2048), default=None)

    genres: Mapped[list["DimGenre"]] = relationship(
        secondary=bridge_movie_genre, back_populates="movies", order_by="DimGenre.nome_genero"
    )
    companies: Mapped[list["DimCompany"]] = relationship(
        secondary=bridge_movie_company,
        back_populates="movies",
        order_by="DimCompany.nome_produtora",
    )
    people: Mapped[list["DimPerson"]] = relationship(
        secondary=bridge_movie_person, back_populates="movies"
    )
    performance: Mapped["FactMoviePerformance | None"] = relationship(
        back_populates="movie", cascade="all, delete-orphan", uselist=False
    )
    reviews_summary: Mapped["DimReview | None"] = relationship(
        back_populates="movie", cascade="all, delete-orphan", uselist=False
    )
    reviews: Mapped[list["MovieReview"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan", order_by="MovieReview.created_at"
    )


class DimGenre(Base):
    """Catálogo deduplicado de gêneros."""

    __tablename__ = "dim_genres"

    sk_genre_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_surrogate_key
    )
    nome_genero: Mapped[str] = mapped_column(String(50), unique=True)

    movies: Mapped[list[DimMovie]] = relationship(
        secondary=bridge_movie_genre, back_populates="genres"
    )


class DimCompany(Base):
    """Catálogo deduplicado de produtoras e estúdios."""

    __tablename__ = "dim_companies"

    sk_company_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_surrogate_key
    )
    nome_produtora: Mapped[str] = mapped_column(String(255), unique=True)

    movies: Mapped[list[DimMovie]] = relationship(
        secondary=bridge_movie_company, back_populates="companies"
    )


PERSON_TYPES: tuple[str, ...] = ("Ator", "Diretor", "Roteirista")
PersonType = Literal["Ator", "Diretor", "Roteirista"]


class DimPerson(Base):
    """Pessoa associada a um filme em um papel específico."""

    __tablename__ = "dim_people"
    __table_args__ = (
        UniqueConstraint(
            "nome_pessoa", "tipo_pessoa", name="uq_dim_people_nome_pessoa_tipo_pessoa"
        ),
        CheckConstraint(
            "tipo_pessoa IN (" + ", ".join(f"'{value}'" for value in PERSON_TYPES) + ")",
            name="tipo_pessoa_valido",
        ),
    )

    sk_person_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_surrogate_key
    )
    nome_pessoa: Mapped[str] = mapped_column(String(255), index=True)
    tipo_pessoa: Mapped[PersonType] = mapped_column(String(20))

    movies: Mapped[list[DimMovie]] = relationship(
        secondary=bridge_movie_person, back_populates="people"
    )


class FactMoviePerformance(Base):
    """Métricas financeiras e de engajamento; uma ocorrência por filme.

    Todo filme tem uma linha aqui (mesmo sem métricas), o que permite ordenar o
    catálogo por popularidade a partir do índice, sem LEFT JOIN.
    """

    __tablename__ = "fact_movies_performance"
    __table_args__ = (
        Index("ix_fact_movies_performance_popularidade", "popularidade", "sk_movie_id"),
    )

    sk_movie_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("dim_movies.sk_movie_id", ondelete="CASCADE"), primary_key=True
    )
    orcamento_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    receita_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    lucro_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    orcamento_brl: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    receita_brl: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    lucro_brl: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    popularidade: Mapped[float | None] = mapped_column(Double, default=None)
    nota_tmdb: Mapped[float | None] = mapped_column(Double, default=None)
    qtd_tmdb: Mapped[int | None] = mapped_column(Integer, default=None)
    nota_imdb: Mapped[float | None] = mapped_column(Double, default=None)
    qtd_imdb: Mapped[int | None] = mapped_column(Integer, default=None)

    movie: Mapped[DimMovie] = relationship(back_populates="performance")


class MovieReview(Base):
    """Avaliação individual de um filme na escala de 0 a 10."""

    __tablename__ = "movie_reviews"
    __table_args__ = (CheckConstraint("nota >= 0 AND nota <= 10", name="nota_range"),)

    sk_movie_review_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_surrogate_key
    )
    sk_movie_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("dim_movies.sk_movie_id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(120))
    nota: Mapped[float] = mapped_column(Double)
    comentario: Mapped[str] = mapped_column(String(4000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    movie: Mapped[DimMovie] = relationship(back_populates="reviews")


class DimReview(Base):
    """Resumo consolidado de avaliações por filme.

    Todo filme tem uma linha aqui (``qtd_avaliacoes_usuarios = 0`` quando ainda
    não foi avaliado), mantida em sincronia com ``movie_reviews``.
    """

    __tablename__ = "dim_reviews"
    __table_args__ = (
        Index(
            "ix_dim_reviews_nota_media",
            "nota_media_usuarios",
            "qtd_avaliacoes_usuarios",
            "sk_movie_id",
        ),
        Index(
            "ix_dim_reviews_qtd_avaliacoes",
            "qtd_avaliacoes_usuarios",
            "nota_media_usuarios",
            "sk_movie_id",
        ),
    )

    sk_review_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_surrogate_key
    )
    sk_movie_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("dim_movies.sk_movie_id", ondelete="CASCADE"), unique=True
    )
    qtd_avaliacoes_usuarios: Mapped[int] = mapped_column(Integer, default=0)
    nota_media_usuarios: Mapped[float | None] = mapped_column(Double, default=None)

    movie: Mapped[DimMovie] = relationship(back_populates="reviews_summary")
