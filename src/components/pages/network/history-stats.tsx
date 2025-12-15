import { useMemo } from 'react'
import { Activity, CheckCircle, RefreshCw, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { NetworkScan } from './types'

interface HistoryStatsProps {
    scans: NetworkScan[]
}

export function HistoryStats({ scans }: HistoryStatsProps) {
    const stats = useMemo(() => {
        const total = scans.length
        const completed = scans.filter((s) => s.status === 'completed').length
        const running = scans.filter((s) => s.status === 'running').length
        const failed = scans.filter((s) => s.status === 'failed').length

        return { total, completed, running, failed }
    }, [scans])

    return (
        <div className='grid gap-4 md:grid-cols-4'>
            <Card>
                <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
                    <CardTitle className='text-sm font-medium'>Total Scans</CardTitle>
                    <Activity className='text-muted-foreground h-4 w-4' />
                </CardHeader>
                <CardContent>
                    <div className='text-2xl font-bold'>{stats.total}</div>
                    <p className='text-muted-foreground text-xs'>All time scans</p>
                </CardContent>
            </Card>
            <Card>
                <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
                    <CardTitle className='text-sm font-medium'>Completed</CardTitle>
                    <CheckCircle className='h-4 w-4 text-green-600' />
                </CardHeader>
                <CardContent>
                    <div className='text-2xl font-bold text-green-600'>
                        {stats.completed}
                    </div>
                    <p className='text-muted-foreground text-xs'>
                        Successfully completed
                    </p>
                </CardContent>
            </Card>
            <Card>
                <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
                    <CardTitle className='text-sm font-medium'>Running</CardTitle>
                    <RefreshCw className='h-4 w-4 text-blue-600' />
                </CardHeader>
                <CardContent>
                    <div className='text-2xl font-bold text-blue-600'>
                        {stats.running}
                    </div>
                    <p className='text-muted-foreground text-xs'>
                        Currently in progress
                    </p>
                </CardContent>
            </Card>
            <Card>
                <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
                    <CardTitle className='text-sm font-medium'>Failed</CardTitle>
                    <AlertTriangle className='h-4 w-4 text-red-600' />
                </CardHeader>
                <CardContent>
                    <div className='text-2xl font-bold text-red-600'>
                        {stats.failed}
                    </div>
                    <p className='text-muted-foreground text-xs'>Failed to complete</p>
                </CardContent>
            </Card>
        </div>
    )
}
