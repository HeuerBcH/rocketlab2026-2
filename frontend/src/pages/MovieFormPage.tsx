import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { ApiError } from '@/api/client'
import { useCreateMovie, useGenres, useMovie, usePeopleSearch, useUpdateMovie } from '@/api/queries'
import type { MovieDetail } from '@/api/types'
import { StatusMessage } from '@/components/StatusMessage'
import { TagInput } from '@/components/TagInput'
import { FieldError, Spinner } from '@/components/ui'
import { findGenre, genreLabel } from '@/lib/genres'
import {
  changedFields,
  emptyMovieForm,
  formToPayload,
  movieFormSchema,
  movieToForm,
  STATUS_OPTIONS,
  type MovieFormValues,
} from '@/lib/movieForm'

interface MovieFormPageProps {
  mode: 'create' | 'edit'
}

export function MovieFormPage({ mode }: MovieFormPageProps) {
  const { movieId = '' } = useParams()
  if (mode === 'create') return <MovieForm />
  return <EditMovie movieId={movieId} />
}

function EditMovie({ movieId }: { movieId: string }) {
  const movie = useMovie(movieId)
  if (movie.isPending) return <Spinner label="Carregando filme…" />
  if (movie.isError) return <StatusMessage tone="error" title={movie.error.message} />
  return <MovieForm movie={movie.data} />
}

function MovieForm({ movie }: { movie?: MovieDetail }) {
  const navigate = useNavigate()
  const initial = movie ? movieToForm(movie) : emptyMovieForm
  const createMovie = useCreateMovie()
  const updateMovie = useUpdateMovie(movie?.id ?? '')
  const saving = createMovie.isPending || updateMovie.isPending

  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<MovieFormValues>({ resolver: zodResolver(movieFormSchema), defaultValues: initial })

  const [genreQuery, setGenreQuery] = useState('')
  const [directorQuery, setDirectorQuery] = useState('')
  const genres = useGenres()
  const directors = usePeopleSearch(directorQuery, 'Diretor')

  const normalizedGenreQuery = genreQuery.trim().toLocaleLowerCase('pt-BR')
  const genreSuggestions = (genres.data ?? [])
    .map((genre) => ({ value: genre.nome, label: genreLabel(genre.nome) }))
    .filter(
      (option) =>
        option.label.toLocaleLowerCase('pt-BR').includes(normalizedGenreQuery) ||
        option.value.toLocaleLowerCase('pt-BR').includes(normalizedGenreQuery),
    )

  const onSubmit = async (values: MovieFormValues) => {
    try {
      let saved: MovieDetail
      if (movie) {
        const changes = changedFields(initial, values)
        if (Object.keys(changes).length === 0) {
          toast.info('Nenhuma alteração para salvar.')
          return
        }
        saved = await updateMovie.mutateAsync(changes)
        toast.success('Filme atualizado.')
      } else {
        saved = await createMovie.mutateAsync(formToPayload(values))
        toast.success('Filme cadastrado.')
      }
      navigate(`/movies/${saved.id}`)
    } catch (error) {
      if (error instanceof ApiError) {
        // Erros de validação da API aparecem no próprio campo.
        for (const [field, message] of Object.entries(error.fieldErrors)) {
          const name = field.split('.')[0] as keyof MovieFormValues
          if (name in emptyMovieForm) setError(name, { message })
        }
        toast.error(error.message)
      } else {
        toast.error('Erro inesperado ao salvar.')
      }
    }
  }

  const title = movie ? `Editar “${movie.titulo}”` : 'Novo filme'

  return (
    <section className="mx-auto max-w-3xl">
      <h1 className="mb-1 text-4xl font-bold">{title}</h1>
      <p className="meta mb-6">Apenas o título é obrigatório.</p>

      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="card grid gap-5 p-6 sm:grid-cols-6"
      >
        <div className="sm:col-span-6">
          <label htmlFor="titulo" className="label">
            Título <span className="text-accent">*</span>
          </label>
          <input
            id="titulo"
            className="input"
            aria-invalid={Boolean(errors.titulo)}
            {...register('titulo')}
          />
          <FieldError message={errors.titulo?.message} />
        </div>

        <div className="sm:col-span-2">
          <label htmlFor="ano_lancamento" className="label">
            Ano
          </label>
          <input
            id="ano_lancamento"
            inputMode="numeric"
            className="input"
            aria-invalid={Boolean(errors.ano_lancamento)}
            {...register('ano_lancamento')}
          />
          <FieldError message={errors.ano_lancamento?.message} />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="data_lancamento" className="label">
            Data de lançamento
          </label>
          <input
            id="data_lancamento"
            type="date"
            className="input"
            aria-invalid={Boolean(errors.data_lancamento)}
            {...register('data_lancamento')}
          />
          <FieldError message={errors.data_lancamento?.message} />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="duracao_minutos" className="label">
            Duração (min)
          </label>
          <input
            id="duracao_minutos"
            inputMode="numeric"
            className="input"
            aria-invalid={Boolean(errors.duracao_minutos)}
            {...register('duracao_minutos')}
          />
          <FieldError message={errors.duracao_minutos?.message} />
        </div>

        <div className="sm:col-span-3">
          <Controller
            control={control}
            name="generos"
            render={({ field, fieldState }) => (
              <TagInput
                label="Gêneros"
                values={field.value}
                onChange={field.onChange}
                suggestions={genreSuggestions}
                onQueryChange={setGenreQuery}
                resolve={(typed) => findGenre(genres.data ?? [], typed)?.nome}
                renderLabel={genreLabel}
                placeholder="Ex.: Drama, Ação…"
                error={fieldState.error?.message}
              />
            )}
          />
        </div>
        <div className="sm:col-span-3">
          <Controller
            control={control}
            name="diretores"
            render={({ field, fieldState }) => (
              <TagInput
                label="Direção"
                values={field.value}
                onChange={field.onChange}
                suggestions={(directors.data ?? []).map((p) => ({ value: p.nome, label: p.nome }))}
                onQueryChange={setDirectorQuery}
                placeholder="Digite um nome…"
                error={fieldState.error?.message}
              />
            )}
          />
        </div>

        <div className="sm:col-span-6">
          <label htmlFor="sinopse" className="label">
            Sinopse
          </label>
          <textarea
            id="sinopse"
            rows={5}
            className="input resize-y"
            aria-invalid={Boolean(errors.sinopse)}
            {...register('sinopse')}
          />
          <FieldError message={errors.sinopse?.message} />
        </div>

        <div className="sm:col-span-2">
          <label htmlFor="status_filme" className="label">
            Situação
          </label>
          <select id="status_filme" className="input" {...register('status_filme')}>
            <option value="">—</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status}>{status}</option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-4">
          <label htmlFor="url_poster" className="label">
            URL do pôster
          </label>
          <input
            id="url_poster"
            type="url"
            className="input"
            placeholder="https://…"
            aria-invalid={Boolean(errors.url_poster)}
            {...register('url_poster')}
          />
          <FieldError message={errors.url_poster?.message} />
        </div>
        <div className="sm:col-span-6">
          <label htmlFor="url_backdrop" className="label">
            URL da imagem de fundo
          </label>
          <input
            id="url_backdrop"
            type="url"
            className="input"
            placeholder="https://…"
            aria-invalid={Boolean(errors.url_backdrop)}
            {...register('url_backdrop')}
          />
          <FieldError message={errors.url_backdrop?.message} />
        </div>

        <div className="flex justify-end gap-2 sm:col-span-6">
          <Link to={movie ? `/movies/${movie.id}` : '/'} className="btn-ghost">
            Cancelar
          </Link>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Salvando…' : movie ? 'Salvar alterações' : 'Cadastrar filme'}
          </button>
        </div>
      </form>
    </section>
  )
}
