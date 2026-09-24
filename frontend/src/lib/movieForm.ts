import { z } from 'zod'

import type { MovieCreate, MovieDetail, MovieStatus, MovieUpdate } from '@/api/types'

export const STATUS_OPTIONS: MovieStatus[] = ['Lançado', 'Pós-Produção', 'Em Produção', 'Planejado']

const optionalInt = (min: number, max: number, message: string) =>
  z
    .string()
    .trim()
    .refine(
      (value) => value === '' || (/^\d+$/.test(value) && +value >= min && +value <= max),
      message,
    )

const optionalUrl = z
  .string()
  .trim()
  .max(2048, 'URL muito longa')
  .refine(
    (value) => value === '' || /^https?:\/\/\S+$/.test(value),
    'Informe uma URL http(s) válida',
  )

/**
 * Regras espelham a API: só o título é obrigatório (único NOT NULL no modelo);
 * os demais campos são opcionais, mas validados quando preenchidos.
 * Os valores ficam como texto no formulário e são convertidos no envio.
 */
export const movieFormSchema = z
  .object({
    titulo: z.string().trim().min(1, 'Informe o título').max(500, 'Máximo de 500 caracteres'),
    ano_lancamento: optionalInt(1888, 2100, 'Ano entre 1888 e 2100'),
    data_lancamento: z.string(),
    duracao_minutos: optionalInt(1, 1000, 'Duração entre 1 e 1000 minutos'),
    status_filme: z.union([
      z.enum(STATUS_OPTIONS as [MovieStatus, ...MovieStatus[]]),
      z.literal(''),
    ]),
    generos: z.array(z.string()).max(10, 'Máximo de 10 gêneros'),
    diretores: z.array(z.string()).max(10, 'Máximo de 10 diretores'),
    sinopse: z.string().trim().max(4000, 'Máximo de 4000 caracteres'),
    url_poster: optionalUrl,
    url_backdrop: optionalUrl,
  })
  .refine(
    (values) =>
      !values.data_lancamento ||
      !values.ano_lancamento ||
      values.data_lancamento.startsWith(values.ano_lancamento.trim()),
    { path: ['data_lancamento'], message: 'A data deve ser do mesmo ano de lançamento' },
  )

export type MovieFormValues = z.input<typeof movieFormSchema>

export const emptyMovieForm: MovieFormValues = {
  titulo: '',
  ano_lancamento: '',
  data_lancamento: '',
  duracao_minutos: '',
  status_filme: '',
  generos: [],
  diretores: [],
  sinopse: '',
  url_poster: '',
  url_backdrop: '',
}

/** Preenche o formulário de edição a partir do detalhe do filme. */
export function movieToForm(movie: MovieDetail): MovieFormValues {
  return {
    titulo: movie.titulo,
    ano_lancamento: movie.ano_lancamento?.toString() ?? '',
    data_lancamento: movie.data_lancamento ?? '',
    duracao_minutos: movie.duracao_minutos?.toString() ?? '',
    // O catálogo importado só usa as situações de STATUS_OPTIONS.
    status_filme: (movie.status_filme ?? '') as MovieFormValues['status_filme'],
    generos: movie.generos.map((genre) => genre.nome),
    diretores: movie.diretores.map((person) => person.nome),
    sinopse: movie.sinopse ?? '',
    url_poster: movie.url_poster ?? '',
    url_backdrop: movie.url_backdrop ?? '',
  }
}

const orNull = (value: string) => (value.trim() === '' ? null : value.trim())
const intOrNull = (value: string) => (value.trim() === '' ? null : Number(value))

/** Converte os valores do formulário no corpo aceito pela API. */
export function formToPayload(values: MovieFormValues): MovieCreate {
  return {
    titulo: values.titulo.trim(),
    ano_lancamento: intOrNull(values.ano_lancamento),
    data_lancamento: orNull(values.data_lancamento),
    duracao_minutos: intOrNull(values.duracao_minutos),
    status_filme: values.status_filme || null,
    generos: values.generos,
    diretores: values.diretores,
    sinopse: orNull(values.sinopse),
    url_poster: orNull(values.url_poster),
    url_backdrop: orNull(values.url_backdrop),
  }
}

/**
 * Na edição, envia só os campos alterados. Filmes importados sem gênero/diretor
 * continuam editáveis, e o PATCH não reescreve o que o usuário não tocou.
 */
export function changedFields(initial: MovieFormValues, values: MovieFormValues): MovieUpdate {
  const before = formToPayload(initial)
  const after = formToPayload(values)
  const changes: Record<string, unknown> = {}
  for (const key of Object.keys(after) as (keyof MovieCreate)[]) {
    if (JSON.stringify(before[key]) !== JSON.stringify(after[key])) changes[key] = after[key]
  }
  return changes as MovieUpdate
}
