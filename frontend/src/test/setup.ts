import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

import { clearToken } from '@/auth/session'

// Sem `globals: true`, a Testing Library não desmonta sozinha entre os testes.
afterEach(() => {
  cleanup()
  clearToken()
})
