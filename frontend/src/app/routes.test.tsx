import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { MovieDetail, MoviePage, ReviewPage } from '@/api/types'
import { json, mockApi, renderRoute } from '@/test/utils'

const listItem = {
  id: 'm1',
  titulo: 'Cidade de Deus',
  ano_lancamento: 2002,
  url_poster: null,
  generos: ['Drama', 'Crime'],
  avaliacao: { media: 8.5, qtd_avaliacoes: 2 },
}

const page = (items = [listItem]): MoviePage => ({
  items,
  total: items.length,
  page: 1,
  page_size: 24,
  pages: items.length ? 1 : 0,
})

const movie: MovieDetail = {
  id: 'm1',
  id_filme: '598',
  titulo: 'Cidade de Deus',
  data_lancamento: '2002-08-31',
  ano_lancamento: 2002,
  duracao_minutos: 130,
  status_filme: 'Lançado',
  sinopse: 'Buscapé cresce na Cidade de Deus.',
  url_poster: null,
  url_backdrop: null,
  generos: [{ id: 'g1', nome: 'Drama' }],
  diretores: [{ id: 'p1', nome: 'Fernando Meirelles', tipo: 'Diretor' }],
  roteiristas: [],
  elenco: [{ id: 'p2', nome: 'Alice Braga', tipo: 'Ator' }],
  produtoras: ['O2 Filmes'],
  desempenho: null,
  avaliacao: { media: 8.5, qtd_avaliacoes: 2 },
}

const reviews: ReviewPage = {
  items: [
    {
      id: 'r1',
      nome: 'Ana',
      nota: 9,
      comentario: 'Obra-prima.',
      created_at: '2026-01-02T10:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 10,
  pages: 1,
}

const genres = [
  { id: 'g1', nome: 'Drama' },
  { id: 'g2', nome: 'Action' },
]

describe('catálogo', () => {
  it('lista filmes com gêneros traduzidos e média', async () => {
    mockApi({ 'GET /api/v1/movies': () => json(page()), 'GET /api/v1/genres': () => json(genres) })

    renderRoute('/')

    const card = await screen.findByRole('link', { name: /Cidade de Deus/ })
    expect(card).toHaveAttribute('href', '/movies/m1')
    expect(within(card).getByText('2002 · Drama, Crime')).toBeInTheDocument()
    expect(within(card).getByLabelText('Média 8,5 de 10, 2 avaliações')).toBeInTheDocument()
    expect(screen.getByText('1 filme')).toBeInTheDocument()
    // Gêneros do filtro aparecem traduzidos.
    expect(await screen.findByRole('option', { name: 'Ação' })).toBeInTheDocument()
  })

  it('busca com debounce e mostra estado vazio com opção de limpar', async () => {
    const queries: (string | null)[] = []
    mockApi({
      'GET /api/v1/genres': () => json(genres),
      'GET /api/v1/movies': (request) => {
        const q = new URL(request.url).searchParams.get('q')
        queries.push(q)
        return json(page(q ? [] : [listItem]))
      },
    })
    const { router } = renderRoute('/')
    await screen.findByRole('heading', { name: 'Cidade de Deus' })

    await userEvent.type(screen.getByRole('searchbox'), 'xyz')

    expect(await screen.findByText('Nenhum filme encontrado')).toBeInTheDocument()
    expect(router.state.location.search).toBe('?q=xyz')
    expect(queries).toEqual([null, 'xyz']) // uma requisição só, não uma por tecla

    await userEvent.click(screen.getByRole('button', { name: 'Limpar filtros' }))
    expect(await screen.findByRole('heading', { name: 'Cidade de Deus' })).toBeInTheDocument()
    expect(screen.getByRole('searchbox')).toHaveValue('')
  })

  it('mostra erro amigável quando a API está fora do ar', async () => {
    mockApi({})

    renderRoute('/')

    expect(await screen.findByRole('alert')).toHaveTextContent(/Não foi possível conectar/)
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  })
})

describe('detalhe', () => {
  it('mostra informações, média e avaliações', async () => {
    mockApi({
      'GET /api/v1/movies/m1': () => json(movie),
      'GET /api/v1/movies/m1/reviews': () => json(reviews),
    })

    renderRoute('/movies/m1')

    expect(await screen.findByRole('heading', { name: 'Cidade de Deus' })).toBeInTheDocument()
    expect(screen.getByText('2002 · 2h 10min · Lançado')).toBeInTheDocument()
    expect(screen.getByText('Fernando Meirelles')).toBeInTheDocument()
    expect(screen.getByLabelText('Média 8,5 de 10, 2 avaliações')).toBeInTheDocument()
    expect(await screen.findByText('Obra-prima.')).toBeInTheDocument()
  })

  it('publica avaliação e atualiza a média sem recarregar', async () => {
    let posted: unknown
    mockApi({
      'GET /api/v1/movies/m1': () => json(movie),
      'GET /api/v1/movies/m1/reviews': () => json(reviews),
      'POST /api/v1/movies/m1/reviews': async (request) => {
        posted = await request.json()
        return json(
          {
            id: 'r2',
            nome: 'Bia',
            nota: 6,
            comentario: 'Bom.',
            created_at: '2026-09-24T12:00:00Z',
            avaliacao: { media: 7.7, qtd_avaliacoes: 3 },
          },
          201,
        )
      },
    })
    renderRoute('/movies/m1', { authenticated: true })
    await screen.findByText('Obra-prima.')

    await userEvent.click(screen.getByRole('button', { name: 'Publicar avaliação' }))
    expect(await screen.findByText('Informe seu nome')).toBeInTheDocument()
    expect(screen.getByText('Dê uma nota de 0 a 10')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Seu nome'), 'Bia')
    await userEvent.type(screen.getByLabelText('Nota (0 a 10)'), '6')
    await userEvent.type(screen.getByLabelText('Resenha'), 'Bom.')
    await userEvent.click(screen.getByRole('button', { name: 'Publicar avaliação' }))

    expect(await screen.findByLabelText('Média 7,7 de 10, 3 avaliações')).toBeInTheDocument()
    expect(posted).toEqual({ nome: 'Bia', nota: 6, comentario: 'Bom.' })
    expect(screen.getByLabelText('Seu nome')).toHaveValue('')
  })

  it('exclui após confirmação e volta ao catálogo', async () => {
    let deleted = false
    mockApi({
      'GET /api/v1/movies/m1': () => json(movie),
      'GET /api/v1/movies/m1/reviews': () => json(reviews),
      'DELETE /api/v1/movies/m1': () => {
        deleted = true
        return new Response(null, { status: 204 })
      },
      'GET /api/v1/movies': () => json(page([])),
      'GET /api/v1/genres': () => json(genres),
    })
    const { router } = renderRoute('/movies/m1', { authenticated: true })
    await screen.findByRole('heading', { name: 'Cidade de Deus' })

    await userEvent.click(screen.getByRole('button', { name: 'Excluir' }))
    const dialog = screen.getByRole('dialog', { name: 'Excluir filme?' })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }))
    expect(deleted).toBe(false)

    await userEvent.click(screen.getByRole('button', { name: 'Excluir' }))
    await userEvent.click(screen.getByRole('button', { name: 'Excluir definitivamente' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
    expect(deleted).toBe(true)
  })

  it('filme inexistente mostra a mensagem da API', async () => {
    mockApi({ 'GET /api/v1/movies/x': () => json({ detail: 'Filme não encontrado' }, 404) })

    renderRoute('/movies/x')

    expect(await screen.findByRole('alert')).toHaveTextContent('Filme não encontrado')
  })
})

describe('formulário de filme', () => {
  it('cadastra reaproveitando gênero digitado em português', async () => {
    let posted: Record<string, unknown> = {}
    mockApi({
      'GET /api/v1/genres': () => json(genres),
      'POST /api/v1/movies': async (request) => {
        posted = await request.json()
        return json({ ...movie, id: 'novo', titulo: 'Filme Novo' }, 201)
      },
      'GET /api/v1/movies/novo/reviews': () => json({ ...reviews, items: [], total: 0 }),
    })
    const { router } = renderRoute('/movies/new', { authenticated: true })

    await userEvent.click(screen.getByRole('button', { name: 'Cadastrar filme' }))
    expect(await screen.findByText('Informe o título')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText(/Título/), 'Filme Novo')
    await userEvent.type(screen.getByLabelText('Gêneros'), 'acao{Enter}')
    await userEvent.type(screen.getByLabelText('Gêneros'), 'Biografia{Enter}')
    expect(screen.getByText('Ação')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Cadastrar filme' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/movies/novo'))
    expect(posted).toMatchObject({
      titulo: 'Filme Novo',
      generos: ['Action', 'Biografia'],
      diretores: [],
      ano_lancamento: null,
      sinopse: null,
    })
  })

  it('edição envia só os campos alterados', async () => {
    let patched: unknown
    mockApi({
      'GET /api/v1/movies/m1': () => json(movie),
      'GET /api/v1/genres': () => json(genres),
      'PATCH /api/v1/movies/m1': async (request) => {
        patched = await request.json()
        return json({ ...movie, duracao_minutos: 135 })
      },
      'GET /api/v1/movies/m1/reviews': () => json(reviews),
    })
    renderRoute('/movies/m1/edit', { authenticated: true })

    const duration = await screen.findByLabelText('Duração (min)')
    expect(screen.getByLabelText(/Título/)).toHaveValue('Cidade de Deus')
    await userEvent.clear(duration)
    await userEvent.type(duration, '135')
    await userEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))

    await waitFor(() => expect(patched).toEqual({ duracao_minutos: 135 }))
  })

  it('exibe erros de validação da API no campo', async () => {
    mockApi({
      'GET /api/v1/genres': () => json(genres),
      'POST /api/v1/movies': () =>
        json({ detail: [{ loc: ['body', 'titulo'], msg: 'Título já usado' }] }, 422),
    })
    renderRoute('/movies/new', { authenticated: true })

    await userEvent.type(screen.getByLabelText(/Título/), 'X')
    await userEvent.click(screen.getByRole('button', { name: 'Cadastrar filme' }))

    expect(await screen.findByText('Título já usado')).toBeInTheDocument()
  })
})

it('rota desconhecida mostra 404 dentro do layout', () => {
  renderRoute('/nao-existe')

  expect(screen.getByRole('heading', { name: 'Página não encontrada' })).toBeInTheDocument()
  expect(screen.getByRole('navigation', { name: 'Principal' })).toBeInTheDocument()
})
