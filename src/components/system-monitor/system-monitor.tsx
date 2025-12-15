import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Cpu, HardDrive, Wifi, Zap, Activity } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import type { DataPoint, ResourceData, Agent } from './types'
import { generateDataPoint, generateInitialData } from './types'
import { ResourceCard } from './resource-card'
import { AgentMemoryCard } from './agent-memory-card'
import { TargetConfigDialog } from './target-config-dialog'

const DEFAULT_AGENTS: Agent[] = [
    {
        id: '1',
        name: 'Network Scanner',
        memory: generateInitialData(15, 150, 50),
        color: '#3b82f6',
    },
    {
        id: '2',
        name: 'Wazuh Agent',
        memory: generateInitialData(15, 200, 50),
        color: '#10b981',
    },
    {
        id: '3',
        name: 'Security Monitor',
        memory: generateInitialData(15, 80, 50),
        color: '#f59e0b',
    },
    {
        id: '4',
        name: 'Threat Detection',
        memory: generateInitialData(15, 120, 50),
        color: '#8b5cf6',
    },
]

export function SystemMonitor() {
    const [resourceData, setResourceData] = useState<ResourceData>({
        cpu: generateInitialData(20, 45, 30),
        gpu: generateInitialData(20, 35, 25),
        vram: generateInitialData(20, 60, 20),
        network: generateInitialData(20, 25, 40),
        memory: generateInitialData(20, 70, 15),
    })

    const [agents] = useState<Agent[]>(DEFAULT_AGENTS)
    const [isExpanded, setIsExpanded] = useState(false)
    const [targetSystem, setTargetSystem] = useState(
        () => localStorage.getItem('cloudx-monitor-target') || '192.168.1.100'
    )
    const [tempTarget, setTempTarget] = useState(targetSystem)
    const [isDialogOpen, setIsDialogOpen] = useState(false)

    const handleSaveTarget = () => {
        setTargetSystem(tempTarget)
        localStorage.setItem('cloudx-monitor-target', tempTarget)
        setIsDialogOpen(false)
    }

    useEffect(() => {
        const fetchData = async () => {
            try {
                const target = targetSystem || 'localhost'
                const response = await fetch(
                    `${import.meta.env.VITE_API_BASE_URL}/api/system-monitor?target=${target}`
                )
                if (!response.ok) throw new Error('Failed to fetch metrics')

                const newData = await response.json()

                setResourceData((prev) => {
                    const maxPoints = 20

                    const append = (arr: DataPoint[], val: DataPoint | DataPoint[]) => {
                        const point = Array.isArray(val) ? val[0] : val
                        return [...arr, point].slice(-maxPoints)
                    }

                    if (newData.is_agentless) {
                        return {
                            cpu: [
                                ...prev.cpu,
                                generateDataPoint(
                                    prev.cpu[prev.cpu.length - 1]?.value || 45,
                                    5,
                                    0.01
                                ),
                            ].slice(-maxPoints),
                            gpu: [
                                ...prev.gpu,
                                generateDataPoint(
                                    prev.gpu[prev.gpu.length - 1]?.value || 35,
                                    5,
                                    0.01
                                ),
                            ].slice(-maxPoints),
                            vram: [
                                ...prev.vram,
                                generateDataPoint(
                                    prev.vram[prev.vram.length - 1]?.value || 60,
                                    5,
                                    0.01
                                ),
                            ].slice(-maxPoints),
                            network: append(prev.network, newData.network),
                            memory: [
                                ...prev.memory,
                                generateDataPoint(
                                    prev.memory[prev.memory.length - 1]?.value || 70,
                                    5,
                                    0.01
                                ),
                            ].slice(-maxPoints),
                        }
                    } else {
                        return {
                            cpu: append(prev.cpu, newData.cpu),
                            memory: append(prev.memory, newData.memory),
                            gpu: [...prev.gpu, generateDataPoint(35, 25, 0.06)].slice(
                                -maxPoints
                            ),
                            vram: [...prev.vram, generateDataPoint(60, 20, 0.05)].slice(
                                -maxPoints
                            ),
                            network: [...prev.network, generateDataPoint(25, 40, 0.1)].slice(
                                -maxPoints
                            ),
                        }
                    }
                })
            } catch {
                // Silently fail - monitor API may not be available
            }
        }

        const interval = setInterval(fetchData, 2000)
        return () => clearInterval(interval)
    }, [targetSystem])

    const currentCpu = resourceData.cpu[resourceData.cpu.length - 1]?.value || 0
    const currentGpu = resourceData.gpu[resourceData.gpu.length - 1]?.value || 0
    const currentVram =
        resourceData.vram[resourceData.vram.length - 1]?.value || 0
    const currentNetwork =
        resourceData.network[resourceData.network.length - 1]?.value || 0
    const currentMemory =
        resourceData.memory[resourceData.memory.length - 1]?.value || 0

    const hasAnySpikes = [
        ...resourceData.cpu,
        ...resourceData.gpu,
        ...resourceData.vram,
        ...resourceData.network,
        ...resourceData.memory,
        ...agents.flatMap((a) => a.memory),
    ].some((d) => d.isSpike)

    return (
        <Card className='transition-all duration-300 hover:shadow-lg'>
            <div className='p-4'>
                {/* Header */}
                <div className='mb-4 flex items-center justify-between'>
                    <div className='flex items-center gap-3'>
                        <div
                            className='flex cursor-pointer items-center gap-2'
                            onClick={() => setIsExpanded(!isExpanded)}
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
                        </div>

                        <TargetConfigDialog
                            targetSystem={targetSystem}
                            tempTarget={tempTarget}
                            isOpen={isDialogOpen}
                            onOpenChange={setIsDialogOpen}
                            onTempTargetChange={setTempTarget}
                            onSave={handleSaveTarget}
                        />

                        {hasAnySpikes && (
                            <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: 'spring', stiffness: 400, damping: 10 }}
                            >
                                <Badge
                                    variant='destructive'
                                    className='animate-pulse px-2 py-1 text-xs text-white'
                                >
                                    <Activity className='mr-1 h-3 w-3' />
                                    High Usage
                                </Badge>
                            </motion.div>
                        )}
                    </div>
                    <motion.div
                        animate={{ rotate: isExpanded ? 180 : 0 }}
                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                        className='text-muted-foreground cursor-pointer'
                        onClick={() => setIsExpanded(!isExpanded)}
                    >
                        ▼
                    </motion.div>
                </div>

                {/* Main Metrics Grid */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    onClick={() => setIsExpanded(!isExpanded)}
                    className='cursor-pointer'
                >
                    <div className='grid grid-cols-2 gap-1.5'>
                        <ResourceCard
                            icon={Cpu}
                            label='CPU'
                            value={currentCpu}
                            data={resourceData.cpu}
                            color='#3b82f6'
                        />
                        <ResourceCard
                            icon={Zap}
                            label='GPU'
                            value={currentGpu}
                            data={resourceData.gpu}
                            color='#10b981'
                        />
                        <ResourceCard
                            icon={HardDrive}
                            label='VRAM'
                            value={currentVram}
                            data={resourceData.vram}
                            color='#f59e0b'
                        />
                        <ResourceCard
                            icon={Wifi}
                            label='Network'
                            value={currentNetwork}
                            data={resourceData.network}
                            color='#8b5cf6'
                            unit='MB/s'
                        />
                    </div>
                </motion.div>

                {/* Expanded Section */}
                <AnimatePresence>
                    {isExpanded && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                            className='overflow-hidden'
                        >
                            <div className='border-t px-3 pb-3'>
                                <div className='mt-3 mb-2'>
                                    <ResourceCard
                                        icon={HardDrive}
                                        label='System Memory'
                                        value={currentMemory}
                                        data={resourceData.memory}
                                        color='#ef4444'
                                        unit='GB'
                                    />
                                </div>

                                <div className='space-y-1'>
                                    <span className='text-muted-foreground text-xs font-medium'>
                                        Per-Agent Memory
                                    </span>
                                    {agents.map((agent, index) => (
                                        <motion.div
                                            key={agent.id}
                                            initial={{ x: -20, opacity: 0 }}
                                            animate={{ x: 0, opacity: 1 }}
                                            transition={{
                                                delay: index * 0.1,
                                                type: 'spring',
                                                stiffness: 300,
                                                damping: 30,
                                            }}
                                        >
                                            <AgentMemoryCard agent={agent} />
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </Card>
    )
}

export default SystemMonitor
