"""Adiciona índices para ordenar o catálogo por popularidade e avaliações.

Revision ID: 0002_catalog_sort_indexes
Revises: 0001_initial_movie_schema
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_catalog_sort_indexes"
down_revision: str | Sequence[str] | None = "0001_initial_movie_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A chave do filme entra no fim de cada índice como critério de desempate:
    # a ordenação fica estável (paginação sem repetições) e resolvida só pelo índice.
    op.create_index(
        "ix_fact_movies_performance_popularidade",
        "fact_movies_performance",
        ["popularidade", "sk_movie_id"],
    )
    op.create_index(
        "ix_dim_reviews_nota_media",
        "dim_reviews",
        ["nota_media_usuarios", "qtd_avaliacoes_usuarios", "sk_movie_id"],
    )
    op.create_index(
        "ix_dim_reviews_qtd_avaliacoes",
        "dim_reviews",
        ["qtd_avaliacoes_usuarios", "nota_media_usuarios", "sk_movie_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_dim_reviews_qtd_avaliacoes", table_name="dim_reviews")
    op.drop_index("ix_dim_reviews_nota_media", table_name="dim_reviews")
    op.drop_index("ix_fact_movies_performance_popularidade", table_name="fact_movies_performance")
