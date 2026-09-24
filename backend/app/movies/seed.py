"""Carga inicial do catálogo de filmes a partir dos CSVs da atividade.

Uso (a partir de ``backend/``, com o banco já migrado pelo Alembic)::

    python -m app.movies.seed --data-dir ../data [--reset]

Decisões:

- A carga é atômica: qualquer linha inválida desfaz tudo e o erro aponta
  ``arquivo:linha``.
- As colunas esperadas vêm do metadata do ORM, então o script acompanha os
  modelos automaticamente.
- ``dim_reviews.csv`` não é importado. O resumo veio inconsistente com
  ``movies_reviews.csv``, então ``dim_reviews`` é recalculada a partir de
  ``movie_reviews``, que é a fonte de verdade das avaliações.
"""

import argparse
import csv
import sqlite3
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import Column, Date, Double, Integer, Numeric, Table
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.db.base import Base
from app.movies import models  # noqa: F401  Registra as tabelas no metadata.

BATCH_SIZE = 5_000


@dataclass(frozen=True)
class Source:
    filename: str
    table: str


# Ordem respeita as chaves estrangeiras: dimensões, filmes, fatos e pontes.
SOURCES: tuple[Source, ...] = (
    Source("dim_genres.csv", "dim_genres"),
    Source("dim_companies.csv", "dim_companies"),
    Source("dim_people.csv", "dim_people"),
    Source("dim_movies.csv", "dim_movies"),
    Source("fact_movies_performance.csv", "fact_movies_performance"),
    Source("bridge_movie_genre.csv", "bridge_movie_genre"),
    Source("bridge_movie_company.csv", "bridge_movie_company"),
    Source("bridge_movie_person.csv", "bridge_movie_person"),
    Source("movies_reviews.csv", "movie_reviews"),
)

# Tabelas limpas no --reset, das dependentes para as independentes.
RESET_ORDER: tuple[str, ...] = (
    "dim_reviews",
    *(source.table for source in reversed(SOURCES)),
)


class SeedError(Exception):
    """Erro de carga com mensagem pronta para o usuário."""


# --------------------------------------------------------------------------- #
# Conversão de valores
# --------------------------------------------------------------------------- #


def to_int(value: str) -> int:
    # Alguns inteiros vêm serializados como float ("2375.0").
    number = Decimal(value)
    if number != number.to_integral_value():
        raise ValueError(f"esperado inteiro, recebido {value!r}")
    return int(number)


def to_float(value: str) -> float:
    return float(Decimal(value))


def to_date(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def clean_text(value: str) -> str:
    return value.strip()


def clean_synopsis(value: str) -> str:
    # Parte das sinopses foi escapada duas vezes como CSV: vem envolvida em aspas
    # (às vezes sem a aspa final) e com as aspas internas duplicadas.
    value = value.strip()
    # Sem aspas duplicadas, a aspa inicial é uma citação legítima do texto.
    if value.startswith('"') and '""' in value:
        value = value[1:]
        # Aspas internas escapadas vêm em pares; sobrando uma, é a de fechamento.
        trailing_quotes = len(value) - len(value.rstrip('"'))
        if trailing_quotes % 2 == 1:
            value = value[:-1]
    # Alguns textos já tinham aspas duplicadas na origem; prosa nunca tem "" legítimo.
    while '""' in value:
        value = value.replace('""', '"')
    return value.strip()


def converter_for(column: Column) -> Callable[[str], object]:
    if column.name == "sinopse":
        return clean_synopsis
    if isinstance(column.type, Integer):
        return to_int
    if isinstance(column.type, Double | Numeric):
        return to_float
    if isinstance(column.type, Date):
        return to_date
    return clean_text


# --------------------------------------------------------------------------- #
# Leitura dos CSVs
# --------------------------------------------------------------------------- #


def find_csv(data_dir: Path, filename: str) -> Path:
    matches = sorted(data_dir.rglob(filename))
    if not matches:
        raise SeedError(f"Arquivo {filename} não encontrado em {data_dir}")
    if len(matches) > 1:
        found = ", ".join(str(match) for match in matches)
        raise SeedError(f"Arquivo {filename} encontrado mais de uma vez: {found}")
    return matches[0]


def csv_columns(table: Table) -> list[Column]:
    # Colunas com default no servidor (created_at) são preenchidas pelo banco.
    return [column for column in table.columns if column.server_default is None]


def read_rows(path: Path, table: Table) -> Iterator[tuple[int, tuple[object, ...]]]:
    """Lê o CSV validando o cabeçalho e convertendo cada valor pelo tipo da coluna."""

    columns = csv_columns(table)
    expected = {column.name for column in columns}
    converters = [(column, converter_for(column)) for column in columns]

    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        header = set(reader.fieldnames or ())
        if header != expected:
            missing = ", ".join(sorted(expected - header)) or "-"
            extra = ", ".join(sorted(header - expected)) or "-"
            raise SeedError(
                f"{path.name}: cabeçalho inválido (faltando: {missing}; inesperadas: {extra})"
            )

        for row in reader:
            line = reader.line_num
            if None in row or None in row.values():
                raise SeedError(f"{path.name}:{line}: número de colunas inválido")
            values: list[object] = []
            for column, convert in converters:
                raw = row[column.name]
                try:
                    value = convert(raw) if raw.strip() else None
                except (ValueError, InvalidOperation) as exc:
                    raise SeedError(f"{path.name}:{line}: coluna {column.name}: {exc}") from exc
                if value in (None, "") and not column.nullable:
                    raise SeedError(f"{path.name}:{line}: coluna {column.name} é obrigatória")
                values.append(value if value != "" else None)
            yield line, tuple(values)


# --------------------------------------------------------------------------- #
# Escrita no banco
# --------------------------------------------------------------------------- #


def insert_batch(
    db: sqlite3.Connection, sql: str, batch: list[tuple[int, tuple[object, ...]]], filename: str
) -> None:
    db.execute("SAVEPOINT seed_batch")
    try:
        db.executemany(sql, [values for _, values in batch])
    except sqlite3.Error:
        # Refaz linha a linha só para descobrir qual linha do CSV quebrou.
        db.execute("ROLLBACK TO seed_batch")
        for line, values in batch:
            try:
                db.execute(sql, values)
            except sqlite3.Error as exc:
                raise SeedError(f"{filename}:{line}: {exc}") from exc
        raise
    finally:
        db.execute("RELEASE seed_batch")


def load_table(db: sqlite3.Connection, path: Path, table: Table) -> int:
    names = [column.name for column in csv_columns(table)]
    sql = f"INSERT INTO {table.name} ({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})"
    count = 0
    batch: list[tuple[int, tuple[object, ...]]] = []
    for item in read_rows(path, table):
        batch.append(item)
        if len(batch) == BATCH_SIZE:
            insert_batch(db, sql, batch, path.name)
            count += len(batch)
            batch.clear()
    if batch:
        insert_batch(db, sql, batch, path.name)
        count += len(batch)
    return count


def rebuild_review_summary(db: sqlite3.Connection) -> int:
    """Recalcula ``dim_reviews`` (quantidade e média) a partir de ``movie_reviews``."""

    db.execute("DELETE FROM dim_reviews")
    cursor = db.execute(
        "INSERT INTO dim_reviews "
        "(sk_review_id, sk_movie_id, qtd_avaliacoes_usuarios, nota_media_usuarios) "
        "SELECT lower(hex(randomblob(32))), sk_movie_id, COUNT(*), AVG(nota) "
        "FROM movie_reviews GROUP BY sk_movie_id"
    )
    return cursor.rowcount


def sqlite_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise SeedError("A carga suporta apenas DATABASE_URL SQLite em arquivo")
    return Path(url.database)


def ensure_migrated(db: sqlite3.Connection) -> None:
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = {source.table for source in SOURCES} | {"dim_reviews"}
    if not missing <= tables:
        raise SeedError("Banco sem as tabelas do catálogo. Rode antes: alembic upgrade head")


def seed(
    data_dir: Path,
    db_path: Path,
    *,
    reset: bool = False,
    log: Callable[[str], None] = lambda _: None,
) -> dict[str, int]:
    """Popula o banco com os CSVs de ``data_dir`` numa única transação."""

    data_dir = data_dir.resolve()
    if not data_dir.is_dir():
        raise SeedError(f"Diretório de dados não encontrado: {data_dir}")
    paths = {source.table: find_csv(data_dir, source.filename) for source in SOURCES}
    if not db_path.exists():
        raise SeedError(f"Banco {db_path} não existe. Rode antes: alembic upgrade head")

    db = sqlite3.connect(db_path, isolation_level=None)
    try:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA synchronous = OFF")
        db.execute("PRAGMA temp_store = MEMORY")
        ensure_migrated(db)

        populated = db.execute("SELECT EXISTS(SELECT 1 FROM dim_movies)").fetchone()[0]
        if populated and not reset:
            raise SeedError("O banco já contém filmes. Use --reset para recarregar do zero.")

        counts: dict[str, int] = {}
        db.execute("BEGIN")
        try:
            if populated:
                for table in RESET_ORDER:
                    db.execute(f"DELETE FROM {table}")
                log("Dados anteriores removidos.")
            for source in SOURCES:
                started = time.perf_counter()
                table = Base.metadata.tables[source.table]
                counts[source.table] = load_table(db, paths[source.table], table)
                elapsed = time.perf_counter() - started
                log(f"{source.table:<25} {counts[source.table]:>9,} linhas  ({elapsed:.1f}s)")
            counts["dim_reviews"] = rebuild_review_summary(db)
            log(f"{'dim_reviews (recalculada)':<25} {counts['dim_reviews']:>9,} linhas")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        db.execute("COMMIT")
        return counts
    except sqlite3.Error as exc:
        raise SeedError(f"Erro no banco: {exc}") from exc
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Carga inicial do catálogo de filmes a partir dos CSVs."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("../data"),
        help="Diretório com os CSVs (busca recursiva). Padrão: ../data",
    )
    parser.add_argument(
        "--reset", action="store_true", help="Apaga os dados atuais antes de carregar"
    )
    args = parser.parse_args(argv)

    started = time.perf_counter()
    try:
        db_path = sqlite_path(get_settings().database_url)
        print(f"Carregando {args.data_dir.resolve()} -> {db_path.resolve()}")
        seed(args.data_dir, db_path, reset=args.reset, log=print)
    except SeedError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    print(f"Carga concluída em {time.perf_counter() - started:.1f}s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
