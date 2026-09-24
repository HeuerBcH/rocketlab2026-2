import { describe, expect, it } from 'vitest'

import { formatDate, formatDuration, formatRating, formatReviewCount, formatUsd } from './format'

describe('formatRating', () => {
  it.each([
    [8.5, '8,5'],
    [10, '10,0'],
    [0, '0,0'],
    [7.333, '7,3'],
    [null, '–'],
    [undefined, '–'],
  ])('%s → %s', (value, expected) => {
    expect(formatRating(value)).toBe(expected)
  })
})

describe('formatReviewCount', () => {
  it.each([
    [0, 'Sem avaliações'],
    [1, '1 avaliação'],
    [1234, '1.234 avaliações'],
  ])('%s → %s', (count, expected) => {
    expect(formatReviewCount(count)).toBe(expected)
  })
})

describe('formatDuration', () => {
  it.each([
    [137, '2h 17min'],
    [120, '2h'],
    [45, '45min'],
    [null, null],
    [0, null],
  ])('%s → %s', (minutes, expected) => {
    expect(formatDuration(minutes)).toBe(expected)
  })
})

describe('formatDate', () => {
  it('formata sem deslocar o dia por fuso horário', () => {
    expect(formatDate('2024-11-07')).toBe('07/11/2024')
    expect(formatDate('2024-01-01')).toBe('01/01/2024')
    expect(formatDate(null)).toBeNull()
  })
})

describe('formatUsd', () => {
  it('usa notação compacta e ignora valores ausentes', () => {
    expect(formatUsd(25_000_000)).toMatch(/US\$\s?25\s?mi/)
    expect(formatUsd(null)).toBeNull()
    expect(formatUsd(0)).toBeNull()
  })
})
