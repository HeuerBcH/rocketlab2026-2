import { Link, NavLink, Outlet, ScrollRestoration } from 'react-router'
import { toast } from 'sonner'

import { AdminOnly, LoginLink } from '@/auth/RequireAuth'
import { useLogout, useSession } from '@/auth/useAuth'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-4 py-2 text-sm font-bold transition-colors ${
    isActive ? 'bg-accent text-bg' : 'text-muted hover:bg-surface-2 hover:text-text'
  }`

function SessionControl() {
  const { isAuthenticated, username } = useSession()
  const logout = useLogout()
  if (!isAuthenticated) {
    return (
      <LoginLink className="ml-2 rounded-full border border-border px-4 py-2 text-sm font-bold hover:border-accent">
        Entrar
      </LoginLink>
    )
  }
  return (
    <button
      className="ml-2 rounded-full border border-border px-4 py-2 text-sm font-bold hover:border-accent"
      onClick={() => {
        logout()
        toast.info('Sessão encerrada.')
      }}
      title="Sair"
    >
      {username ?? 'admin'} · Sair
    </button>
  )
}

export function Layout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 border-b border-border bg-bg/85 backdrop-blur">
        <div className="mx-auto flex min-h-16 max-w-6xl flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-3">
          <Link to="/" className="font-display text-xl font-bold">
            Rocket<span className="text-accent">Lab</span> Filmes
          </Link>
          <nav aria-label="Principal" className="flex flex-wrap items-center gap-1">
            <NavLink to="/" end className={navLinkClass}>
              Catálogo
            </NavLink>
            <AdminOnly>
              <NavLink to="/movies/new" className={navLinkClass}>
                + Novo filme
              </NavLink>
            </AdminOnly>
            <SessionControl />
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      <footer className="meta border-t border-border py-5 text-center">
        Dados: TMDB · Notas de 0 a 10
      </footer>
      <ScrollRestoration />
    </div>
  )
}
