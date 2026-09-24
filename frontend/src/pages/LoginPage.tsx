import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate, useSearchParams } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'

import { useLogin, useSession } from '@/auth/useAuth'
import { FieldError } from '@/components/ui'

const loginSchema = z.object({
  username: z.string().trim().min(1, 'Informe o usuário'),
  password: z.string().min(1, 'Informe a senha'),
})
type LoginValues = z.infer<typeof loginSchema>

/** Só aceita caminhos internos em ?next= (evita redirecionar para outro site). */
function safeNext(next: string | null): string {
  return next?.startsWith('/') && !next.startsWith('//') ? next : '/'
}

export function LoginPage() {
  const [searchParams] = useSearchParams()
  const next = safeNext(searchParams.get('next'))
  const navigate = useNavigate()
  const { isAuthenticated } = useSession()
  const login = useLogin()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  })

  if (isAuthenticated && !login.isSuccess) return <Navigate to={next} replace />

  const onSubmit = (values: LoginValues) =>
    login.mutate(values, {
      onSuccess: () => {
        toast.success('Bem-vindo, administrador.')
        navigate(next, { replace: true })
      },
    })

  return (
    <section className="mx-auto max-w-sm">
      <h1 className="mb-1 text-4xl font-bold">Entrar</h1>
      <p className="meta mb-6">Área do administrador: cadastro, edição e avaliações.</p>
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="card space-y-4 p-6">
        {login.isError && (
          <p role="alert" className="rounded-xl bg-danger/15 px-3 py-2 text-sm text-danger">
            {login.error.message}
          </p>
        )}
        <div>
          <label htmlFor="username" className="label">
            Usuário
          </label>
          <input
            id="username"
            autoComplete="username"
            className="input"
            aria-invalid={Boolean(errors.username)}
            {...register('username')}
          />
          <FieldError message={errors.username?.message} />
        </div>
        <div>
          <label htmlFor="password" className="label">
            Senha
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className="input"
            aria-invalid={Boolean(errors.password)}
            {...register('password')}
          />
          <FieldError message={errors.password?.message} />
        </div>
        <button type="submit" className="btn-primary w-full" disabled={login.isPending}>
          {login.isPending ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </section>
  )
}
