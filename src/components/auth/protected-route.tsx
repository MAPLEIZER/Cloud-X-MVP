import type { ReactNode } from 'react'
import { Navigate } from '@tanstack/react-router'
import { useAuth } from '@clerk/clerk-react'

interface ProtectedRouteProps {
  children: ReactNode
  _fallback?: ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isSignedIn, isLoaded } = useAuth()

  // Show loading state while Clerk is initializing
  if (!isLoaded) {
    return (
      <div className='flex min-h-screen items-center justify-center'>
        <div className='h-8 w-8 animate-spin rounded-full border-b-2 border-gray-900'></div>
      </div>
    )
  }

  // Redirect to sign-in if not authenticated
  if (!isSignedIn) {
    return <Navigate to='/sign-in' search={{ redirect: location.pathname }} />
  }

  return <>{children}</>
}
