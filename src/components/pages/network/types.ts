// Shared types for Network History components

export interface NetworkScan {
    job_id: string
    target: string
    tool: string
    scan_type: string
    status: 'completed' | 'running' | 'failed' | 'submitted' | 'stopped'
    progress?: number
    created_at: string
    results?: unknown
}

export interface PortInfo {
    portid: string
    protocol: string
    state: { state: string }
    service?: {
        name?: string
        product?: string
        version?: string
    }
}

export interface HostInfo {
    ip: string
    status: string
    hostnames: string
    os: string
    openPorts: PortInfo[]
    filteredPorts: PortInfo[]
}

export interface ParsedScanData {
    summary: {
        totalHosts: number
        hostsUp: number
        hostsDown: number
        totalPorts: number
    }
    hosts: HostInfo[]
}
