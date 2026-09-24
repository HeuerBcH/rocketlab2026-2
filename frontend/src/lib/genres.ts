/**
 * Os gêneros do dataset (TMDB) estão em inglês no banco. A tradução acontece só
 * na exibição: o valor enviado à API continua sendo o nome original, então
 * filtros e cadastros reaproveitam o gênero existente em vez de criar duplicatas.
 */
const GENRE_LABELS: Record<string, string> = {
  Action: 'Ação',
  Adventure: 'Aventura',
  Animation: 'Animação',
  Comedy: 'Comédia',
  Crime: 'Crime',
  Documentary: 'Documentário',
  Drama: 'Drama',
  Family: 'Família',
  Fantasy: 'Fantasia',
  History: 'História',
  Horror: 'Terror',
  Music: 'Música',
  Mystery: 'Mistério',
  Romance: 'Romance',
  'Science Fiction': 'Ficção científica',
  Thriller: 'Suspense',
  'Tv Movie': 'Filme para TV',
  War: 'Guerra',
  Western: 'Faroeste',
}

/** Nome do gênero para exibição em português (gêneros criados no sistema ficam como estão). */
export function genreLabel(name: string): string {
  return GENRE_LABELS[name] ?? name
}

function normalize(value: string): string {
  return value.normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase('pt-BR').trim()
}

/**
 * Encontra o gênero existente que corresponde ao texto digitado, pelo nome
 * original ou pela tradução (ex.: "acao" → "Action"), ignorando acentos.
 */
export function findGenre<T extends { nome: string }>(genres: T[], typed: string): T | undefined {
  const key = normalize(typed)
  return genres.find(
    (genre) => normalize(genre.nome) === key || normalize(genreLabel(genre.nome)) === key,
  )
}
