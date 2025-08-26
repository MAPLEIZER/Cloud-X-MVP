import { SignIn, SignUp } from '@clerk/clerk-react';

interface AuthLayoutProps {
  mode: 'sign-in' | 'sign-up';
}

export function AuthLayout({ mode }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-md">
        {mode === 'sign-in' ? (
          <SignIn 
            path="/sign-in"
            routing="path"
            signUpUrl="/sign-up"
            appearance={{
              elements: {
                rootBox: "w-full",
                card: "shadow-lg border-0"
              }
            }}
          />
        ) : (
          <SignUp 
            path="/sign-up"
            routing="path"
            signInUrl="/sign-in"
            appearance={{
              elements: {
                rootBox: "w-full",
                card: "shadow-lg border-0"
              }
            }}
          />
        )}
      </div>
    </div>
  );
}
