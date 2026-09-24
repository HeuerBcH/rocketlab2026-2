import { zodResolver } from '@hookform/resolvers/zod'
import { useState, type ReactNode } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'

import { ApiError } from '@/api/client'
import { AdminOnly, LoginLink } from '@/auth/RequireAuth'
import { useCreateReview, useDeleteMovie, useMovie, useMovieReviews } from '@/api/queries'
import type { MovieDetail, Person } from '@/api/types'
import { StatusMessage } from '@/components/StatusMessage'
import {
  ConfirmDialog,
  FieldError,
  Pagination,
  Poster,
  RatingBadge,
  Spinner,
} from '@/components/ui'
import { formatDate, formatDateTime, formatDuration, formatRating, formatUsd } from '@/lib/format'
import { genreLabel } from '@/lib/genres'

export function MovieDetailPage() {
  const { movieId = '' } = useParams()
  const movie = useMovie(movieId)

  if (movie.isPending) return <Spinner label="Carregando filme…" />
  if (movie.isError) {
    return (
      <StatusMessage
        tone="error"
        title={movie.error.message}
        action={
          <Link to="/" className="btn-ghost">
            Voltar ao catálogo
          </Link>
        }
      />
    )
  }
  return <MovieView movie={movie.data} />
}

function MovieView({ movie }: { movie: MovieDetail }) {
  const navigate = useNavigate()
  const deleteMovie = useDeleteMovie()
  const [confirming, setConfirming] = useState(false)

  const onDelete = () =>
    deleteMovie.mutate(movie.id, {
      onSuccess: () => {
        toast.success(`“${movie.titulo}” foi excluído.`)
        navigate('/', { replace: true })
      },
      onError: (error) => toast.error(error.message),
    })

  const facts = [
    movie.ano_lancamento,
    formatDuration(movie.duracao_minutos),
    movie.status_filme,
  ].filter(Boolean)

  return (
    <article>
      {movie.url_backdrop && (
        <div
          aria-hidden
          className="-mx-4 -mt-8 mb-8 h-56 bg-cover bg-center sm:h-72"
          style={{
            backgroundImage: `linear-gradient(to bottom, transparent, var(--color-bg)), url(${movie.url_backdrop})`,
          }}
        />
      )}

      <div className="grid gap-8 md:grid-cols-[220px_1fr]">
        <Poster src={movie.url_poster} title={movie.titulo} className="max-w-56 shadow-2xl" />

        <div>
          <h1 className="text-4xl font-bold sm:text-5xl">{movie.titulo}</h1>
          {facts.length > 0 && <p className="meta mt-2">{facts.join(' · ')}</p>}
          {movie.generos.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {movie.generos.map((genre) => (
                <li key={genre.id}>
                  <Link to={`/?genre=${genre.id}`} className="chip hover:bg-border">
                    {genreLabel(genre.nome)}
                  </Link>
                </li>
              ))}
            </ul>
          )}

          <div className="card mt-6 inline-flex flex-col p-4">
            <span className="meta">Média geral</span>
            <RatingBadge rating={movie.avaliacao} size="lg" />
          </div>

          {movie.sinopse && <p className="mt-6 max-w-prose leading-relaxed">{movie.sinopse}</p>}

          <AdminOnly>
            <div className="mt-6 flex flex-wrap gap-2">
              <Link to={`/movies/${movie.id}/edit`} className="btn-ghost">
                Editar
              </Link>
              <button className="btn-danger" onClick={() => setConfirming(true)}>
                Excluir
              </button>
            </div>
          </AdminOnly>
        </div>
      </div>

      <MovieFacts movie={movie} />
      <ReviewsSection movieId={movie.id} />

      <ConfirmDialog
        open={confirming}
        title="Excluir filme?"
        confirmLabel="Excluir definitivamente"
        pending={deleteMovie.isPending}
        onConfirm={onDelete}
        onCancel={() => setConfirming(false)}
      >
        “{movie.titulo}” e todas as suas {movie.avaliacao.qtd_avaliacoes} avaliações serão
        removidos. Essa ação não pode ser desfeita.
      </ConfirmDialog>
    </article>
  )
}

function PeopleList({ people, limit }: { people: Person[]; limit?: number }) {
  const [expanded, setExpanded] = useState(false)
  const visible = limit && !expanded ? people.slice(0, limit) : people
  return (
    <>
      {visible.map((person) => person.nome).join(', ')}
      {limit && people.length > limit && (
        <button className="ml-2 text-accent hover:underline" onClick={() => setExpanded(!expanded)}>
          {expanded ? 'ver menos' : `+${people.length - limit}`}
        </button>
      )}
    </>
  )
}

function MovieFacts({ movie }: { movie: MovieDetail }) {
  const perf = movie.desempenho
  const rows: [string, ReactNode][] = [
    ['Direção', movie.diretores.length > 0 && <PeopleList key="d" people={movie.diretores} />],
    ['Roteiro', movie.roteiristas.length > 0 && <PeopleList key="r" people={movie.roteiristas} />],
    ['Elenco', movie.elenco.length > 0 && <PeopleList key="e" people={movie.elenco} limit={12} />],
    ['Produção', movie.produtoras.join(', ')],
    ['Lançamento', formatDate(movie.data_lancamento)],
    ['Orçamento', formatUsd(perf?.orcamento_usd)],
    ['Bilheteria', formatUsd(perf?.receita_usd)],
    [
      'Nota TMDB',
      perf?.nota_tmdb ? `${formatRating(perf.nota_tmdb)} (${perf.qtd_tmdb ?? 0} votos)` : null,
    ],
    [
      'Nota IMDb',
      perf?.nota_imdb ? `${formatRating(perf.nota_imdb)} (${perf.qtd_imdb ?? 0} votos)` : null,
    ],
  ]
  const filled = rows.filter(([, value]) => value)
  if (filled.length === 0) return null

  return (
    <section className="mt-12">
      <h2 className="mb-4 text-2xl font-bold">Ficha técnica</h2>
      <dl className="card grid gap-x-6 gap-y-3 p-5 sm:grid-cols-[140px_1fr]">
        {filled.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="meta font-semibold">{label}</dt>
            <dd className="text-sm">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

// --------------------------------------------------------------------------- //
// Avaliações
// --------------------------------------------------------------------------- //

function ReviewsSection({ movieId }: { movieId: string }) {
  const [page, setPage] = useState(1)
  const reviews = useMovieReviews(movieId, page)

  return (
    <section className="mt-12 grid gap-8 lg:grid-cols-[1fr_360px]">
      <div>
        <h2 className="mb-4 text-2xl font-bold">
          Avaliações{' '}
          {reviews.data && <span className="meta font-sans">({reviews.data.total})</span>}
        </h2>
        {reviews.isPending ? (
          <Spinner label="Carregando avaliações…" />
        ) : reviews.isError ? (
          <StatusMessage tone="error" title={reviews.error.message} />
        ) : reviews.data.items.length === 0 ? (
          <p className="meta card p-5">Ainda não há avaliações. Seja o primeiro!</p>
        ) : (
          <>
            <ul className={`space-y-3 ${reviews.isPlaceholderData ? 'opacity-60' : ''}`}>
              {reviews.data.items.map((review) => (
                <li key={review.id} className="card p-4">
                  <div className="flex items-baseline justify-between gap-3">
                    <strong>{review.nome}</strong>
                    <span className="font-display text-lg font-bold text-highlight">
                      {formatRating(review.nota)}
                    </span>
                  </div>
                  <p className="mt-1 text-sm leading-relaxed whitespace-pre-line">
                    {review.comentario}
                  </p>
                  <time className="meta mt-2 block text-xs" dateTime={review.created_at}>
                    {formatDateTime(review.created_at)}
                  </time>
                </li>
              ))}
            </ul>
            <Pagination page={page} pages={reviews.data.pages} onChange={setPage} />
          </>
        )}
      </div>
      <AdminOnly
        fallback={
          <div className="card h-fit space-y-3 p-5">
            <h3 className="text-xl font-bold">Avaliar este filme</h3>
            <p className="meta">Avaliações são publicadas pelo administrador.</p>
            <LoginLink className="btn-primary w-full">Entrar para avaliar</LoginLink>
          </div>
        }
      >
        <ReviewForm movieId={movieId} onCreated={() => setPage(1)} />
      </AdminOnly>
    </section>
  )
}

const reviewSchema = z.object({
  nome: z.string().trim().min(1, 'Informe seu nome').max(120, 'Máximo de 120 caracteres'),
  nota: z
    .string()
    .trim()
    .min(1, 'Dê uma nota de 0 a 10')
    .refine(
      (value) => !Number.isNaN(Number(value)) && +value >= 0 && +value <= 10,
      'A nota vai de 0 a 10',
    ),
  comentario: z
    .string()
    .trim()
    .min(1, 'Escreva sua resenha')
    .max(4000, 'Máximo de 4000 caracteres'),
})
type ReviewValues = z.input<typeof reviewSchema>

function ReviewForm({ movieId, onCreated }: { movieId: string; onCreated: () => void }) {
  const createReview = useCreateReview(movieId)
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    control,
    formState: { errors },
  } = useForm<ReviewValues>({
    resolver: zodResolver(reviewSchema),
    defaultValues: { nome: '', nota: '', comentario: '' },
  })
  const nota = Number(useWatch({ control, name: 'nota' }) || 0)

  const onSubmit = async (values: ReviewValues) => {
    try {
      const created = await createReview.mutateAsync({
        nome: values.nome.trim(),
        nota: Number(values.nota),
        comentario: values.comentario.trim(),
      })
      toast.success(`Avaliação publicada. Nova média: ${formatRating(created.avaliacao.media)}`)
      reset()
      onCreated()
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Erro ao publicar a avaliação.')
    }
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className="card h-fit space-y-4 p-5 lg:sticky lg:top-20"
    >
      <h3 className="text-xl font-bold">Avaliar este filme</h3>
      <div>
        <label htmlFor="review-nome" className="label">
          Seu nome
        </label>
        <input
          id="review-nome"
          className="input"
          aria-invalid={Boolean(errors.nome)}
          {...register('nome')}
        />
        <FieldError message={errors.nome?.message} />
      </div>
      <div>
        <label htmlFor="review-nota" className="label">
          Nota (0 a 10)
        </label>
        <div className="flex items-center gap-3">
          <input
            id="review-nota"
            type="number"
            min={0}
            max={10}
            step={0.5}
            className="input w-24"
            aria-invalid={Boolean(errors.nota)}
            {...register('nota')}
          />
          {/* Atalho visual: cada estrela vale 2 pontos. */}
          <div className="flex text-2xl" aria-hidden>
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                tabIndex={-1}
                className={nota >= star * 2 - 1 ? 'text-highlight' : 'text-border'}
                onClick={() => setValue('nota', String(star * 2), { shouldValidate: true })}
              >
                ★
              </button>
            ))}
          </div>
        </div>
        <FieldError message={errors.nota?.message} />
      </div>
      <div>
        <label htmlFor="review-comentario" className="label">
          Resenha
        </label>
        <textarea
          id="review-comentario"
          rows={4}
          className="input resize-y"
          aria-invalid={Boolean(errors.comentario)}
          {...register('comentario')}
        />
        <FieldError message={errors.comentario?.message} />
      </div>
      <button type="submit" className="btn-primary w-full" disabled={createReview.isPending}>
        {createReview.isPending ? 'Publicando…' : 'Publicar avaliação'}
      </button>
    </form>
  )
}
