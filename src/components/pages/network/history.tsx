import { useState, useMemo } from 'react'
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { 
  Search, 
  Eye, 
  Download, 
  RefreshCw, 
  Network, 
  Clock, 
  Target, 
  Settings, 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  Server, 
  Code, 
  ChevronDown, 
  ChevronUp,
  ArrowUpDown,
  Trash2,
  Activity
} from 'lucide-react'
import { useApp } from '@/context/app-context'
import { ConnectionStatus } from '@/components/custom/connection-status'
import { CloudXLogo } from '@/assets/cloud-x-logo'
import { format } from 'date-fns'

// Types
interface NetworkScan {
  job_id: string
  target: string
  tool: string
  scan_type: string
  status: 'completed' | 'running' | 'failed' | 'submitted'
  progress?: number
  created_at: string
  results?: any
}

// Date Badge Component
function DateBadge({ date: rawDate }: { date: string | Date }) {
  const date = new Date(rawDate)
  const day = format(date, 'd')
  const month = format(date, 'LLL')

  return (
    <div className="bg-background/40 flex size-10 shrink-0 cursor-default flex-col items-center justify-center rounded-md border text-center">
      <span className="text-sm font-semibold leading-snug">{day}</span>
      <span className="text-muted-foreground text-xs leading-none">
        {month}
      </span>
    </div>
  )
}

// Status Badge Component
function StatusBadge({ status }: { status: NetworkScan['status'] }) {
  const statusConfig = {
    completed: {
      variant: 'default' as const,
      icon: CheckCircle,
      text: 'Completed',
      className: 'bg-green-100 text-green-800 border-green-200'
    },
    running: {
      variant: 'default' as const,
      icon: RefreshCw,
      text: 'Running',
      className: 'bg-blue-100 text-blue-800 border-blue-200'
    },
    failed: {
      variant: 'destructive' as const,
      icon: AlertTriangle,
      text: 'Failed',
      className: 'bg-red-100 text-red-800 border-red-200'
    },
    submitted: {
      variant: 'secondary' as const,
      icon: Clock,
      text: 'Submitted',
      className: 'bg-yellow-100 text-yellow-800 border-yellow-200'
    },
  }

  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <Badge className={`flex items-center gap-1 ${config.className}`}>
      <Icon
        size={12}
        className={status === 'running' ? 'animate-spin' : ''}
      />
      {config.text}
    </Badge>
  )
}

// Tool Badge Component
function ToolBadge({ tool }: { tool: string }) {
  const toolConfig = {
    nmap: { color: 'bg-purple-100 text-purple-800 border-purple-200', text: 'NMAP' },
    zmap: { color: 'bg-indigo-100 text-indigo-800 border-indigo-200', text: 'ZMAP' },
    masscan: { color: 'bg-orange-100 text-orange-800 border-orange-200', text: 'MASSCAN' }
  }

  const config = toolConfig[tool as keyof typeof toolConfig] || {
    color: 'bg-gray-100 text-gray-800 border-gray-200',
    text: tool.toUpperCase()
  }

  return (
    <Badge className={`flex items-center gap-1 ${config.color}`}>
      <Network size={12} />
      {config.text}
    </Badge>
  )
}

export function NetworkHistory() {
  const { state } = useApp()
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [selectedScan, setSelectedScan] = useState<NetworkScan | null>(null)
  const [isResultsDialogOpen, setIsResultsDialogOpen] = useState(false)
  const [showRawJson, setShowRawJson] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      // TODO: Implement refresh functionality
      await new Promise(resolve => setTimeout(resolve, 1000))
    } finally {
      setIsRefreshing(false)
    }
  }

  const columns: ColumnDef<NetworkScan>[] = [
    {
      accessorKey: 'target',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto p-0 font-medium"
        >
          Target
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Target size={16} className="text-muted-foreground" />
          <span className="font-medium break-words">{row.getValue('target')}</span>
        </div>
      ),
    },
    {
      accessorKey: 'created_at',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto p-0 font-medium"
        >
          Date
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const date = new Date(row.getValue('created_at'))
        return (
          <div className="flex items-center gap-2">
            <DateBadge date={date} />
            <div className="flex flex-col">
              <span className="text-sm font-medium">
                {format(date, 'MMM dd, yyyy')}
              </span>
              <span className="text-xs text-muted-foreground">
                {format(date, 'HH:mm:ss')}
              </span>
            </div>
          </div>
        )
      },
    },
    {
      accessorKey: 'tool',
      header: 'Tool',
      cell: ({ row }) => <ToolBadge tool={row.getValue('tool')} />,
    },
    {
      accessorKey: 'scan_type',
      header: 'Scan Type',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-blue-500" />
          <span className="text-sm text-muted-foreground">{row.getValue('scan_type')}</span>
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.getValue('status')} />,
    },
    {
      accessorKey: 'progress',
      header: 'Progress',
      cell: ({ row }) => {
        const status = row.original.status
        const progress = row.original.progress
        
        if (status === 'running' && progress) {
          return (
            <div className="flex items-center gap-2">
              <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-600 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-xs text-muted-foreground">{progress}%</span>
            </div>
          )
        } else if (status === 'completed') {
          return <span className="text-xs text-green-600">100%</span>
        }
        return <span className="text-xs text-muted-foreground">-</span>
      },
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const scan = row.original
        
        return (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => viewScanResults(scan)}
              disabled={scan.status !== 'completed'}
              className="h-8 w-8"
              title="View scan results"
            >
              <Eye size={14} />
            </Button>
            {scan.status === 'completed' && scan.results && (
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-8 w-8"
                onClick={() => downloadResults(scan)}
                title="Download results"
              >
                <Download size={14} />
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-destructive"
              title="Delete scan"
            >
              <Trash2 size={14} />
            </Button>
          </div>
        )
      },
    },
  ]

  const table = useReactTable({
    data: state.scans,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
  })

  const stats = useMemo(() => {
    const total = state.scans.length
    const completed = state.scans.filter(s => s.status === 'completed').length
    const running = state.scans.filter(s => s.status === 'running').length
    const failed = state.scans.filter(s => s.status === 'failed').length
    
    return { total, completed, running, failed }
  }, [state.scans])

  const viewScanResults = (scan: NetworkScan) => {
    setSelectedScan(scan)
    setIsResultsDialogOpen(true)
    setShowRawJson(false)
  }

  const formatScanResults = (results: any) => {
    if (!results) return 'No results available'
    
    try {
      const parsedResults = typeof results === 'string' ? JSON.parse(results) : results
      return JSON.stringify(parsedResults, null, 2)
    } catch {
      return typeof results === 'string' ? results : JSON.stringify(results, null, 2)
    }
  }

  const formatDate = (dateString: string) => {
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

  const parseScanResults = (results: any) => {
    if (!results) return null
    
    try {
      const parsedResults = typeof results === 'string' ? JSON.parse(results) : results
      
      // Handle nmap XML format converted to JSON
      if (parsedResults.nmaprun) {
        const nmapData = parsedResults.nmaprun
        const hosts = []
        let totalPorts = 0
        
        if (nmapData.host) {
          const hostArray = Array.isArray(nmapData.host) ? nmapData.host : [nmapData.host]
          
          for (const host of hostArray) {
            const hostInfo = {
              ip: host.address?.addr || 'Unknown',
              status: host.status?.state || 'unknown',
              hostnames: host.hostnames?.hostname?.name || 'No hostname',
              os: host.os?.osmatch?.[0]?.name || 'Unknown',
              openPorts: [] as any[],
              filteredPorts: [] as any[]
            }
            
            if (host.ports?.port) {
              const ports = Array.isArray(host.ports.port) ? host.ports.port : [host.ports.port]
              
              for (const port of ports) {
                totalPorts++
                const portInfo = {
                  portid: port.portid,
                  protocol: port.protocol,
                  state: port.state,
                  service: port.service
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
            hostsUp: hosts.filter(h => h.status === 'up').length,
            hostsDown: hosts.filter(h => h.status === 'down').length,
            totalPorts
          },
          hosts
        }
      }
      
      // Handle other formats or return null for unsupported formats
      return null
    } catch (error) {
      console.error('Error parsing scan results:', error)
      return null
    }
  }

  const downloadResults = (scan: NetworkScan) => {
    if (!scan.results) return
    
    try {
      const results = typeof scan.results === 'string' ? JSON.parse(scan.results) : scan.results
      const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `scan-${scan.job_id}-results.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (_error) {
      alert('Error downloading results')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Scan History</h1>
          <p className="text-muted-foreground">
            View and manage your network scan results
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ConnectionStatus />
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing || !state.isConnected}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Scans</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">
              All time scans
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
            <p className="text-xs text-muted-foreground">
              Successfully completed
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
            <RefreshCw className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats.running}</div>
            <p className="text-xs text-muted-foreground">
              Currently in progress
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
            <p className="text-xs text-muted-foreground">
              Failed to complete
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardHeader>
          <CardTitle>Search & Filter</CardTitle>
          <CardDescription>
            Find specific scans using filters and search
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search targets, tools, or scan types..."
                  value={(table.getColumn('target')?.getFilterValue() as string) ?? ''}
                  onChange={(event) =>
                    table.getColumn('target')?.setFilterValue(event.target.value)
                  }
                  className="pl-10 max-w-sm"
                />
              </div>
            </div>
            <Select
              value={(table.getColumn('status')?.getFilterValue() as string) ?? 'all'}
              onValueChange={(value) =>
                table.getColumn('status')?.setFilterValue(value === 'all' ? '' : value)
              }
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="submitted">Submitted</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={(table.getColumn('tool')?.getFilterValue() as string) ?? 'all'}
              onValueChange={(value) =>
                table.getColumn('tool')?.setFilterValue(value === 'all' ? '' : value)
              }
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by tool" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Tools</SelectItem>
                <SelectItem value="nmap">Nmap</SelectItem>
                <SelectItem value="zmap">ZMap</SelectItem>
                <SelectItem value="masscan">Masscan</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Data Table */}
      <Card>
        <CardHeader>
          <CardTitle>Scan History ({table.getFilteredRowModel().rows.length})</CardTitle>
          <CardDescription>
            {table.getFilteredRowModel().rows.length === 0 
              ? 'No scans found matching your criteria' 
              : `Showing ${table.getFilteredRowModel().rows.length} of ${state.scans.length} scans`
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          {table.getFilteredRowModel().rows.length === 0 ? (
            <div className="text-center py-12">
              <div className="flex flex-col items-center gap-2">
                <Network className="h-12 w-12 text-muted-foreground" />
                <p className="text-lg font-medium text-muted-foreground">No scans found</p>
                <p className="text-sm text-muted-foreground">
                  {state.scans.length === 0 
                    ? 'Start your first scan from the Network Scanner page'
                    : 'Try adjusting your search or filter criteria'
                  }
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    {table.getHeaderGroups().map((headerGroup) => (
                      <TableRow key={headerGroup.id}>
                        {headerGroup.headers.map((header) => (
                          <TableHead key={header.id} className="font-semibold">
                            {header.isPlaceholder
                              ? null
                              : flexRender(
                                  header.column.columnDef.header,
                                  header.getContext()
                                )}
                          </TableHead>
                        ))}
                      </TableRow>
                    ))}
                  </TableHeader>
                  <TableBody>
                    {table.getRowModel().rows.map((row) => (
                      <TableRow
                        key={row.id}
                        data-state={row.getIsSelected() && 'selected'}
                        className="hover:bg-muted/50 transition-colors"
                      >
                        {row.getVisibleCells().map((cell) => (
                          <TableCell key={cell.id}>
                            {flexRender(
                              cell.column.columnDef.cell,
                              cell.getContext()
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              
              {/* Pagination */}
              <div className="flex items-center justify-between">
                <div className="flex-1 text-sm text-muted-foreground">
                  {table.getFilteredSelectedRowModel().rows.length} of{' '}
                  {table.getFilteredRowModel().rows.length} row(s) selected.
                </div>
                <div className="flex items-center space-x-6 lg:space-x-8">
                  <div className="flex items-center space-x-2">
                    <p className="text-sm font-medium">Rows per page</p>
                    <Select
                      value={`${table.getState().pagination.pageSize}`}
                      onValueChange={(value) => {
                        table.setPageSize(Number(value))
                      }}
                    >
                      <SelectTrigger className="h-8 w-[70px]">
                        <SelectValue placeholder={table.getState().pagination.pageSize} />
                      </SelectTrigger>
                      <SelectContent side="top">
                        {[10, 20, 30, 40, 50].map((pageSize) => (
                          <SelectItem key={pageSize} value={`${pageSize}`}>
                            {pageSize}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex w-[100px] items-center justify-center text-sm font-medium">
                    Page {table.getState().pagination.pageIndex + 1} of{' '}
                    {table.getPageCount()}
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      className="hidden h-8 w-8 p-0 lg:flex"
                      onClick={() => table.setPageIndex(0)}
                      disabled={!table.getCanPreviousPage()}
                    >
                      <span className="sr-only">Go to first page</span>
                      <ChevronDown className="h-4 w-4 rotate-90" />
                    </Button>
                    <Button
                      variant="outline"
                      className="h-8 w-8 p-0"
                      onClick={() => table.previousPage()}
                      disabled={!table.getCanPreviousPage()}
                    >
                      <span className="sr-only">Go to previous page</span>
                      <ChevronDown className="h-4 w-4 rotate-90" />
                    </Button>
                    <Button
                      variant="outline"
                      className="h-8 w-8 p-0"
                      onClick={() => table.nextPage()}
                      disabled={!table.getCanNextPage()}
                    >
                      <span className="sr-only">Go to next page</span>
                      <ChevronDown className="h-4 w-4 -rotate-90" />
                    </Button>
                    <Button
                      variant="outline"
                      className="hidden h-8 w-8 p-0 lg:flex"
                      onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                      disabled={!table.getCanNextPage()}
                    >
                      <span className="sr-only">Go to last page</span>
                      <ChevronDown className="h-4 w-4 -rotate-90" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Scan Results Dialog */}
      <Dialog open={isResultsDialogOpen} onOpenChange={setIsResultsDialogOpen}>
        <DialogContent className="max-w-[95vw] w-[95vw] max-h-[95vh] overflow-y-auto flex flex-col sm:max-w-[95vw]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              Scan Results - {selectedScan?.job_id}
            </DialogTitle>
            <DialogDescription>
              Detailed results for {selectedScan?.tool?.toUpperCase()} scan of {selectedScan?.target}
            </DialogDescription>
          </DialogHeader>
          
          <ScrollArea className="flex-1 pr-6">
            <div className="flex justify-center">
              <div className="max-w-7xl w-full">
                {selectedScan && (() => {
                  const parsedData = parseScanResults(selectedScan.results)
                  
                  return (
                    <div className="space-y-4 pb-4">
                {/* Scan Info */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-muted/50 rounded-lg">
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Target className="h-4 w-4 flex-shrink-0" />
                        Target
                      </div>
                      <p className="text-sm text-muted-foreground break-words">{selectedScan.target}</p>
                    </div>
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Settings className="h-4 w-4 flex-shrink-0" />
                        Tool
                      </div>
                      <p className="text-sm text-muted-foreground break-words">{selectedScan.tool?.toUpperCase()}</p>
                    </div>
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Network className="h-4 w-4 flex-shrink-0" />
                        Scan Type
                      </div>
                      <p className="text-sm text-muted-foreground break-words">{selectedScan.scan_type}</p>
                    </div>
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Clock className="h-4 w-4 flex-shrink-0" />
                        Started
                      </div>
                      <p className="text-sm text-muted-foreground break-words">{formatDate(selectedScan.created_at)}</p>
                    </div>
                </div>
                
                <Separator />
                
                {parsedData ? (
                  <div className="space-y-6">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      <Card className="p-4 flex-1 min-w-0">
                        <div className="flex items-center gap-3 min-w-0">
                          <Server className="h-5 w-5 text-blue-600 flex-shrink-0" />
                          <div className="min-w-0 flex-1">
                            <p className="text-2xl font-bold break-words">{parsedData.summary.totalHosts}</p>
                            <p className="text-sm text-muted-foreground break-words">Total Hosts</p>
                          </div>
                        </div>
                      </Card>
                      <Card className="p-4 flex-1 min-w-0">
                        <div className="flex items-center gap-3 min-w-0">
                          <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                          <div className="min-w-0 flex-1">
                            <p className="text-2xl font-bold text-green-600 break-words">{parsedData.summary.hostsUp}</p>
                            <p className="text-sm text-muted-foreground break-words">Hosts Up</p>
                          </div>
                        </div>
                      </Card>
                      <Card className="p-4 flex-1 min-w-0">
                        <div className="flex items-center gap-3 min-w-0">
                          <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0" />
                          <div className="min-w-0 flex-1">
                            <p className="text-2xl font-bold text-red-600 break-words">{parsedData.summary.hostsDown}</p>
                            <p className="text-sm text-muted-foreground break-words">Hosts Down</p>
                          </div>
                        </div>
                      </Card>
                      <Card className="p-4 flex-1 min-w-0">
                        <div className="flex items-center gap-3 min-w-0">
                          <Shield className="h-5 w-5 text-purple-600 flex-shrink-0" />
                          <div className="min-w-0 flex-1">
                            <p className="text-2xl font-bold break-words">{parsedData.summary.totalPorts}</p>
                            <p className="text-sm text-muted-foreground break-words">Total Ports</p>
                          </div>
                        </div>
                      </Card>
                    </div>
                    
                    {/* Host Details */}
                    <div className="space-y-4">
                      <h4 className="text-lg font-semibold">Host Details</h4>
                      {parsedData.hosts.map((host: any, index: number) => (
                        <Card key={index} className="p-4">
                          <div className="space-y-4">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                              <div className="flex flex-col sm:flex-row sm:items-center gap-3 min-w-0 flex-1">
                                <div className="flex items-center gap-2 min-w-0">
                                  <Server className="h-4 w-4 flex-shrink-0" />
                                  <span className="font-medium break-words">{host.ip}</span>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {host.hostnames !== 'No hostname' && (
                                    <Badge variant="outline" className="break-words">{host.hostnames}</Badge>
                                  )}
                                  <Badge className={host.status === 'up' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                                    {host.status.toUpperCase()}
                                  </Badge>
                                </div>
                              </div>
                              {host.os !== 'Unknown' && (
                                <Badge variant="secondary" className="break-words flex-shrink-0">{host.os}</Badge>
                              )}
                            </div>
                            
                            {host.openPorts.length > 0 && (
                              <div className="space-y-2">
                                <h5 className="font-medium text-green-600 flex items-center gap-2">
                                  <CheckCircle className="h-4 w-4" />
                                  Open Ports ({host.openPorts.length})
                                </h5>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                                  {host.openPorts.map((port: any, portIndex: number) => (
                                    <div key={portIndex} className="p-3 bg-green-50 rounded-lg border border-green-200 min-w-0">
                                      <div className="flex items-center justify-between gap-2 mb-2">
                                        <span className="font-medium text-green-800 break-words">
                                          {port.portid}/{port.protocol}
                                        </span>
                                        <Badge className="bg-green-100 text-green-800 text-xs flex-shrink-0">
                                          {port.state?.state || 'open'}
                                        </Badge>
                                      </div>
                                      {port.service && (
                                        <div className="space-y-1 text-sm text-green-700">
                                          <p className="break-words"><strong>Service:</strong> {port.service.name || 'Unknown'}</p>
                                          {port.service.product && (
                                            <p className="break-words"><strong>Product:</strong> {port.service.product}</p>
                                          )}
                                          {port.service.version && (
                                            <p className="break-words"><strong>Version:</strong> {port.service.version}</p>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {host.filteredPorts.length > 0 && (
                              <div className="space-y-2">
                                <h5 className="font-medium text-yellow-600 flex items-center gap-2">
                                  <Shield className="h-4 w-4" />
                                  Filtered Ports ({host.filteredPorts.length})
                                </h5>
                                <div className="flex flex-wrap gap-2">
                                  {host.filteredPorts.slice(0, 10).map((port: any, portIndex: number) => (
                                    <Badge key={portIndex} className="bg-yellow-100 text-yellow-800">
                                      {port.portid}/{port.protocol}
                                    </Badge>
                                  ))}
                                  {host.filteredPorts.length > 10 && (
                                    <Badge variant="outline">+{host.filteredPorts.length - 10} more</Badge>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <AlertTriangle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">Unable to parse scan results</p>
                  </div>
                )}
                
                  {/* Raw JSON View */}
                  {showRawJson && (
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium flex items-center gap-2">
                        <Code className="h-4 w-4" />
                        Raw JSON Data
                      </h4>
                      <div className="h-[60vh] w-full border rounded-md overflow-auto">
                        <ScrollArea className="h-full w-full">
                          <pre className="p-4 text-xs font-mono whitespace-pre-wrap break-words overflow-wrap-anywhere">
                            {formatScanResults(selectedScan.results)}
                          </pre>
                        </ScrollArea>
                      </div>
                    </div>
                  )}
                </div>
              )
            })()}
              </div>
            </div>
          </ScrollArea>
          
          {/* Fixed Footer */}
          <div className="flex items-center justify-between pt-4 border-t bg-background">
            <Button
              variant="outline"
              onClick={() => setShowRawJson(!showRawJson)}
              className="flex items-center gap-2"
            >
              <Code className="h-4 w-4" />
              {showRawJson ? 'Hide' : 'Show'} Raw JSON
              {showRawJson ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
            
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => selectedScan && downloadResults(selectedScan)}
                disabled={!selectedScan?.results}
              >
                <Download className="h-4 w-4 mr-2" />
                Download Results
              </Button>
              <Button
                variant="outline"
                onClick={() => setIsResultsDialogOpen(false)}
              >
                Close
              </Button>
            </div>
          </div>


        </DialogContent>
      </Dialog>
    </div>
  )
}
