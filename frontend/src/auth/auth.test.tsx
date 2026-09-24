import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { MovieDetail } from '@/api/types'
import { getToken, setToken } from '@/auth/session'
import { fakeToken, json, mockApi, renderRoute } from '@/test/utils'

const movie = {
  id: 'm1',
  titulo: 'Cidade de Deus',
  generos: [],
  diretores: [],
  roteiristas: [],
  elenco: [],
  produtoras: [],
  desempenho: null,
  avaliacao: { media: 8, qtd_avaliacoes: 1 },
} as unknown as MovieDetail
const emptyReviews = { items: [], total: 0, page: 1, page_size: 10, pages: 0 }
const catalog = { items: [], total: 0, page: 1, page_size: 24, pages: 0 }

const detailApi = {
  'GET /api/v1/movies/m1': () => json(movie),
  'GET /api/v1/movies/m1/reviews': () => json(emptyReviews),
}

describe('login', () => {
  it('envia formulário OAuth2, guarda o token e volta à página de origem', async () => {
    let body = ''
    let contentType: string | null = null
    mockApi({
      ...detailApi,
      'POST /api/v1/auth/token': async (request) => {
        contentType = request.headers.get('content-type')
        body = await request.text()
        return json({ access_token: fakeToken(), token_type: 'bearer', expires_in: 3600 })
      },
    })
    const { router } = renderRoute('/login?next=%2Fmovies%2Fm1')

    await userEvent.type(screen.getByLabelText('Usuário'), 'admin')
    await userEvent.type(screen.getByLabelText('Senha'), 'rocketlab123')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/movies/m1'))
    expect(contentType).toBe('application/x-www-form-urlencoded')
    expect(Object.fromEntries(new URLSearchParams(body))).toEqual({
      username: 'admin',
      password: 'rocketlab123',
    })
    expect(getToken()).not.toBeNull()
    expect(await screen.findByRole('button', { name: /admin · Sair/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Excluir' })).toBeInTheDocument()
  })

  it('mostra o erro da API com credenciais inválidas', async () => {
    mockApi({
      'POST /api/v1/auth/token': () => json({ detail: 'Usuário ou senha inválidos' }, 401),
    })
    renderRoute('/login')

    await userEvent.type(screen.getByLabelText('Usuário'), 'admin')
    await userEvent.type(screen.getByLabelText('Senha'), 'errada')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Usuário ou senha inválidos')
    expect(getToken()).toBeNull()
  })

  it('não redireciona para fora do site (open redirect)', async () => {
    mockApi({ 'GET /api/v1/movies': () => json(catalog), 'GET /api/v1/genres': () => json([]) })
    setToken(fakeToken())

    const { router } = renderRoute('/login?next=%2F%2Fsite-malicioso.com')

    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
  })
})

describe('áreas restritas', () => {
  it('cadastro sem login redireciona ao login guardando o destino', async () => {
    const { router } = renderRoute('/movies/new')

    expect(router.state.location.pathname).toBe('/login')
    expect(router.state.location.search).toBe('?next=%2Fmovies%2Fnew')
  })

  it('visitante vê o filme, mas não edita, exclui nem avalia', async () => {
    mockApi(detailApi)
    renderRoute('/movies/m1')

    await screen.findByRole('heading', { name: 'Cidade de Deus' })
    expect(screen.queryByRole('button', { name: 'Excluir' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Seu nome')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Entrar para avaliar' })).toHaveAttribute(
      'href',
      '/login?next=%2Fmovies%2Fm1',
    )
    expect(screen.queryByRole('link', { name: '+ Novo filme' })).not.toBeInTheDocument()
  })

  it('envia o token nas escritas e encerra a sessão se a API recusar', async () => {
    let authorization: string | null = null
    mockApi({
      ...detailApi,
      'POST /api/v1/movies/m1/reviews': (request) => {
        authorization = request.headers.get('authorization')
        return json({ detail: 'Sessão expirada; entre novamente' }, 401)
      },
    })
    renderRoute('/movies/m1', { authenticated: true })

    await userEvent.type(await screen.findByLabelText('Seu nome'), 'Ana')
    await userEvent.type(screen.getByLabelText('Nota (0 a 10)'), '7')
    await userEvent.type(screen.getByLabelText('Resenha'), 'Bom')
    await userEvent.click(screen.getByRole('button', { name: 'Publicar avaliação' }))

    expect(await screen.findByRole('link', { name: 'Entrar para avaliar' })).toBeInTheDocument()
    expect(authorization).toMatch(/^Bearer header\./)
    expect(getToken()).toBeNull()
  })

  it('sair encerra a sessão', async () => {
    mockApi(detailApi)
    renderRoute('/movies/m1', { authenticated: true })

    await userEvent.click(await screen.findByRole('button', { name: /admin · Sair/ }))

    expect(screen.getByRole('link', { name: 'Entrar' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Excluir' })).not.toBeInTheDocument()
  })

  it('token expirado guardado no navegador não conta como sessão', () => {
    const expired = btoa(JSON.stringify({ sub: 'admin', exp: Math.floor(Date.now() / 1000) - 1 }))
    setToken(`header.${expired}.assinatura`)

    expect(getToken()).toBeNull()
  })
})
