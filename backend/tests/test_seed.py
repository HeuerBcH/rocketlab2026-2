import csv
import sqlite3
from pathlib import Path

import pytest

from app.movies.seed import SeedError, clean_synopsis, main, seed

MOVIE = "m1"
OTHER_MOVIE = "m2"


def base_rows() -> dict[str, list[list[str]]]:
    """Conjunto mínimo e consistente com o formato dos CSVs reais."""

    return {
        "dim_genres.csv": [["nome_genero", "sk_genre_id"], ["Drama", "g1"]],
        "dim_companies.csv": [["nome_produtora", "sk_company_id"], ["Estúdio, Ltda", "c1"]],
        "dim_people.csv": [
            ["nome_pessoa", "tipo_pessoa", "sk_person_id"],
            ["Ana Diretora", "Diretor", "p1"],
        ],
        "dim_movies.csv": [
            [
                "sk_movie_id",
                "id_filme",
                "titulo",
                "data_lancamento",
                "ano_lancamento",
                "duracao_minutos",
                "status_filme",
                "sinopse",
                "url_poster",
                "url_backdrop",
            ],
            [
                MOVIE,
                "10",
                '"Weird" Title',
                "2017-02-01",
                "2017",
                "102",
                "Lançado",
                '"Uma sinopse com ""filme dentro do filme""."',
                "http://poster",
                "",
            ],
            [OTHER_MOVIE, "11", "Sem Review", "", "", "", "", "", "", ""],
        ],
        "fact_movies_performance.csv": [
            [
                "sk_movie_id",
                "orcamento_usd",
                "receita_usd",
                "lucro_usd",
                "orcamento_brl",
                "receita_brl",
                "lucro_brl",
                "popularidade",
                "nota_tmdb",
                "qtd_tmdb",
                "nota_imdb",
                "qtd_imdb",
            ],
            [MOVIE, "25000000.0", "", "0.0", "", "", "0.0", "24.5", "4.9", "2375.0", "", ""],
        ],
        "bridge_movie_genre.csv": [["sk_movie_id", "sk_genre_id"], [MOVIE, "g1"]],
        "bridge_movie_company.csv": [["sk_movie_id", "sk_company_id"], [MOVIE, "c1"]],
        "bridge_movie_person.csv": [["sk_movie_id", "sk_person_id"], [MOVIE, "p1"]],
        "movies_reviews.csv": [
            ["sk_movie_review_id", "sk_movie_id", "nome", "nota", "comentario"],
            ["r1", MOVIE, "Ana", "9.8", "Ótimo, recomendo"],
            ["r2", MOVIE, "Bia", "0.2", "Ruim"],
        ],
        # Resumo propositalmente errado: a carga deve ignorá-lo e recalcular.
        "dim_reviews.csv": [
            ["sk_review_id", "sk_movie_id", "qtd_avaliacoes_usuarios", "nota_media_usuarios"],
            ["s1", MOVIE, "7", "1.0"],
        ],
    }


def write_csvs(data_dir: Path, rows: dict[str, list[list[str]]] | None = None) -> Path:
    rows = rows or base_rows()
    # Espelha a organização original em duas pastas para validar a busca recursiva.
    for index, (filename, content) in enumerate(rows.items()):
        folder = data_dir / ("bases_1" if index % 2 else "bases_2")
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / filename).open("w", encoding="utf-8", newline="") as file:
            csv.writer(file).writerows(content)
    return data_dir


def query(db_path: Path, sql: str) -> list[tuple]:
    with sqlite3.connect(db_path) as db:
        return db.execute(sql).fetchall()


def test_seed_loads_and_cleans_data(tmp_path: Path, db_path: Path) -> None:
    counts = seed(write_csvs(tmp_path / "data"), db_path)

    assert counts["dim_movies"] == 2
    assert counts["movie_reviews"] == 2
    assert query(
        db_path,
        f"SELECT titulo, sinopse, url_backdrop, ano_lancamento "
        f"FROM dim_movies WHERE sk_movie_id = '{MOVIE}'",
    ) == [('"Weird" Title', 'Uma sinopse com "filme dentro do filme".', None, 2017)]
    assert query(db_path, "SELECT qtd_tmdb, receita_usd FROM fact_movies_performance") == [
        (2375, None)
    ]
    assert query(db_path, "SELECT nome_produtora FROM dim_companies") == [("Estúdio, Ltda",)]


def test_seed_rebuilds_review_summary_from_reviews(tmp_path: Path, db_path: Path) -> None:
    seed(write_csvs(tmp_path / "data"), db_path)

    assert query(
        db_path, "SELECT sk_movie_id, qtd_avaliacoes_usuarios, nota_media_usuarios FROM dim_reviews"
    ) == [(MOVIE, 2, 5.0)]


def test_seed_refuses_populated_database_unless_reset(tmp_path: Path, db_path: Path) -> None:
    data_dir = write_csvs(tmp_path / "data")
    seed(data_dir, db_path)

    with pytest.raises(SeedError, match="--reset"):
        seed(data_dir, db_path)

    counts = seed(data_dir, db_path, reset=True)
    assert counts["dim_movies"] == 2
    assert query(db_path, "SELECT COUNT(*) FROM movie_reviews") == [(2,)]


def test_seed_rolls_back_everything_on_invalid_foreign_key(tmp_path: Path, db_path: Path) -> None:
    rows = base_rows()
    rows["bridge_movie_genre.csv"].append([MOVIE, "genero-inexistente"])

    with pytest.raises(SeedError, match=r"bridge_movie_genre\.csv:3"):
        seed(write_csvs(tmp_path / "data", rows), db_path)

    assert query(db_path, "SELECT COUNT(*) FROM dim_movies") == [(0,)]
    assert query(db_path, "SELECT COUNT(*) FROM dim_genres") == [(0,)]


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (["r3", MOVIE, "Caio", "11", "Nota fora da escala"], r"movies_reviews\.csv:4"),
        (["r3", MOVIE, "Caio", "abc", "Texto"], r"movies_reviews\.csv:4: coluna nota"),
        (["r3", MOVIE, "", "5", "Sem nome"], r"movies_reviews\.csv:4: coluna nome"),
        (["r3", MOVIE, "Caio"], r"movies_reviews\.csv:4: número de colunas"),
    ],
)
def test_seed_reports_invalid_review_line(
    tmp_path: Path, db_path: Path, row: list[str], message: str
) -> None:
    rows = base_rows()
    rows["movies_reviews.csv"].append(row)

    with pytest.raises(SeedError, match=message):
        seed(write_csvs(tmp_path / "data", rows), db_path)

    assert query(db_path, "SELECT COUNT(*) FROM movie_reviews") == [(0,)]


def test_seed_rejects_unexpected_header(tmp_path: Path, db_path: Path) -> None:
    rows = base_rows()
    rows["dim_genres.csv"][0] = ["genero", "sk_genre_id"]

    with pytest.raises(SeedError, match="cabeçalho inválido"):
        seed(write_csvs(tmp_path / "data", rows), db_path)


def test_seed_requires_all_files(tmp_path: Path, db_path: Path) -> None:
    rows = base_rows()
    del rows["dim_people.csv"]

    with pytest.raises(SeedError, match="dim_people.csv não encontrado"):
        seed(write_csvs(tmp_path / "data", rows), db_path)


def test_cli_returns_error_code_and_message(
    tmp_path: Path, db_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    del db_path  # Garante DATABASE_URL apontando para o banco temporário.

    assert main(["--data-dir", str(tmp_path / "nao-existe")]) == 1
    assert "Diretório de dados não encontrado" in capsys.readouterr().err

    assert main(["--data-dir", str(write_csvs(tmp_path / "data"))]) == 0
    assert "Carga concluída" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Texto normal.", "Texto normal."),
        ('"Julia vê um ""filme"" estranho."', 'Julia vê um "filme" estranho.'),
        ('"Sem aspa final e ""citação"" no meio', 'Sem aspa final e "citação" no meio'),
        ('"Termina citando ""Kyiv Frescoes"""', 'Termina citando "Kyiv Frescoes"'),
        ('"Termina citando ""Kyiv Frescoes""', 'Termina citando "Kyiv Frescoes"'),
        ('Sequência de ""Grizzly"" (1976)', 'Sequência de "Grizzly" (1976)'),
        ('"Favoritismo de """"La Roja"""" na final."', 'Favoritismo de "La Roja" na final.'),
        ('"Citação" legítima no início.', '"Citação" legítima no início.'),
    ],
)
def test_clean_synopsis_undoes_double_csv_escaping(raw: str, expected: str) -> None:
    assert clean_synopsis(raw) == expected
