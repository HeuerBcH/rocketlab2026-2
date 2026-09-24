# Dados de carga

Arquivos CSV fornecidos pela atividade (~230 MB), versionados junto com o
projeto para que a aplicação rode logo após o clone. Estão organizados nas
pastas originais `bases_atv_dev1/` e `bases_atv_dev_2/`; a carga procura cada
arquivo recursivamente, então a organização em subpastas é livre.

Arquivos esperados:

| Arquivo | Tabela |
|---|---|
| `dim_genres.csv` | `dim_genres` |
| `dim_companies.csv` | `dim_companies` |
| `dim_people.csv` | `dim_people` |
| `dim_movies.csv` | `dim_movies` |
| `fact_movies_performance.csv` | `fact_movies_performance` |
| `bridge_movie_genre.csv` | `bridge_movie_genre` |
| `bridge_movie_company.csv` | `bridge_movie_company` |
| `bridge_movie_person.csv` | `bridge_movie_person` |
| `movies_reviews.csv` | `movie_reviews` |
| `dim_reviews.csv` | não é importado: `dim_reviews` é recalculada a partir de `movie_reviews` |

Depois, a partir de `backend/`:

```bash
python -m app.movies.seed --data-dir ../data
```
