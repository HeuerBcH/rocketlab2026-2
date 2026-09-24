/**
 * Sessão do administrador: guarda o JWT no localStorage e avisa os inscritos
 * quando ele muda (login, logout ou expiração). Integra com React via
 * useSyncExternalStore (ver useSession).
 */

const STORAGE_KEY = 'rocketlab.token'
const listeners = new Set<() => void>()

let token: string | null = readStoredToken()

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null // modo privado / storage bloqueado: sessão só em memória
  }
}

/** Lê o `exp` (segundos) do JWT sem validar a assinatura — só para a interface. */
function expiresAt(jwt: string): number | null {
  try {
    const payload = jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const exp = (JSON.parse(atob(payload)) as { exp?: unknown }).exp
    return typeof exp === 'number' ? exp * 1000 : null
  } catch {
    return null
  }
}

function notify() {
  for (const listener of listeners) listener()
}

/**
 * Token atual, ou null se ausente/expirado (quem valida de fato é a API).
 * Sem efeitos colaterais: é chamada pelo React durante a renderização.
 */
export function getToken(): string | null {
  if (!token) return null
  const exp = expiresAt(token)
  return exp !== null && exp > Date.now() ? token : null
}

export function setToken(value: string): void {
  token = value
  try {
    localStorage.setItem(STORAGE_KEY, value)
  } catch {
    /* sessão só em memória */
  }
  notify()
}

export function clearToken(): void {
  if (token === null) return
  token = null
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* nada a limpar */
  }
  notify()
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
