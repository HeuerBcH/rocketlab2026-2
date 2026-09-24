import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'

import { api, request } from './client'
import type {
  Genre,
  MovieCreate,
  MovieDetail,
  MovieListParams,
  MoviePage,
  MovieUpdate,
  Person,
  ReviewCreate,
  ReviewCreated,
  ReviewPage,
} from './types'

/**
 * Chaves de cache hierárquicas: invalidar `movieKeys.lists()` atualiza todas as
 * páginas/buscas do catálogo de uma vez, sem tocar nos detalhes.
 */
export const movieKeys = {
  all: ['movies'] as const,
  lists: () => [...movieKeys.all, 'list'] as const,
  list: (params: MovieListParams) => [...movieKeys.lists(), params] as const,
  detail: (id: string) => [...movieKeys.all, 'detail', id] as const,
  reviews: (id: string) => [...movieKeys.all, 'reviews', id] as const,
  reviewPage: (id: string, page: number, pageSize: number) =>
    [...movieKeys.reviews(id), { page, pageSize }] as const,
}

export const genreKeys = { all: ['genres'] as const }
export const peopleKeys = {
  search: (q: string, tipo?: Person['tipo']) => ['people', { q, tipo }] as const,
}

// --------------------------------------------------------------------------- //
// Leitura
// --------------------------------------------------------------------------- //

export function useMovies(params: MovieListParams) {
  return useQuery({
    queryKey: movieKeys.list(params),
    queryFn: ({ signal }) =>
      request<MoviePage>(() => api.GET('/api/v1/movies', { params: { query: params }, signal })),
    // Mantém a página anterior visível enquanto a próxima carrega (sem "piscar").
    placeholderData: keepPreviousData,
  })
}

export function useMovie(id: string) {
  return useQuery({
    queryKey: movieKeys.detail(id),
    queryFn: ({ signal }) =>
      request<MovieDetail>(() =>
        api.GET('/api/v1/movies/{movie_id}', { params: { path: { movie_id: id } }, signal }),
      ),
  })
}

export function useMovieReviews(id: string, page: number, pageSize = 10) {
  return useQuery({
    queryKey: movieKeys.reviewPage(id, page, pageSize),
    queryFn: ({ signal }) =>
      request<ReviewPage>(() =>
        api.GET('/api/v1/movies/{movie_id}/reviews', {
          params: { path: { movie_id: id }, query: { page, page_size: pageSize } },
          signal,
        }),
      ),
    placeholderData: keepPreviousData,
  })
}

export function useGenres() {
  return useQuery({
    queryKey: genreKeys.all,
    queryFn: ({ signal }) => request<Genre[]>(() => api.GET('/api/v1/genres', { signal })),
    // Gêneros mudam raramente; só são invalidados quando um cadastro cria um novo.
    staleTime: 10 * 60 * 1000,
  })
}

/** Autocomplete de pessoas; só consulta a partir de 2 caracteres. */
export function usePeopleSearch(q: string, tipo?: Person['tipo']) {
  const term = q.trim()
  return useQuery({
    queryKey: peopleKeys.search(term, tipo),
    queryFn: ({ signal }) =>
      request<Person[]>(() =>
        api.GET('/api/v1/people', { params: { query: { q: term, tipo, limit: 8 } }, signal }),
      ),
    enabled: term.length >= 2,
    staleTime: 5 * 60 * 1000,
  })
}

// --------------------------------------------------------------------------- //
// Escrita
// --------------------------------------------------------------------------- //

/** Após salvar um filme: guarda o detalhe novo e marca catálogo e gêneros como desatualizados. */
function onMovieSaved(queryClient: QueryClient, movie: MovieDetail) {
  queryClient.setQueryData(movieKeys.detail(movie.id), movie)
  void queryClient.invalidateQueries({ queryKey: movieKeys.lists() })
  // O cadastro pode ter criado gêneros novos.
  void queryClient.invalidateQueries({ queryKey: genreKeys.all })
}

export function useCreateMovie() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: MovieCreate) =>
      request<MovieDetail>(() => api.POST('/api/v1/movies', { body })),
    onSuccess: (movie) => onMovieSaved(queryClient, movie),
  })
}

export function useUpdateMovie(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: MovieUpdate) =>
      request<MovieDetail>(() =>
        api.PATCH('/api/v1/movies/{movie_id}', { params: { path: { movie_id: id } }, body }),
      ),
    onSuccess: (movie) => onMovieSaved(queryClient, movie),
  })
}

export function useDeleteMovie() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      request<unknown>(() =>
        api.DELETE('/api/v1/movies/{movie_id}', { params: { path: { movie_id: id } } }),
      ),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: movieKeys.detail(id) })
      queryClient.removeQueries({ queryKey: movieKeys.reviews(id) })
      void queryClient.invalidateQueries({ queryKey: movieKeys.lists() })
    },
  })
}

export function useCreateReview(movieId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ReviewCreate) =>
      request<ReviewCreated>(() =>
        api.POST('/api/v1/movies/{movie_id}/reviews', {
          params: { path: { movie_id: movieId } },
          body,
        }),
      ),
    onSuccess: (review) => {
      // A API já devolve a média recalculada: atualiza o detalhe sem nova requisição.
      queryClient.setQueryData<MovieDetail>(movieKeys.detail(movieId), (movie) =>
        movie ? { ...movie, avaliacao: review.avaliacao } : movie,
      )
      void queryClient.invalidateQueries({ queryKey: movieKeys.reviews(movieId) })
      // Média e contagem aparecem nos cards e nas ordenações do catálogo.
      void queryClient.invalidateQueries({ queryKey: movieKeys.lists() })
    },
  })
}
