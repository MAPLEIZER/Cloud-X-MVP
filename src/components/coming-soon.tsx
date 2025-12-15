import { Telescope } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function ComingSoon() {
  return (
    <div className='flex h-[calc(100vh-4rem)] flex-col items-center justify-center p-4 text-center'>
      <div className='flex flex-col items-center justify-center space-y-6'>
        <div className='bg-primary/10 ring-primary/20 rounded-full p-8 ring-1'>
          <Telescope size={64} className='text-primary' />
        </div>
        <div className='space-y-2'>
          <h1 className='from-primary to-primary/60 bg-gradient-to-r bg-clip-text text-4xl font-bold tracking-tight text-transparent lg:text-5xl'>
            Coming Soon
          </h1>
          <p className='text-muted-foreground max-w-[600px] md:text-xl'>
            We are working hard to bring you this feature.{' '}
            <br className='hidden sm:inline' />
            Stay tuned for updates!
          </p>
        </div>
        <div className='flex gap-4'>
          <Button variant='outline' onClick={() => window.history.back()}>
            Go Back
          </Button>
          <Button disabled>Notify Me</Button>
        </div>
      </div>
    </div>
  )
}
