import { useState } from 'react'
import { motion } from 'framer-motion'
import type { DataPoint } from './types'
import { Sparkline } from './sparkline'

interface ResourceCardProps {
    icon: React.ComponentType<{ className?: string }>
    label: string
    value: number
    data: DataPoint[]
    color: string
    unit?: string
}

export function ResourceCard({
    icon: Icon,
    label,
    value,
    data,
    color,
    unit = '%',
}: ResourceCardProps) {
    const [isHovered, setIsHovered] = useState(false)
    const hasSpikes = data.some((d) => d.isSpike)

    return (
        <motion.div
            className='hover:bg-muted/50 flex items-center gap-2 rounded-lg p-1.5 transition-colors'
            onHoverStart={() => setIsHovered(true)}
            onHoverEnd={() => setIsHovered(false)}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
            <motion.div
                className='bg-muted flex h-7 w-7 items-center justify-center rounded-md'
                animate={{
                    backgroundColor: hasSpikes ? '#fef2f2' : undefined,
                    scale: isHovered ? 1.1 : 1,
                }}
                transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            >
                <Icon
                    className={`h-4 w-4 ${hasSpikes ? 'text-red-500' : 'text-muted-foreground'}`}
                />
            </motion.div>

            <div className='min-w-0 flex-1'>
                <div className='mb-1 flex items-center justify-between'>
                    <span className='text-muted-foreground text-xs font-medium'>
                        {label}
                    </span>
                    <motion.span
                        className={`font-mono text-xs ${hasSpikes ? 'text-red-500' : 'text-foreground'}`}
                        animate={{ color: hasSpikes ? '#ef4444' : undefined }}
                    >
                        {value.toFixed(1)} {unit}
                    </motion.span>
                </div>
                <div className='mt-1'>
                    <Sparkline data={data} color={color} />
                </div>
            </div>
        </motion.div>
    )
}
