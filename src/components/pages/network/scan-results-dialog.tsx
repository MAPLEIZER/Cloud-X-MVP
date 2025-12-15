import { useState } from 'react'
import {
    Network,
    Target,
    Settings,
    Clock,
    Server,
    Code,
    ChevronDown,
    ChevronUp,
    Download,
    AlertTriangle,
    CheckCircle,
    Shield,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import type { NetworkScan, HostInfo, PortInfo } from './types'
import {
    parseScanResults,
    formatScanResults,
    formatRelativeDate,
    downloadScanResults,
} from './history-utils'

interface ScanResultsDialogProps {
    scan: NetworkScan | null
    isOpen: boolean
    onOpenChange: (open: boolean) => void
}

export function ScanResultsDialog({
    scan,
    isOpen,
    onOpenChange,
}: ScanResultsDialogProps) {
    const [showRawJson, setShowRawJson] = useState(false)

    if (!scan) return null

    const parsedData = parseScanResults(scan.results)

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className='flex max-h-[95vh] w-[95vw] max-w-[95vw] flex-col overflow-y-auto sm:max-w-[95vw]'>
                <DialogHeader>
                    <DialogTitle className='flex items-center gap-2'>
                        <Network className='h-5 w-5' />
                        Scan Results - {scan.job_id}
                    </DialogTitle>
                    <DialogDescription>
                        Detailed results for {scan.tool?.toUpperCase()} scan of{' '}
                        {scan.target}
                    </DialogDescription>
                </DialogHeader>

                <ScrollArea className='flex-1 pr-6'>
                    <div className='flex justify-center'>
                        <div className='w-full max-w-7xl'>
                            <div className='space-y-4 pb-4'>
                                {/* Scan Info */}
                                <div className='bg-muted/50 grid grid-cols-1 gap-4 rounded-lg p-4 sm:grid-cols-2 lg:grid-cols-4'>
                                    <div className='min-w-0 space-y-1'>
                                        <div className='flex items-center gap-2 text-sm font-medium'>
                                            <Target className='h-4 w-4 flex-shrink-0' />
                                            Target
                                        </div>
                                        <p className='text-muted-foreground text-sm break-words'>
                                            {scan.target}
                                        </p>
                                    </div>
                                    <div className='min-w-0 space-y-1'>
                                        <div className='flex items-center gap-2 text-sm font-medium'>
                                            <Settings className='h-4 w-4 flex-shrink-0' />
                                            Tool
                                        </div>
                                        <p className='text-muted-foreground text-sm break-words'>
                                            {scan.tool?.toUpperCase()}
                                        </p>
                                    </div>
                                    <div className='min-w-0 space-y-1'>
                                        <div className='flex items-center gap-2 text-sm font-medium'>
                                            <Network className='h-4 w-4 flex-shrink-0' />
                                            Scan Type
                                        </div>
                                        <p className='text-muted-foreground text-sm break-words'>
                                            {scan.scan_type}
                                        </p>
                                    </div>
                                    <div className='min-w-0 space-y-1'>
                                        <div className='flex items-center gap-2 text-sm font-medium'>
                                            <Clock className='h-4 w-4 flex-shrink-0' />
                                            Started
                                        </div>
                                        <p className='text-muted-foreground text-sm break-words'>
                                            {formatRelativeDate(scan.created_at)}
                                        </p>
                                    </div>
                                </div>

                                <Separator />

                                {parsedData ? (
                                    <div className='space-y-6'>
                                        {/* Summary Cards */}
                                        <div className='grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4'>
                                            <Card className='min-w-0 flex-1 p-4'>
                                                <div className='flex min-w-0 items-center gap-3'>
                                                    <Server className='h-5 w-5 flex-shrink-0 text-blue-600' />
                                                    <div className='min-w-0 flex-1'>
                                                        <p className='text-2xl font-bold break-words'>
                                                            {parsedData.summary.totalHosts}
                                                        </p>
                                                        <p className='text-muted-foreground text-sm break-words'>
                                                            Total Hosts
                                                        </p>
                                                    </div>
                                                </div>
                                            </Card>
                                            <Card className='min-w-0 flex-1 p-4'>
                                                <div className='flex min-w-0 items-center gap-3'>
                                                    <CheckCircle className='h-5 w-5 flex-shrink-0 text-green-600' />
                                                    <div className='min-w-0 flex-1'>
                                                        <p className='text-2xl font-bold break-words text-green-600'>
                                                            {parsedData.summary.hostsUp}
                                                        </p>
                                                        <p className='text-muted-foreground text-sm break-words'>
                                                            Hosts Up
                                                        </p>
                                                    </div>
                                                </div>
                                            </Card>
                                            <Card className='min-w-0 flex-1 p-4'>
                                                <div className='flex min-w-0 items-center gap-3'>
                                                    <AlertTriangle className='h-5 w-5 flex-shrink-0 text-red-600' />
                                                    <div className='min-w-0 flex-1'>
                                                        <p className='text-2xl font-bold break-words text-red-600'>
                                                            {parsedData.summary.hostsDown}
                                                        </p>
                                                        <p className='text-muted-foreground text-sm break-words'>
                                                            Hosts Down
                                                        </p>
                                                    </div>
                                                </div>
                                            </Card>
                                            <Card className='min-w-0 flex-1 p-4'>
                                                <div className='flex min-w-0 items-center gap-3'>
                                                    <Shield className='h-5 w-5 flex-shrink-0 text-purple-600' />
                                                    <div className='min-w-0 flex-1'>
                                                        <p className='text-2xl font-bold break-words'>
                                                            {parsedData.summary.totalPorts}
                                                        </p>
                                                        <p className='text-muted-foreground text-sm break-words'>
                                                            Total Ports
                                                        </p>
                                                    </div>
                                                </div>
                                            </Card>
                                        </div>

                                        {/* Host Details */}
                                        <div className='space-y-4'>
                                            <h4 className='text-lg font-semibold'>Host Details</h4>
                                            {parsedData.hosts.map(
                                                (host: HostInfo, index: number) => (
                                                    <HostCard key={index} host={host} />
                                                )
                                            )}
                                        </div>
                                    </div>
                                ) : (
                                    <div className='py-8 text-center'>
                                        <AlertTriangle className='text-muted-foreground mx-auto mb-4 h-12 w-12' />
                                        <p className='text-muted-foreground'>
                                            Unable to parse scan results
                                        </p>
                                    </div>
                                )}

                                {/* Raw JSON View */}
                                {showRawJson && (
                                    <div className='space-y-2'>
                                        <h4 className='flex items-center gap-2 text-sm font-medium'>
                                            <Code className='h-4 w-4' />
                                            Raw JSON Data
                                        </h4>
                                        <div className='h-[60vh] w-full overflow-auto rounded-md border'>
                                            <ScrollArea className='h-full w-full'>
                                                <pre className='overflow-wrap-anywhere p-4 font-mono text-xs break-words whitespace-pre-wrap'>
                                                    {formatScanResults(scan.results)}
                                                </pre>
                                            </ScrollArea>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </ScrollArea>

                {/* Fixed Footer */}
                <div className='bg-background flex items-center justify-between border-t pt-4'>
                    <Button
                        variant='outline'
                        onClick={() => setShowRawJson(!showRawJson)}
                        className='flex items-center gap-2'
                    >
                        <Code className='h-4 w-4' />
                        {showRawJson ? 'Hide' : 'Show'} Raw JSON
                        {showRawJson ? (
                            <ChevronUp className='h-4 w-4' />
                        ) : (
                            <ChevronDown className='h-4 w-4' />
                        )}
                    </Button>

                    <div className='flex gap-2'>
                        <Button
                            variant='outline'
                            onClick={() => downloadScanResults(scan)}
                            disabled={!scan.results}
                        >
                            <Download className='mr-2 h-4 w-4' />
                            Download Results
                        </Button>
                        <Button variant='outline' onClick={() => onOpenChange(false)}>
                            Close
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    )
}

// Host Card sub-component
function HostCard({ host }: { host: HostInfo }) {
    return (
        <Card className='p-4'>
            <div className='space-y-4'>
                <div className='flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between'>
                    <div className='flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center'>
                        <div className='flex min-w-0 items-center gap-2'>
                            <Server className='h-4 w-4 flex-shrink-0' />
                            <span className='font-medium break-words'>{host.ip}</span>
                        </div>
                        <div className='flex flex-wrap gap-2'>
                            {host.hostnames !== 'No hostname' && (
                                <Badge variant='outline' className='break-words'>
                                    {host.hostnames}
                                </Badge>
                            )}
                            <Badge
                                className={
                                    host.status === 'up'
                                        ? 'bg-green-100 text-green-800'
                                        : 'bg-red-100 text-red-800'
                                }
                            >
                                {host.status.toUpperCase()}
                            </Badge>
                        </div>
                    </div>
                    {host.os !== 'Unknown' && (
                        <Badge variant='secondary' className='flex-shrink-0 break-words'>
                            {host.os}
                        </Badge>
                    )}
                </div>

                {host.openPorts.length > 0 && (
                    <div className='space-y-2'>
                        <h5 className='flex items-center gap-2 font-medium text-green-600'>
                            <CheckCircle className='h-4 w-4' />
                            Open Ports ({host.openPorts.length})
                        </h5>
                        <div className='grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'>
                            {host.openPorts.map((port: PortInfo, portIndex: number) => (
                                <PortCard key={portIndex} port={port} type='open' />
                            ))}
                        </div>
                    </div>
                )}

                {host.filteredPorts.length > 0 && (
                    <div className='space-y-2'>
                        <h5 className='flex items-center gap-2 font-medium text-yellow-600'>
                            <Shield className='h-4 w-4' />
                            Filtered Ports ({host.filteredPorts.length})
                        </h5>
                        <div className='flex flex-wrap gap-2'>
                            {host.filteredPorts.slice(0, 10).map(
                                (port: PortInfo, portIndex: number) => (
                                    <Badge key={portIndex} className='bg-yellow-100 text-yellow-800'>
                                        {port.portid}/{port.protocol}
                                    </Badge>
                                )
                            )}
                            {host.filteredPorts.length > 10 && (
                                <Badge variant='outline'>
                                    +{host.filteredPorts.length - 10} more
                                </Badge>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </Card>
    )
}

// Port Card sub-component
function PortCard({ port, type }: { port: PortInfo; type: 'open' | 'filtered' }) {
    const colorClass =
        type === 'open'
            ? 'border-green-200 bg-green-50'
            : 'border-yellow-200 bg-yellow-50'
    const textClass = type === 'open' ? 'text-green-800' : 'text-yellow-800'
    const textMutedClass = type === 'open' ? 'text-green-700' : 'text-yellow-700'

    return (
        <div className={`min-w-0 rounded-lg border p-3 ${colorClass}`}>
            <div className='mb-2 flex items-center justify-between gap-2'>
                <span className={`font-medium break-words ${textClass}`}>
                    {port.portid}/{port.protocol}
                </span>
                <Badge className={`flex-shrink-0 text-xs ${type === 'open' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                    {port.state?.state || type}
                </Badge>
            </div>
            {port.service && (
                <div className={`space-y-1 text-sm ${textMutedClass}`}>
                    <p className='break-words'>
                        <strong>Service:</strong> {port.service.name || 'Unknown'}
                    </p>
                    {port.service.product && (
                        <p className='break-words'>
                            <strong>Product:</strong> {port.service.product}
                        </p>
                    )}
                    {port.service.version && (
                        <p className='break-words'>
                            <strong>Version:</strong> {port.service.version}
                        </p>
                    )}
                </div>
            )}
        </div>
    )
}
