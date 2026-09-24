import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { vi } from 'vitest'

import { routes } from '@/app/router'
import { setToken } from '@/auth/session'

/** JWT falso (a assinatura não é verificada no front), válido por 1 hora. */
export function fakeToken(): string {
  const payload = btoa(JSON.stringify({ sub: 'admin', exp: Math.floor(Date.now() / 1000) + 3600 }))
  return `header.${payload}.assinatura`
}

/** Renderiza a aplicação numa rota, com cache isolado e sem novas tentativas. */
export function renderRoute(path: string, { authenticated = false } = {}) {
  if (authenticated) setToken(fakeToken())
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { router, queryClient }
}

type Handler = (request: Request) => Response | Promise<Response>

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/**
 * Simula a API: cada chave é "MÉTODO /caminho" (sem query string).
 * Requisições sem handler falham o teste com uma mensagem clara.
 */
export function mockApi(handlers: Record<string, Handler>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const request = input instanceof Request ? input : new Request(input)
    const { pathname } = new URL(request.url)
    const key = `${request.method} ${pathname}`
    // Sessão: por padrão, qualquer token é aceito pela API simulada.
    const handler =
      handlers[key] ??
      (key === 'GET /api/v1/auth/me' ? () => json({ username: 'admin' }) : undefined)
    if (!handler) throw new Error(`Requisição não simulada: ${request.method} ${pathname}`)
    return handler(request)
  })
}
