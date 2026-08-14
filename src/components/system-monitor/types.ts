// Shared types for System Monitor components

export interface DataPoint {
    value: number
    timestamp: number
    isSpike?: boolean
}

export interface ResourceData {
    cpu: DataPoint[]
    memory: DataPoint[]
    disk: DataPoint[]
    network: DataPoint[]
    latency: DataPoint[]
}

// Retained for the standalone AgentMemoryCard component. The production system
// monitor no longer generates or displays synthetic per-agent memory histories.
export interface Agent {
    id: string
    name: string
    memory: DataPoint[]
    color: string
}
