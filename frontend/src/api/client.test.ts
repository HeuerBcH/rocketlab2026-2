import { describe, expect, it, vi } from 'vitest'

import { ApiError, api, request, toApiError } from './client'
import { json, mockApi } from '@/test/utils'

describe('toApiError', () => {
  it('usa o detail textual do FastAPI', () => {
    const error = toApiError(404, { detail: 'Filme não encontrado' })

    expect(error.message).toBe('Filme não encontrado')
    expect(error.isNotFound).toBe(true)
  })

  it('mapeia erros de validação por campo', () => {
    const error = toApiError(422, {
      detail: [
        { loc: ['body', 'titulo'], msg: 'String should have at least 1 character' },
        { loc: ['body', 'generos', 0], msg: 'Invalid' },
        { loc: ['body'], msg: 'Value error, titulo não pode ser nulo' },
      ],
    })

    expect(error.fieldErrors).toEqual({
      titulo: 'String should have at least 1 character',
      'generos.0': 'Invalid',
      geral: 'titulo não pode ser nulo',
    })
  })

  it('tem mensagem padrão para corpo desconhecido', () => {
    expect(toApiError(500, undefined).message).toMatch(/servidor/)
  })
})

describe('request', () => {
  it('devolve os dados em caso de sucesso', async () => {
    mockApi({ 'GET /api/v1/genres': () => json([{ id: 'g1', nome: 'Drama' }]) })

    await expect(request(() => api.GET('/api/v1/genres'))).resolves.toEqual([
      { id: 'g1', nome: 'Drama' },
    ])
  })

  it('lança ApiError com a mensagem da API', async () => {
    mockApi({
      'GET /api/v1/movies/x': () => json({ detail: 'Filme não encontrado' }, 404),
    })

    const call = request(() =>
      api.GET('/api/v1/movies/{movie_id}', { params: { path: { movie_id: 'x' } } }),
    )
    await expect(call).rejects.toMatchObject({ status: 404, message: 'Filme não encontrado' })
  })

  it('converte falha de rede em ApiError com status 0', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    const call = request(() => api.GET('/api/v1/genres'))
    await expect(call).rejects.toBeInstanceOf(ApiError)
    await expect(call).rejects.toMatchObject({ status: 0 })
  })
})
