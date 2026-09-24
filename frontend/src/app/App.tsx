import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState } from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { Toaster } from 'sonner'

import { createQueryClient } from './queryClient'
import { routes } from './router'

const router = createBrowserRouter(routes)

export function App() {
  const [queryClient] = useState(createQueryClient)

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster richColors position="bottom-right" theme="dark" />
      <ReactQueryDevtools buttonPosition="bottom-left" />
    </QueryClientProvider>
  )
}
