import createClient from 'openapi-fetch'

import { clearToken, getToken } from '@/auth/session'

import type { paths } from './schema'

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

/** Caminhos do contrato OpenAPI são absolutos (/api/v1/...); a base é só a origem. */
const baseUrl = new URL(API_URL).origin

/** Cliente HTTP tipado a partir do OpenAPI do backend (src/api/schema.d.ts). */
export const api = createClient<paths>({
  baseUrl,
  // Resolve o fetch a cada chamada (e não na criação), permitindo simulá-lo nos testes.
  fetch: (input) => globalThis.fetch(input),
})

// Envia o token do administrador em toda requisição, quando houver sessão.
api.use({
  onRequest({ request }) {
    const token = getToken()
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
})

/** Erro de API normalizado para exibição na interface. */
export class ApiError extends Error {
  readonly status: number
  /** Mensagens por campo (erros 422 de validação), quando houver. */
  readonly fieldErrors: Record<string, string>

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }

  get isNotFound(): boolean {
    return this.status === 404
  }
}

interface ValidationIssue {
  loc?: (string | number)[]
  msg?: string
}

/** Converte o corpo de erro do FastAPI (`{"detail": ...}`) em um ApiError. */
export function toApiError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | undefined)?.detail

  if (typeof detail === 'string') {
    return new ApiError(status, detail)
  }
  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {}
    for (const issue of detail as ValidationIssue[]) {
      // loc vem como ["body", "campo", ...]; o primeiro nível é a origem (body/query).
      const field = issue.loc?.slice(1).join('.') || 'geral'
      fieldErrors[field] ??= (issue.msg ?? 'Valor inválido').replace(/^Value error, /, '')
    }
    return new ApiError(status, 'Verifique os campos destacados.', fieldErrors)
  }
  return new ApiError(status, defaultMessage(status))
}

function defaultMessage(status: number): string {
  if (status === 404) return 'Não encontrado.'
  if (status >= 500) return 'Erro no servidor. Tente novamente em instantes.'
  return 'Não foi possível concluir a operação.'
}

type FetchResult<T> = { data?: T; error?: unknown; response: Response }

/**
 * Executa uma chamada do cliente e devolve só os dados, lançando ApiError em falha.
 * Falhas de rede (API fora do ar) viram ApiError com status 0.
 */
export async function request<T>(call: () => Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>
  try {
    result = await call()
  } catch {
    throw new ApiError(0, 'Não foi possível conectar à API. Verifique se o backend está rodando.')
  }
  if (!result.response.ok) {
    // Token recusado (expirado/inválido): encerra a sessão para a interface pedir novo login.
    if (result.response.status === 401) clearToken()
    throw toApiError(result.response.status, result.error)
  }
  return result.data as T
}
