import { useEffect, useState, type ReactNode } from 'react'

import type { RatingSummary } from '@/api/types'
import { formatRating, formatReviewCount } from '@/lib/format'

/** Pôster com fallback tipográfico quando não há imagem (≈9% do catálogo). */
export function Poster({
  src,
  title,
  className = '',
}: {
  src: string | null
  title: string
  className?: string
}) {
  const [failed, setFailed] = useState(false)
  const base = `aspect-[2/3] w-full rounded-xl bg-surface-2 ${className}`

  if (!src || failed) {
    return (
      <div className={`${base} flex items-center justify-center p-3`} aria-hidden>
        <span className="line-clamp-4 text-center font-display text-lg font-semibold text-muted">
          {title}
        </span>
      </div>
    )
  }
  return (
    <img
      src={src}
      alt={`Pôster de ${title}`}
      loading="lazy"
      onError={() => setFailed(true)}
      className={`${base} object-cover`}
    />
  )
}

/** Média geral em destaque: número grande + contagem. */
export function RatingBadge({
  rating,
  size = 'sm',
}: {
  rating: RatingSummary
  size?: 'sm' | 'lg'
}) {
  const empty = rating.media == null
  return (
    <div
      className={`inline-flex items-baseline gap-2 ${size === 'lg' ? 'text-4xl' : 'text-lg'}`}
      aria-label={
        empty
          ? 'Sem avaliações'
          : `Média ${formatRating(rating.media)} de 10, ${formatReviewCount(rating.qtd_avaliacoes)}`
      }
    >
      <span className={`font-display font-bold ${empty ? 'text-muted' : 'text-highlight'}`}>
        {formatRating(rating.media)}
      </span>
      <span className="meta">
        {empty ? 'sem notas' : `/10 · ${formatReviewCount(rating.qtd_avaliacoes)}`}
      </span>
    </div>
  )
}

export function Spinner({ label = 'Carregando…' }: { label?: string }) {
  return (
    <p role="status" className="meta animate-pulse py-12 text-center">
      {label}
    </p>
  )
}

export function FieldError({ message }: { message?: string }) {
  return message ? <p className="field-error">{message}</p> : null
}

/** Diálogo de confirmação acessível (overlay simples, fecha com Esc). */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  pending,
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  children: ReactNode
  confirmLabel: string
  pending?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onCancel()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onCancel])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="card w-full max-w-md p-6"
      >
        <h2 id="confirm-title" className="mb-2 text-2xl font-bold">
          {title}
        </h2>
        <div className="mb-6 text-sm text-muted">{children}</div>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-ghost" onClick={onCancel} autoFocus>
            Cancelar
          </button>
          <button type="button" className="btn-danger" onClick={onConfirm} disabled={pending}>
            {pending ? 'Excluindo…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

/** Paginação com janela de páginas: « 1 … 4 5 6 … 20 ». */
export function Pagination({
  page,
  pages,
  onChange,
}: {
  page: number
  pages: number
  onChange: (page: number) => void
}) {
  if (pages <= 1) return null
  const visible = new Set([1, pages, page - 1, page, page + 1].filter((p) => p >= 1 && p <= pages))
  const items = [...visible].sort((a, b) => a - b)

  return (
    <nav aria-label="Paginação" className="mt-8 flex flex-wrap items-center justify-center gap-1">
      <button className="btn-ghost px-3" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Anterior
      </button>
      {items.map((p, index) => (
        <span key={p} className="flex items-center gap-1">
          {index > 0 && p - items[index - 1] > 1 && <span className="meta px-1">…</span>}
          <button
            className={`btn min-w-10 px-3 ${p === page ? 'bg-accent text-bg' : 'bg-surface-2 hover:bg-border'}`}
            aria-current={p === page ? 'page' : undefined}
            onClick={() => onChange(p)}
          >
            {p}
          </button>
        </span>
      ))}
      <button
        className="btn-ghost px-3"
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        Próxima →
      </button>
    </nav>
  )
}
