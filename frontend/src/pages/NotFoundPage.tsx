import { Link } from 'react-router'

import { StatusMessage } from '@/components/StatusMessage'

export function NotFoundPage() {
  return (
    <StatusMessage
      title="Página não encontrada"
      description="O endereço acessado não existe."
      action={
        <Link to="/" className="text-accent hover:underline">
          Voltar ao catálogo
        </Link>
      }
    />
  )
}
