import { Link, useRouteError } from 'react-router'

import { StatusMessage } from '@/components/StatusMessage'

/** Rede de segurança para erros inesperados de renderização em qualquer rota. */
export function RouteErrorPage() {
  const error = useRouteError()
  const message = error instanceof Error ? error.message : 'Erro inesperado.'

  return (
    <div className="min-h-dvh bg-bg text-text">
      <StatusMessage
        tone="error"
        title="Algo deu errado"
        description={message}
        action={
          <Link to="/" className="text-accent hover:underline">
            Voltar ao catálogo
          </Link>
        }
      />
    </div>
  )
}
