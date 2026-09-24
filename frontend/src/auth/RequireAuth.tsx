import type { ReactNode } from 'react'
import { Link, Navigate, useLocation } from 'react-router'

import { useSession } from './useAuth'

function loginPath(pathname: string) {
  return `/login?next=${encodeURIComponent(pathname)}`
}

/** Protege uma rota: sem sessão, redireciona ao login e volta depois. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useSession()
  const location = useLocation()
  if (!isAuthenticated) return <Navigate to={loginPath(location.pathname)} replace />
  return children
}

/** Mostra o conteúdo só para o administrador; aos demais, `fallback` (opcional). */
export function AdminOnly({
  children,
  fallback = null,
}: {
  children: ReactNode
  fallback?: ReactNode
}) {
  const { isAuthenticated } = useSession()
  return isAuthenticated ? children : fallback
}

/** Link para o login que retorna à página atual. */
export function LoginLink({ children, className }: { children: ReactNode; className?: string }) {
  const location = useLocation()
  return (
    <Link to={loginPath(location.pathname + location.search)} className={className}>
      {children}
    </Link>
  )
}
