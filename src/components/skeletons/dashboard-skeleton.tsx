import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function DashboardSkeleton() {
  return (
    <div className='space-y-6'>
      {/* Header Skeleton */}
      <div className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div className='space-y-2'>
          <Skeleton className='h-8 w-64' />
          <Skeleton className='h-4 w-96' />
        </div>
        <div className='flex items-center gap-4'>
          <Skeleton className='h-4 w-32' />
          <Skeleton className='h-8 w-8 rounded-full' />
        </div>
      </div>

      {/* Metrics Cards Skeleton */}
      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
              <CardTitle className='text-sm font-medium'>
                <Skeleton className='h-4 w-24' />
              </CardTitle>
              <Skeleton className='h-8 w-8 rounded-full' />
            </CardHeader>
            <CardContent>
              <Skeleton className='mb-2 h-8 w-16' />
              <Skeleton className='mb-4 h-3 w-32' />
              <Skeleton className='h-2 w-full' />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-7'>
        {/* Recent Scans Skeleton */}
        <Card className='col-span-4'>
          <CardHeader>
            <div className='flex items-center justify-between'>
              <div>
                <CardTitle>
                  <Skeleton className='h-6 w-32' />
                </CardTitle>
                <div className='mt-1'>
                  <Skeleton className='h-4 w-48' />
                </div>
              </div>
              <Skeleton className='h-9 w-24' />
            </div>
          </CardHeader>
          <CardContent>
            <div className='space-y-4'>
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className='flex items-center justify-between space-x-4 p-3'
                >
                  <div className='flex items-center space-x-4'>
                    <Skeleton className='h-8 w-8 rounded-full' />
                    <div className='space-y-2'>
                      <Skeleton className='h-4 w-32' />
                      <Skeleton className='h-3 w-48' />
                    </div>
                  </div>
                  <Skeleton className='h-6 w-20' />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions Skeleton */}
        <Card className='col-span-3'>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Skeleton className='h-5 w-5' />
              <Skeleton className='h-6 w-32' />
            </CardTitle>
            <div className='mt-1'>
              <Skeleton className='h-4 w-48' />
            </div>
          </CardHeader>
          <CardContent className='space-y-3'>
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className='h-12 w-full' />
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
