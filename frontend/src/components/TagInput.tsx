import { useId, useState, type KeyboardEvent } from 'react'

export interface TagOption {
  /** Valor enviado à API (ex.: "Action"). */
  value: string
  /** Texto exibido (ex.: "Ação"). */
  label: string
}

interface TagInputProps {
  label: string
  values: string[]
  onChange: (values: string[]) => void
  /** Sugestões para o texto digitado (já filtradas pelo chamador). */
  suggestions: TagOption[]
  onQueryChange: (query: string) => void
  /** Converte o texto digitado em um valor existente (ex.: "acao" → "Action"). */
  resolve?: (typed: string) => string | undefined
  renderLabel?: (value: string) => string
  placeholder?: string
  error?: string
}

/** Campo de múltiplos valores: sugere existentes e só cria novos quando o usuário escolhe. */
export function TagInput({
  label,
  values,
  onChange,
  suggestions,
  onQueryChange,
  resolve,
  renderLabel = (value) => value,
  placeholder,
  error,
}: TagInputProps) {
  const id = useId()
  const [query, setQuery] = useState('')
  const typed = query.trim().replace(/\s+/g, ' ')
  const selected = new Set(values.map((value) => value.toLocaleLowerCase('pt-BR')))
  const options = suggestions.filter(
    (option) => !selected.has(option.value.toLocaleLowerCase('pt-BR')),
  )
  const existing = typed ? resolve?.(typed) : undefined
  const canCreate =
    typed !== '' &&
    !existing &&
    !options.some(
      (option) => option.label.toLocaleLowerCase('pt-BR') === typed.toLocaleLowerCase('pt-BR'),
    )

  const setText = (text: string) => {
    setQuery(text)
    onQueryChange(text)
  }
  const add = (value: string) => {
    if (!selected.has(value.toLocaleLowerCase('pt-BR'))) onChange([...values, value])
    setText('')
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && typed) {
      event.preventDefault()
      add(
        existing ??
          options.find((o) => o.label.toLowerCase() === typed.toLowerCase())?.value ??
          typed,
      )
    } else if (event.key === 'Backspace' && !query && values.length) {
      onChange(values.slice(0, -1))
    }
  }

  return (
    <div className="relative">
      <label htmlFor={id} className="label">
        {label}
      </label>
      <div className="input flex flex-wrap gap-1.5" aria-invalid={Boolean(error)}>
        {values.map((value) => (
          <span key={value} className="chip">
            {renderLabel(value)}
            <button
              type="button"
              aria-label={`Remover ${renderLabel(value)}`}
              className="text-muted hover:text-danger"
              onClick={() => onChange(values.filter((item) => item !== value))}
            >
              ×
            </button>
          </span>
        ))}
        <input
          id={id}
          className="min-w-32 flex-1 bg-transparent outline-none"
          value={query}
          placeholder={values.length ? '' : placeholder}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          autoComplete="off"
        />
      </div>
      {typed && (options.length > 0 || canCreate) && (
        <ul
          role="listbox"
          className="card absolute z-10 mt-1 max-h-60 w-full overflow-auto p-1 shadow-xl"
        >
          {options.slice(0, 8).map((option) => (
            <li key={option.value}>
              <button
                type="button"
                role="option"
                aria-selected="false"
                className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-surface-2"
                onClick={() => add(option.value)}
              >
                {option.label}
              </button>
            </li>
          ))}
          {canCreate && (
            <li>
              <button
                type="button"
                role="option"
                aria-selected="false"
                className="w-full rounded-lg px-3 py-2 text-left text-sm text-accent hover:bg-surface-2"
                onClick={() => add(typed)}
              >
                + Criar “{typed}”
              </button>
            </li>
          )}
        </ul>
      )}
      {error && <p className="field-error">{error}</p>}
    </div>
  )
}
