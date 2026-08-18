import { useEffect, useMemo, useState } from 'react'
import { Activity, Cpu, Gauge, HardDrive, MemoryStick, Wifi } from 'lucide-react'
import { apiClient, type SystemMonitorResponse } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import type { DataPoint, ResourceData } from './types'
import { ResourceCard } from './resource-card'
import { TargetConfigDialog } from './target-config-dialog'

const MAX_POINTS = 20

function emptyResourceData(): ResourceData {
    return {
        cpu: [],
        memory: [],
        disk: [],
        network: [],
        latency: [],
    }
}

function appendPoint(history: DataPoint[], incoming: DataPoint[]) {
    const point = incoming[0]
    if (!point) return history
    return [...history, point].slice(-MAX_POINTS)
}

function latestValue(history: DataPoint[]) {
    return history[history.length - 1]?.value ?? 0
}

function formatBytes(value?: number) {
    if (value == null || !Number.isFinite(value)) return '—'
    const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    let current = value
    let index = 0
    while (current >= 1024 && index < units.length - 1) {
        current /= 1024
        index += 1
    }
    return `${current.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

function formatCollectedAt(value?: string | null) {
    if (!value) return 'Not reported by source'
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function sourceLabel(snapshot: SystemMonitorResponse | null) {
    if (!snapshot) return 'No data'
    if (snapshot.source === 'local_psutil') return 'Local measured'
    if (snapshot.source === 'wazuh_syscollector') return 'Wazuh snapshot'
    return 'Agentless latency'
}

export function SystemMonitor() {
    const [resourceData, setResourceData] = useState<ResourceData>(emptyResourceData)
    const [snapshot, setSnapshot] = useState<SystemMonitorResponse | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [isExpanded, setIsExpanded] = useState(false)
    const [targetSystem, setTargetSystem] = useState(
        () => localStorage.getItem('cloudx-monitor-target') || 'localhost'
    )
    const [tempTarget, setTempTarget] = useState(targetSystem)
    const [isDialogOpen, setIsDialogOpen] = useState(false)

    const handleSaveTarget = () => {
        const normalized = tempTarget.trim() || 'localhost'
        setTargetSystem(normalized)
        setTempTarget(normalized)
        localStorage.setItem('cloudx-monitor-target', normalized)
        setIsDialogOpen(false)
    }

    useEffect(() => {
        let cancelled = false
        setResourceData(emptyResourceData())
        setSnapshot(null)
        setError(null)

        const fetchData = async () => {
            try {
                const response = await apiClient.getSystemMonitor(targetSystem)
                if (cancelled) return

                setSnapshot(response)
                setError(null)
                setResourceData((previous) => ({
                    cpu: appendPoint(previous.cpu, response.cpu),
                    memory: appendPoint(previous.memory, response.memory),
                    disk: appendPoint(previous.disk, response.disk),
                    network: appendPoint(previous.network, response.network),
                    latency: appendPoint(previous.latency, response.latency),
                }))
            } catch (fetchError) {
                if (cancelled) return
                setError(
                    fetchError instanceof Error
                        ? fetchError.message
                        : 'Unable to load monitoring metrics'
                )
            }
        }

        void fetchData()
        const interval = window.setInterval(() => void fetchData(), 5000)
        return () => {
            cancelled = true
            window.clearInterval(interval)
        }
    }, [targetSystem])

    const availableCards = useMemo(() => {
        if (!snapshot) return []
        const cards = []
        if (snapshot.availability.cpu) {
            cards.push(
                <ResourceCard
                    key='cpu'
                    icon={Cpu}
                    label='CPU'
                    value={latestValue(resourceData.cpu)}
                    data={resourceData.cpu}
                    color='#3b82f6'
                />
            )
        }
        if (snapshot.availability.memory) {
            cards.push(
                <ResourceCard
                    key='memory'
                    icon={MemoryStick}
                    label='Memory'
                    value={latestValue(resourceData.memory)}
                    data={resourceData.memory}
                    color='#ef4444'
                />
            )
        }
        if (snapshot.availability.disk) {
            cards.push(
                <ResourceCard
                    key='disk'
                    icon={HardDrive}
                    label='Disk'
                    value={latestValue(resourceData.disk)}
                    data={resourceData.disk}
                    color='#f59e0b'
                />
            )
        }
        if (snapshot.availability.network_throughput) {
            cards.push(
                <ResourceCard
                    key='network'
                    icon={Wifi}
                    label='Network'
                    value={latestValue(resourceData.network)}
                    data={resourceData.network}
                    color='#8b5cf6'
                    unit={snapshot.network_unit || 'MiB/s'}
                />
            )
        }
        if (snapshot.availability.latency) {
            cards.push(
                <ResourceCard
                    key='latency'
                    icon={Gauge}
                    label='Latency'
                    value={latestValue(resourceData.latency)}
                    data={resourceData.latency}
                    color='#0ea5e9'
                    unit='ms'
                />
            )
        }
        return cards
    }, [resourceData, snapshot])

    const hasAnySpikes = Object.values(resourceData)
        .flat()
        .some((point) => point.isSpike)

    const unavailable = snapshot
        ? [
              ['CPU', snapshot.availability.cpu],
              ['Memory', snapshot.availability.memory],
              ['Disk', snapshot.availability.disk],
              ['Network throughput', snapshot.availability.network_throughput],
              ['Latency', snapshot.availability.latency],
              ['GPU', snapshot.availability.gpu],
              ['VRAM', snapshot.availability.vram],
          ]
              .filter(([, available]) => !available)
              .map(([name]) => name)
        : []

    return (
        <Card className='transition-all duration-300 hover:shadow-lg'>
            <div className='p-4'>
                <div className='mb-4 flex flex-wrap items-center justify-between gap-3'>
                    <div className='flex items-center gap-3'>
                        <button
                            type='button'
                            className='flex items-center gap-2 text-left'
                            onClick={() => setIsExpanded((value) => !value)}
                        >
                            <img
                                src='/cloud-x logo.png'
                                alt='Cloud-X Logo'
                                className='h-6 w-6 object-contain'
                            />
                            <div className='flex flex-col'>
                                <span className='text-lg leading-none font-semibold'>
                                    Cloud-X System Monitor
                                </span>
                                <span className='text-muted-foreground mt-1 font-mono text-xs'>
                                    Target: {targetSystem}
                                </span>
                            </div>
                        </button>

                        <TargetConfigDialog
                            targetSystem={targetSystem}
                            tempTarget={tempTarget}
                            isOpen={isDialogOpen}
                            onOpenChange={setIsDialogOpen}
                            onTempTargetChange={setTempTarget}
                            onSave={handleSaveTarget}
                        />
                    </div>

                    <div className='flex items-center gap-2'>
                        <Badge variant={snapshot?.is_agentless ? 'secondary' : 'default'}>
                            {sourceLabel(snapshot)}
                        </Badge>
                        {hasAnySpikes && (
                            <Badge variant='destructive'>
                                <Activity className='mr-1 h-3 w-3' />
                                High usage
                            </Badge>
                        )}
                    </div>
                </div>

                {error ? (
                    <div className='border-destructive/40 bg-destructive/5 text-destructive rounded-md border p-3 text-sm'>
                        {error}
                    </div>
                ) : availableCards.length > 0 ? (
                    <div className='grid grid-cols-1 gap-1.5 sm:grid-cols-2'>
                        {availableCards}
                    </div>
                ) : (
                    <div className='text-muted-foreground rounded-md border p-3 text-sm'>
                        {snapshot
                            ? 'The selected source has no live utilization metric available.'
                            : 'Loading measured metrics…'}
                    </div>
                )}

                {isExpanded && snapshot && (
                    <div className='mt-4 space-y-3 border-t pt-4 text-sm'>
                        <div className='grid gap-3 sm:grid-cols-2'>
                            <div>
                                <div className='text-muted-foreground text-xs'>Metric source</div>
                                <div className='font-medium'>{sourceLabel(snapshot)}</div>
                            </div>
                            <div>
                                <div className='text-muted-foreground text-xs'>Collected</div>
                                <div className='font-medium'>
                                    {formatCollectedAt(snapshot.collected_at)}
                                </div>
                            </div>
                        </div>

                        {snapshot.agent && (
                            <div className='rounded-md border p-3'>
                                <div className='font-medium'>Managed Wazuh endpoint</div>
                                <div className='text-muted-foreground mt-1 text-xs'>
                                    {snapshot.agent.name || snapshot.agent.id} · ID {snapshot.agent.id}
                                    {snapshot.agent.ip ? ` · ${snapshot.agent.ip}` : ''}
                                    {snapshot.agent.status ? ` · ${snapshot.agent.status}` : ''}
                                </div>
                            </div>
                        )}

                        {snapshot.source === 'local_psutil' && (
                            <div className='grid gap-3 sm:grid-cols-2'>
                                <div>
                                    <div className='text-muted-foreground text-xs'>Receive</div>
                                    <div className='font-medium'>
                                        {(snapshot.network_rx_mbps ?? 0).toFixed(3)} MiB/s
                                    </div>
                                </div>
                                <div>
                                    <div className='text-muted-foreground text-xs'>Transmit</div>
                                    <div className='font-medium'>
                                        {(snapshot.network_tx_mbps ?? 0).toFixed(3)} MiB/s
                                    </div>
                                </div>
                            </div>
                        )}

                        {snapshot.network_counters && (
                            <div className='grid gap-3 sm:grid-cols-2'>
                                <div>
                                    <div className='text-muted-foreground text-xs'>Interface RX snapshot</div>
                                    <div className='font-medium'>
                                        {formatBytes(snapshot.network_counters.rx_bytes)}
                                    </div>
                                </div>
                                <div>
                                    <div className='text-muted-foreground text-xs'>Interface TX snapshot</div>
                                    <div className='font-medium'>
                                        {formatBytes(snapshot.network_counters.tx_bytes)}
                                    </div>
                                </div>
                            </div>
                        )}

                        {snapshot.hardware?.cpu_name && (
                            <div className='rounded-md border p-3'>
                                <div className='font-medium'>{snapshot.hardware.cpu_name}</div>
                                <div className='text-muted-foreground mt-1 text-xs'>
                                    {snapshot.hardware.cpu_cores ?? '—'} cores ·{' '}
                                    {snapshot.hardware.cpu_mhz ?? '—'} MHz inventory snapshot
                                </div>
                            </div>
                        )}

                        {unavailable.length > 0 && (
                            <div className='text-muted-foreground text-xs'>
                                Not available from this source: {unavailable.join(', ')}.
                            </div>
                        )}

                        <p className='text-muted-foreground text-xs'>{snapshot.note}</p>
                    </div>
                )}

                <button
                    type='button'
                    onClick={() => setIsExpanded((value) => !value)}
                    className='text-muted-foreground mt-3 w-full text-center text-xs'
                >
                    {isExpanded ? 'Hide metric provenance' : 'Show metric provenance'}
                </button>
            </div>
        </Card>
    )
}

export default SystemMonitor
