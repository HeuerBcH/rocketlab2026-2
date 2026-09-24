import { describe, expect, it } from 'vitest'

import { findGenre, genreLabel } from './genres'

const genres = [
  { id: '1', nome: 'Action' },
  { id: '2', nome: 'Science Fiction' },
  { id: '3', nome: 'Biografia' }, // criado no sistema, sem tradução
]

describe('genreLabel', () => {
  it('traduz os gêneros do TMDB e mantém os demais', () => {
    expect(genreLabel('Action')).toBe('Ação')
    expect(genreLabel('Science Fiction')).toBe('Ficção científica')
    expect(genreLabel('Biografia')).toBe('Biografia')
  })
})

describe('findGenre', () => {
  it.each([
    ['Ação', '1'],
    ['acao', '1'],
    ['ACTION', '1'],
    ['ficcao cientifica', '2'],
    ['  biografia ', '3'],
  ])('"%s" encontra o gênero existente', (typed, id) => {
    expect(findGenre(genres, typed)?.id).toBe(id)
  })

  it('retorna undefined para gênero novo', () => {
    expect(findGenre(genres, 'Musical')).toBeUndefined()
  })
})
