import { useState } from 'react'
import { motion } from 'framer-motion'
import type { Agent } from './types'
import { Sparkline } from './sparkline'

interface AgentMemoryCardProps {
    agent: Agent
}

export function AgentMemoryCard({ agent }: AgentMemoryCardProps) {
    const [isHovered, setIsHovered] = useState(false)
    const currentValue = agent.memory[agent.memory.length - 1]?.value || 0
    const hasSpikes = agent.memory.some((d) => d.isSpike)

    return (
        <motion.div
            className='hover:bg-muted/30 flex items-center gap-2 rounded-md p-2 transition-colors'
            onHoverStart={() => setIsHovered(true)}
            onHoverEnd={() => setIsHovered(false)}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
            <motion.div
                className='h-2 w-2 rounded-full'
                style={{ backgroundColor: hasSpikes ? '#ef4444' : agent.color }}
                animate={{
                    scale: isHovered ? 1.2 : 1,
                    backgroundColor: hasSpikes ? '#ef4444' : agent.color,
                }}
                transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            />

            <div className='min-w-0 flex-1'>
                <div className='flex items-center justify-between'>
                    <span className='text-muted-foreground truncate text-xs'>
                        {agent.name}
                    </span>
                    <motion.span
                        className={`ml-2 font-mono text-xs ${hasSpikes ? 'text-red-500' : 'text-foreground'}`}
                        animate={{ color: hasSpikes ? '#ef4444' : undefined }}
                    >
                        {currentValue.toFixed(0)}MB
                    </motion.span>
                </div>
                <div className='mt-1'>
                    <Sparkline
                        data={agent.memory}
                        color={agent.color}
                        width={40}
                        height={12}
                    />
                </div>
            </div>
        </motion.div>
    )
}
