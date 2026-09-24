import { useEffect, useState } from 'react'

/** Valor que só atualiza após `delay` ms sem mudanças (busca sem requisição por tecla). */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(id)
  }, [value, delay])
  return debounced
}
