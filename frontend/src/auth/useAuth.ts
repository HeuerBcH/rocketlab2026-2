import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSyncExternalStore } from 'react'

import { api, request } from '@/api/client'

import { clearToken, getToken, setToken, subscribe } from './session'

/** Estado da sessão, reativo a login/logout/expiração. */
export function useSession() {
  const token = useSyncExternalStore(subscribe, getToken)
  const me = useQuery({
    queryKey: ['auth', 'me', token],
    // Confirma o token com a API; um 401 aqui encerra a sessão (ver request()).
    queryFn: ({ signal }) => request(() => api.GET('/api/v1/auth/me', { signal })),
    enabled: token !== null,
    staleTime: Infinity,
  })
  return { isAuthenticated: token !== null, username: me.data?.username }
}

export function useLogin() {
  return useMutation({
    mutationFn: async (credentials: { username: string; password: string }) => {
      const data = await request(() =>
        api.POST('/api/v1/auth/token', {
          body: {
            ...credentials,
            grant_type: null,
            scope: '',
            client_id: null,
            client_secret: null,
          },
          // O endpoint OAuth2 recebe formulário (x-www-form-urlencoded), não JSON.
          bodySerializer: () => new URLSearchParams(credentials),
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        }),
      )
      setToken(data.access_token)
      return data
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return () => {
    clearToken()
    queryClient.removeQueries({ queryKey: ['auth'] })
  }
}
