import { useState, useCallback } from 'react'
import { Download, RefreshCw } from 'lucide-react'
import { useApp } from '@/context/app-context'
import { Button } from '@/components/ui/button'
import { ConnectionStatus } from '@/components/custom/connection-status'
import type { NetworkScan } from './types'
import { HistoryStats } from './history-stats'
import { HistoryTable } from './history-table'
import { ScanResultsDialog } from './scan-results-dialog'
import { exportHistoryToCSV, downloadScanResults } from './history-utils'

export function NetworkHistory() {
  const { state, deleteScan, fetchScans } = useApp()
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [selectedScan, setSelectedScan] = useState<NetworkScan | null>(null)
  const [isResultsDialogOpen, setIsResultsDialogOpen] = useState(false)

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    await fetchScans()
    setIsRefreshing(false)
  }, [fetchScans])

  const handleViewResults = useCallback((scan: NetworkScan) => {
    setSelectedScan(scan)
    setIsResultsDialogOpen(true)
  }, [])

  const handleDownload = useCallback((scan: NetworkScan) => {
    downloadScanResults(scan)
  }, [])

  const handleDelete = useCallback(
    async (jobId: string) => {
      await deleteScan(jobId)
    },
    [deleteScan]
  )

  const handleExportCSV = useCallback(() => {
    exportHistoryToCSV(state.scans as NetworkScan[])
  }, [state.scans])

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div>
          <h1 className='text-2xl font-bold tracking-tight'>Scan History</h1>
          <p className='text-muted-foreground'>
            View and manage your network scan results
          </p>
        </div>
        <div className='flex items-center gap-2'>
          <ConnectionStatus />
          <Button
            variant='outline'
            size='sm'
            onClick={handleExportCSV}
            className='hidden sm:flex'
          >
            <Download className='mr-2 h-4 w-4' />
            Export CSV
          </Button>
          <Button
            variant='outline'
            size='sm'
            onClick={handleRefresh}
            disabled={isRefreshing || !state.isConnected}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Statistics Cards */}
      <HistoryStats scans={state.scans as NetworkScan[]} />

      {/* Data Table */}
      <HistoryTable
        scans={state.scans as NetworkScan[]}
        isConnected={state.isConnected ?? false}
        isRefreshing={isRefreshing}
        onRefresh={handleRefresh}
        onViewResults={handleViewResults}
        onDownload={handleDownload}
        onDelete={handleDelete}
      />

      {/* Scan Results Dialog */}
      <ScanResultsDialog
        scan={selectedScan}
        isOpen={isResultsDialogOpen}
        onOpenChange={setIsResultsDialogOpen}
      />
    </div>
  )
}
