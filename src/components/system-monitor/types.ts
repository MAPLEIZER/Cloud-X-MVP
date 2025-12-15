// Shared types for System Monitor components

export interface DataPoint {
    value: number
    timestamp: number
    isSpike?: boolean
}

export interface ResourceData {
    cpu: DataPoint[]
    gpu: DataPoint[]
    vram: DataPoint[]
    network: DataPoint[]
    memory: DataPoint[]
}

export interface Agent {
    id: string
    name: string
    memory: DataPoint[]
    color: string
}

// Generate a single data point with optional spike
export function generateDataPoint(
    baseValue: number,
    variance: number,
    spikeChance = 0.05
): DataPoint {
    const isSpike = Math.random() < spikeChance
    const multiplier = isSpike ? 1.5 + Math.random() * 0.5 : 1
    const value = Math.max(
        0,
        Math.min(100, baseValue + (Math.random() - 0.5) * variance * multiplier)
    )

    return {
        value,
        timestamp: Date.now(),
        isSpike: isSpike && value > 70,
    }
}

// Generate initial data array to avoid empty state
export function generateInitialData(
    count: number,
    base: number,
    variance: number
): DataPoint[] {
    const data: DataPoint[] = []
    const now = Date.now()
    for (let i = 0; i < count; i++) {
        data.push({
            value: Math.max(
                0,
                Math.min(100, base + (Math.random() - 0.5) * variance)
            ),
            timestamp: now - (count - 1 - i) * 1000,
            isSpike: false,
        })
    }
    return data
}
