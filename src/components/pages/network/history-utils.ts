import { format } from 'date-fns'
import type { NetworkScan, PortInfo, ParsedScanData } from './types'

// Format scan results for display
export function formatScanResults(results: unknown): string {
    if (!results) return 'No results available'

    try {
        const parsedResults =
            typeof results === 'string' ? JSON.parse(results) : results
        return JSON.stringify(parsedResults, null, 2)
    } catch {
        return typeof results === 'string'
            ? results
            : JSON.stringify(results, null, 2)
    }
}

// Format date relative to now
export function formatRelativeDate(dateString: string): string {
    try {
        const date = new Date(dateString)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMins / 60)
        const diffDays = Math.floor(diffHours / 24)

        if (diffMins < 1) return 'Just now'
        if (diffMins < 60) return `${diffMins}m ago`
        if (diffHours < 24) return `${diffHours}h ago`
        return `${diffDays}d ago`
    } catch {
        return 'Unknown'
    }
}

// Parse nmap scan results into structured data
export function parseScanResults(results: unknown): ParsedScanData | null {
    if (!results) return null

    try {
        const parsedResults =
            typeof results === 'string' ? JSON.parse(results) : results

        // Handle nmap XML format converted to JSON
        if (parsedResults.nmaprun) {
            const nmapData = parsedResults.nmaprun
            const hosts = []
            let totalPorts = 0

            if (nmapData.host) {
                const hostArray = Array.isArray(nmapData.host)
                    ? nmapData.host
                    : [nmapData.host]

                for (const host of hostArray) {
                    const hostInfo = {
                        ip: host.address?.addr || 'Unknown',
                        status: host.status?.state || 'unknown',
                        hostnames: host.hostnames?.hostname?.name || 'No hostname',
                        os: host.os?.osmatch?.[0]?.name || 'Unknown',
                        openPorts: [] as PortInfo[],
                        filteredPorts: [] as PortInfo[],
                    }

                    if (host.ports?.port) {
                        const ports = Array.isArray(host.ports.port)
                            ? host.ports.port
                            : [host.ports.port]

                        for (const port of ports) {
                            totalPorts++
                            const portInfo = {
                                portid: port.portid,
                                protocol: port.protocol,
                                state: port.state,
                                service: port.service,
                            }

                            if (port.state?.state === 'open') {
                                hostInfo.openPorts.push(portInfo)
                            } else if (port.state?.state === 'filtered') {
                                hostInfo.filteredPorts.push(portInfo)
                            }
                        }
                    }

                    hosts.push(hostInfo)
                }
            }

            return {
                summary: {
                    totalHosts: hosts.length,
                    hostsUp: hosts.filter((h) => h.status === 'up').length,
                    hostsDown: hosts.filter((h) => h.status === 'down').length,
                    totalPorts,
                },
                hosts,
            }
        }

        return null
    } catch {
        return null
    }
}

// Export scan history to CSV
export function exportHistoryToCSV(scans: NetworkScan[]): void {
    const headers = ['Target', 'Tool', 'Scan Type', 'Status', 'Date', 'Job ID']
    const csvContent = [
        headers.join(','),
        ...scans.map((scan) =>
            [
                `"${scan.target}"`,
                scan.tool,
                scan.scan_type,
                scan.status,
                `"${new Date(scan.created_at).toISOString()}"`,
                scan.job_id,
            ].join(',')
        ),
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute(
        'download',
        `scan_history_${format(new Date(), 'yyyy-MM-dd')}.csv`
    )
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
}

// Download individual scan results
export function downloadScanResults(scan: NetworkScan): void {
    if (!scan.results) return

    try {
        const results =
            typeof scan.results === 'string'
                ? JSON.parse(scan.results as string)
                : scan.results
        const blob = new Blob([JSON.stringify(results, null, 2)], {
            type: 'application/json',
        })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `scan-${scan.job_id}-results.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    } catch {
        alert('Error downloading results')
    }
}
