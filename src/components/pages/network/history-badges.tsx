import { format } from 'date-fns'
import { CheckCircle, RefreshCw, AlertTriangle, Clock, Network } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { NetworkScan } from './types'

// Date Badge Component
export function DateBadge({ date: rawDate }: { date: string | Date }) {
    const date = new Date(rawDate)
    const day = format(date, 'd')
    const month = format(date, 'LLL')

    return (
        <div className='bg-background/40 flex size-10 shrink-0 cursor-default flex-col items-center justify-center rounded-md border text-center'>
            <span className='text-sm leading-snug font-semibold'>{day}</span>
            <span className='text-muted-foreground text-xs leading-none'>
                {month}
            </span>
        </div>
    )
}

// Status Badge Component
export function StatusBadge({ status }: { status: NetworkScan['status'] }) {
    const statusConfig = {
        completed: {
            variant: 'default' as const,
            icon: CheckCircle,
            text: 'Completed',
            className: 'bg-green-100 text-green-800 border-green-200',
        },
        running: {
            variant: 'default' as const,
            icon: RefreshCw,
            text: 'Running',
            className: 'bg-blue-100 text-blue-800 border-blue-200',
        },
        failed: {
            variant: 'destructive' as const,
            icon: AlertTriangle,
            text: 'Failed',
            className: 'bg-red-100 text-red-800 border-red-200',
        },
        submitted: {
            variant: 'secondary' as const,
            icon: Clock,
            text: 'Submitted',
            className: 'bg-yellow-100 text-yellow-800 border-yellow-200',
        },
        stopped: {
            variant: 'secondary' as const,
            icon: AlertTriangle,
            text: 'Stopped',
            className: 'bg-gray-100 text-gray-800 border-gray-200',
        },
    }

    const config = statusConfig[status] || statusConfig.submitted
    const Icon = config.icon

    return (
        <Badge className={`flex items-center gap-1 ${config.className}`}>
            <Icon size={12} className={status === 'running' ? 'animate-spin' : ''} />
            {config.text}
        </Badge>
    )
}

// Tool Badge Component
export function ToolBadge({ tool }: { tool: string }) {
    const toolConfig = {
        nmap: {
            color: 'bg-purple-100 text-purple-800 border-purple-200',
            text: 'NMAP',
        },
        zmap: {
            color: 'bg-indigo-100 text-indigo-800 border-indigo-200',
            text: 'ZMAP',
        },
        masscan: {
            color: 'bg-orange-100 text-orange-800 border-orange-200',
            text: 'MASSCAN',
        },
    }

    const config = toolConfig[tool as keyof typeof toolConfig] || {
        color: 'bg-gray-100 text-gray-800 border-gray-200',
        text: tool.toUpperCase(),
    }

    return (
        <Badge className={`flex items-center gap-1 ${config.color}`}>
            <Network size={12} />
            {config.text}
        </Badge>
    )
}
