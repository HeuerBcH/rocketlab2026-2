import { describe, expect, it } from 'vitest'

import { changedFields, emptyMovieForm, formToPayload, movieFormSchema } from './movieForm'

const filled = {
  ...emptyMovieForm,
  titulo: ' Ainda Estou Aqui ',
  ano_lancamento: '2024',
  data_lancamento: '2024-11-07',
  duracao_minutos: '137',
  generos: ['Drama'],
  sinopse: '  ',
}

describe('formToPayload', () => {
  it('converte texto em números e vazios em null', () => {
    expect(formToPayload(filled)).toEqual({
      titulo: 'Ainda Estou Aqui',
      ano_lancamento: 2024,
      data_lancamento: '2024-11-07',
      duracao_minutos: 137,
      status_filme: null,
      generos: ['Drama'],
      diretores: [],
      sinopse: null,
      url_poster: null,
      url_backdrop: null,
    })
  })
})

describe('changedFields', () => {
  it('envia só o que mudou, inclusive limpezas', () => {
    const edited = { ...filled, duracao_minutos: '', generos: ['Drama', 'History'] }

    expect(changedFields(filled, edited)).toEqual({
      duracao_minutos: null,
      generos: ['Drama', 'History'],
    })
    expect(changedFields(filled, { ...filled, titulo: 'Ainda Estou Aqui' })).toEqual({})
  })
})

describe('movieFormSchema', () => {
  const errors = (values: typeof filled) =>
    movieFormSchema.safeParse(values).error?.issues.map((issue) => issue.path.join('.')) ?? []

  it('aceita só o título', () => {
    expect(errors({ ...emptyMovieForm, titulo: 'X' })).toEqual([])
  })

  it.each([
    [{ titulo: '  ' }, 'titulo'],
    [{ ano_lancamento: '1500' }, 'ano_lancamento'],
    [{ ano_lancamento: 'abc' }, 'ano_lancamento'],
    [{ duracao_minutos: '0' }, 'duracao_minutos'],
    [{ url_poster: 'ftp://x' }, 'url_poster'],
    [{ data_lancamento: '2023-01-01' }, 'data_lancamento'],
  ])('rejeita %o', (override, field) => {
    expect(errors({ ...filled, ...override })).toContain(field)
  })
})
