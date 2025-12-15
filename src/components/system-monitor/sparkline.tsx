import { useRef } from 'react'
import { motion } from 'framer-motion'
import type { DataPoint } from './types'

interface SparklineProps {
    data: DataPoint[]
    color?: string
    spikeColor?: string
    width?: number
    height?: number
}

export function Sparkline({
    data,
    color = '#3b82f6',
    spikeColor = '#ef4444',
    width = 60,
    height = 20,
}: SparklineProps) {
    const pathRef = useRef<SVGPathElement>(null)

    // Need at least 2 points to draw a line
    if (!data || data.length < 2) {
        return <svg width={width} height={height} className='overflow-visible' />
    }

    const points = data.map((point, index) => ({
        x: (index / (data.length - 1)) * width,
        y: height - (point.value / 100) * height,
        isSpike: point.isSpike,
    }))

    const path = points.reduce((acc, point, index) => {
        if (index === 0) return `M ${point.x} ${point.y}`
        return `${acc} L ${point.x} ${point.y}`
    }, '')

    const hasSpikes = points.some((p) => p.isSpike)

    return (
        <svg width={width} height={height} className='overflow-visible'>
            <defs>
                <linearGradient
                    id={`gradient-${color.replace('#', '')}`}
                    x1='0%'
                    y1='0%'
                    x2='0%'
                    y2='100%'
                >
                    <stop
                        offset='0%'
                        stopColor={hasSpikes ? spikeColor : color}
                        stopOpacity={0.3}
                    />
                    <stop
                        offset='100%'
                        stopColor={hasSpikes ? spikeColor : color}
                        stopOpacity={0.1}
                    />
                </linearGradient>
            </defs>

            <motion.path
                ref={pathRef}
                d={`${path} L ${width} ${height} L 0 ${height} Z`}
                fill={`url(#gradient-${color.replace('#', '')})`}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
            />

            <motion.path
                d={path}
                fill='none'
                stroke={hasSpikes ? spikeColor : color}
                strokeWidth={1.5}
                strokeLinecap='round'
                strokeLinejoin='round'
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
            />

            {/* Spike indicators */}
            {points.map((point, index) =>
                point.isSpike ? (
                    <motion.circle
                        key={index}
                        cx={point.x}
                        cy={point.y}
                        r={2}
                        fill={spikeColor}
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{
                            delay: index * 0.05,
                            type: 'spring',
                            stiffness: 400,
                            damping: 10,
                        }}
                    />
                ) : null
            )}
        </svg>
    )
}
