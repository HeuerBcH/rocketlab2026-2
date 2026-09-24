import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { useGenres, useMovies } from '@/api/queries'
import type { MovieListItem, MovieListParams, MovieSort } from '@/api/types'
import { AdminOnly } from '@/auth/RequireAuth'
import { StatusMessage } from '@/components/StatusMessage'
import { Pagination, Poster, RatingBadge, Spinner } from '@/components/ui'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { genreLabel } from '@/lib/genres'

const PAGE_SIZE = 24

const SORT_OPTIONS: { value: MovieSort; label: string }[] = [
  { value: 'popularidade', label: 'Mais populares' },
  { value: '-media', label: 'Maior média' },
  { value: '-avaliacoes', label: 'Mais avaliados' },
  { value: '-ano', label: 'Mais recentes' },
  { value: 'ano', label: 'Mais antigos' },
  { value: 'titulo', label: 'Título (A–Z)' },
]

function toInt(value: string | null): number | undefined {
  const number = value ? Number.parseInt(value, 10) : NaN
  return Number.isFinite(number) ? number : undefined
}

export function CatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const params: MovieListParams = {
    page: toInt(searchParams.get('page')) ?? 1,
    page_size: PAGE_SIZE,
    q: searchParams.get('q') || undefined,
    genre: searchParams.get('genre') || undefined,
    year_from: toInt(searchParams.get('year_from')),
    year_to: toInt(searchParams.get('year_to')),
    sort: (searchParams.get('sort') as MovieSort | null) ?? 'popularidade',
  }

  /** Atualiza filtros na URL; qualquer mudança de filtro volta para a página 1. */
  const update = (changes: Record<string, string | undefined>) => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      for (const [key, value] of Object.entries(changes)) {
        if (value) next.set(key, value)
        else next.delete(key)
      }
      if (!('page' in changes)) next.delete('page')
      return next
    })
  }

  // Busca digitada: estado local imediato, URL/API só após 300 ms sem digitar.
  const [search, setSearch] = useState(params.q ?? '')
  const debouncedSearch = useDebouncedValue(search.trim())
  const urlQuery = searchParams.get('q') ?? ''
  useEffect(() => {
    if (debouncedSearch !== urlQuery) update({ q: debouncedSearch })
  }, [debouncedSearch]) // eslint-disable-line react-hooks/exhaustive-deps
  // Voltar/avançar no navegador altera a URL: o campo acompanha (ajuste durante o render).
  const [syncedQuery, setSyncedQuery] = useState(urlQuery)
  if (urlQuery !== syncedQuery) {
    setSyncedQuery(urlQuery)
    if (search.trim() !== urlQuery) setSearch(urlQuery)
  }

  const genres = useGenres()
  const movies = useMovies(params)
  const hasFilters = Boolean(params.q || params.genre || params.year_from || params.year_to)

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-2">
        <h1 className="text-4xl font-bold">Catálogo</h1>
        {movies.data && (
          <p className="meta" aria-live="polite">
            {movies.data.total.toLocaleString('pt-BR')} filme{movies.data.total === 1 ? '' : 's'}
          </p>
        )}
      </div>

      <form
        role="search"
        onSubmit={(event) => event.preventDefault()}
        className="card mb-8 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_0.6fr_0.6fr_1fr]"
      >
        <div className="sm:col-span-2 lg:col-span-1">
          <label htmlFor="q" className="label">
            Buscar
          </label>
          <input
            id="q"
            type="search"
            className="input"
            placeholder="Título ou diretor…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="genre" className="label">
            Gênero
          </label>
          <select
            id="genre"
            className="input"
            value={params.genre ?? ''}
            onChange={(event) => update({ genre: event.target.value })}
          >
            <option value="">Todos</option>
            {genres.data
              ?.map((genre) => ({ ...genre, label: genreLabel(genre.nome) }))
              .sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'))
              .map((genre) => (
                <option key={genre.id} value={genre.id}>
                  {genre.label}
                </option>
              ))}
          </select>
        </div>
        <div>
          <label htmlFor="year_from" className="label">
            De (ano)
          </label>
          <input
            id="year_from"
            type="number"
            className="input"
            placeholder="2016"
            key={params.year_from ?? ''}
            defaultValue={params.year_from ?? undefined}
            onBlur={(event) => update({ year_from: event.target.value })}
            onKeyDown={(event) => event.key === 'Enter' && event.currentTarget.blur()}
          />
        </div>
        <div>
          <label htmlFor="year_to" className="label">
            Até (ano)
          </label>
          <input
            id="year_to"
            type="number"
            className="input"
            placeholder="2029"
            key={params.year_to ?? ''}
            defaultValue={params.year_to ?? undefined}
            onBlur={(event) => update({ year_to: event.target.value })}
            onKeyDown={(event) => event.key === 'Enter' && event.currentTarget.blur()}
          />
        </div>
        <div>
          <label htmlFor="sort" className="label">
            Ordenar por
          </label>
          <select
            id="sort"
            className="input"
            value={params.sort}
            onChange={(event) => update({ sort: event.target.value })}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </form>

      {movies.isPending ? (
        <Spinner label="Carregando catálogo…" />
      ) : movies.isError ? (
        <StatusMessage
          tone="error"
          title="Não foi possível carregar o catálogo"
          description={movies.error.message}
          action={
            <button className="btn-ghost" onClick={() => void movies.refetch()}>
              Tentar novamente
            </button>
          }
        />
      ) : movies.data.items.length === 0 ? (
        <StatusMessage
          title="Nenhum filme encontrado"
          description={
            hasFilters ? 'Tente outros termos ou remova os filtros.' : 'O catálogo está vazio.'
          }
          action={
            hasFilters ? (
              <button
                className="btn-ghost"
                onClick={() => {
                  setSearch('')
                  setSearchParams({})
                }}
              >
                Limpar filtros
              </button>
            ) : (
              <AdminOnly>
                <Link to="/movies/new" className="btn-primary">
                  Cadastrar filme
                </Link>
              </AdminOnly>
            )
          }
        />
      ) : (
        <>
          <ul
            className={`grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 ${
              movies.isPlaceholderData ? 'opacity-60' : ''
            }`}
          >
            {movies.data.items.map((movie) => (
              <li key={movie.id}>
                <MovieCard movie={movie} />
              </li>
            ))}
          </ul>
          <Pagination
            page={movies.data.page}
            pages={movies.data.pages}
            onChange={(page) => {
              update({ page: String(page) })
              window.scrollTo({ top: 0 })
            }}
          />
        </>
      )}
    </section>
  )
}

function MovieCard({ movie }: { movie: MovieListItem }) {
  return (
    <Link to={`/movies/${movie.id}`} className="group block">
      <Poster
        src={movie.url_poster}
        title={movie.titulo}
        className="transition group-hover:-translate-y-1 group-hover:ring-2 group-hover:ring-accent"
      />
      <h2 className="mt-2 line-clamp-2 text-base leading-tight font-semibold group-hover:text-accent">
        {movie.titulo}
      </h2>
      <p className="meta mt-1 truncate">
        {[movie.ano_lancamento, movie.generos.slice(0, 2).map(genreLabel).join(', ')]
          .filter(Boolean)
          .join(' · ')}
      </p>
      <div className="mt-1">
        <RatingBadge rating={movie.avaliacao} />
      </div>
    </Link>
  )
}
