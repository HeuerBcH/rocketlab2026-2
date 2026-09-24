import type { ReactNode } from 'react'

interface StatusMessageProps {
  title: string
  description?: ReactNode
  action?: ReactNode
  tone?: 'neutral' | 'error'
}

/** Bloco padrão para estados vazios, erros e 404. */
export function StatusMessage({
  title,
  description,
  action,
  tone = 'neutral',
}: StatusMessageProps) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className="mx-auto flex max-w-md flex-col items-center gap-3 py-16 text-center"
    >
      <h2 className={`text-xl font-semibold ${tone === 'error' ? 'text-danger' : ''}`}>{title}</h2>
      {description && <p className="text-muted">{description}</p>}
      {action}
    </div>
  )
}
