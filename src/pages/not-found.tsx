import { useNavigate } from '@tanstack/react-router'
import { AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function NotFound() {
  const navigate = useNavigate()

  return (
    <div className='bg-background flex h-screen w-full flex-col items-center justify-center p-4 text-center'>
      <div className='flex flex-col items-center justify-center space-y-4'>
        <div className='bg-muted rounded-full p-8'>
          <AlertCircle className='text-muted-foreground h-16 w-16' />
        </div>
        <h1 className='text-4xl font-bold tracking-tight lg:text-5xl'>404</h1>
        <h2 className='text-2xl font-semibold tracking-tight'>
          Page not found
        </h2>
        <p className='text-muted-foreground max-w-[500px]'>
          The page you are looking for doesn't exist or has been moved.
        </p>
        <div className='flex gap-4 pt-4'>
          <Button variant='default' onClick={() => navigate({ to: '/' })}>
            Go to Dashboard
          </Button>
          <Button variant='outline' onClick={() => window.history.back()}>
            Go Back
          </Button>
        </div>
      </div>
    </div>
  )
}
