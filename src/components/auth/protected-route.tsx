import { useAuth } from '@clerk/clerk-react';
import { Navigate } from '@tanstack/react-router';
import type { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
  _fallback?: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isSignedIn, isLoaded } = useAuth();

  // Show loading state while Clerk is initializing
  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  // Redirect to sign-in if not authenticated
  if (!isSignedIn) {
    return <Navigate to="/sign-in" search={{ redirect: location.pathname }} />;
  }

  return <>{children}</>;
}
