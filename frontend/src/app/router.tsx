import type { RouteObject } from 'react-router'

import { RequireAuth } from '@/auth/RequireAuth'
import { Layout } from '@/components/Layout'
import { RouteErrorPage } from '@/pages/RouteErrorPage'
import { CatalogPage } from '@/pages/CatalogPage'
import { LoginPage } from '@/pages/LoginPage'
import { MovieDetailPage } from '@/pages/MovieDetailPage'
import { MovieFormPage } from '@/pages/MovieFormPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <CatalogPage /> },
      { path: 'login', element: <LoginPage /> },
      {
        path: 'movies/new',
        element: (
          <RequireAuth>
            <MovieFormPage mode="create" />
          </RequireAuth>
        ),
      },
      { path: 'movies/:movieId', element: <MovieDetailPage /> },
      {
        path: 'movies/:movieId/edit',
        element: (
          <RequireAuth>
            <MovieFormPage mode="edit" />
          </RequireAuth>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
