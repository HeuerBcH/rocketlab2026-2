import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '@/api/client'

const MAX_RETRIES = 2

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Dados considerados frescos por 30s: navegar entre páginas já visitadas é instantâneo.
        staleTime: 30 * 1000,
        refetchOnWindowFocus: false,
        // Erros do cliente (404, 422) não mudam ao tentar de novo; só rede/servidor são repetidos.
        retry: (failureCount, error) =>
          !(error instanceof ApiError && error.status >= 400 && error.status < 500) &&
          failureCount < MAX_RETRIES,
      },
    },
  })
}
