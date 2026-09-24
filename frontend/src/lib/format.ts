const numberFormat = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

/** Nota na escala 0–10 com uma casa decimal (ex.: "8,5"); "–" quando não há. */
export function formatRating(value: number | null | undefined): string {
  return value == null ? '–' : numberFormat.format(value)
}

/** "1 avaliação" / "12 avaliações" / "Sem avaliações". */
export function formatReviewCount(count: number): string {
  if (count === 0) return 'Sem avaliações'
  return `${count.toLocaleString('pt-BR')} ${count === 1 ? 'avaliação' : 'avaliações'}`
}

/** Duração em minutos para "2h 17min". */
export function formatDuration(minutes: number | null | undefined): string | null {
  if (!minutes) return null
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (hours === 0) return `${rest}min`
  return rest === 0 ? `${hours}h` : `${hours}h ${rest}min`
}

/** Data ISO (AAAA-MM-DD) para "07/11/2024", sem deslocamento de fuso. */
export function formatDate(iso: string | null | undefined): string | null {
  if (!iso) return null
  const [year, month, day] = iso.split('-')
  return `${day}/${month}/${year}`
}

const dateTimeFormat = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'short',
})

/** Data/hora UTC da API no fuso local do navegador. */
export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso))
}

const compactCurrency = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
})

/** Valor em dólares no formato compacto (ex.: "US$ 25 mi"). */
export function formatUsd(value: number | null | undefined): string | null {
  return value ? compactCurrency.format(value) : null
}
