import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Search, Eye, Download, RefreshCw, Network, Clock, Target, Settings } from 'lucide-react'
import { useApp } from '@/context/app-context'
import { ConnectionStatus } from '@/components/custom/connection-status'

export function NetworkHistory() {
  const { state } = useApp()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [toolFilter, setToolFilter] = useState<string>('all')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [selectedScan, setSelectedScan] = useState<any>(null)
  const [isResultsDialogOpen, setIsResultsDialogOpen] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      // TODO: Implement refresh functionality
      await new Promise(resolve => setTimeout(resolve, 1000))
    } finally {
      setIsRefreshing(false)
    }
  }

  // Filter scans based on search and filters
  const filteredScans = state.scans.filter(scan => {
    const matchesSearch = scan.target.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         scan.tool.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         scan.scan_type.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesStatus = statusFilter === 'all' || scan.status === statusFilter
    const matchesTool = toolFilter === 'all' || scan.tool === toolFilter
    
    return matchesSearch && matchesStatus && matchesTool
  })

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-100 text-green-800">Completed</Badge>
      case 'running':
        return <Badge className="bg-blue-100 text-blue-800">Running</Badge>
      case 'failed':
        return <Badge className="bg-red-100 text-red-800">Failed</Badge>
      case 'submitted':
        return <Badge className="bg-yellow-100 text-yellow-800">Submitted</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const getToolBadge = (tool: string) => {
    const colors = {
      nmap: 'bg-purple-100 text-purple-800',
      zmap: 'bg-indigo-100 text-indigo-800',
      masscan: 'bg-orange-100 text-orange-800'
    }
    return <Badge className={colors[tool as keyof typeof colors] || 'bg-gray-100 text-gray-800'}>{tool.toUpperCase()}</Badge>
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

  const viewScanResults = (scan: any) => {
    setSelectedScan(scan)
    setIsResultsDialogOpen(true)
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

  const downloadResults = (scan: { job_id: string; results?: Record<string, unknown> | string }) => {
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

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filter Scans</CardTitle>
          <CardDescription>
            Search and filter your scan history
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label htmlFor="search" className="text-sm font-medium">
                Search
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search by target, tool, or type..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label htmlFor="status" className="text-sm font-medium">
                Status
              </label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger id="status">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="submitted">Submitted</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label htmlFor="tool" className="text-sm font-medium">
                Tool
              </label>
              <Select value={toolFilter} onValueChange={setToolFilter}>
                <SelectTrigger id="tool">
                  <SelectValue placeholder="All tools" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tools</SelectItem>
                  <SelectItem value="nmap">Nmap</SelectItem>
                  <SelectItem value="zmap">ZMap</SelectItem>
                  <SelectItem value="masscan">Masscan</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Scan Results Table */}
      <Card>
        <CardHeader>
          <CardTitle>Scan Results ({filteredScans.length})</CardTitle>
          <CardDescription>
            {filteredScans.length === 0 ? 'No scans found' : `Showing ${filteredScans.length} scan(s)`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredScans.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">No scans found matching your criteria.</p>
              {state.scans.length === 0 && (
                <p className="text-sm text-muted-foreground mt-2">
                  Start your first scan from the Network Scanner page.
                </p>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-b">
                    <TableHead className="font-semibold">Target</TableHead>
                    <TableHead className="font-semibold">Tool</TableHead>
                    <TableHead className="font-semibold">Scan Type</TableHead>
                    <TableHead className="font-semibold">Status</TableHead>
                    <TableHead className="font-semibold">Progress</TableHead>
                    <TableHead className="font-semibold">Started</TableHead>
                    <TableHead className="font-semibold text-center">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredScans
                    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                    .map((scan) => (
                      <TableRow key={scan.job_id}>
                        <TableCell className="font-medium">
                          {scan.target}
                        </TableCell>
                        <TableCell>
                          {getToolBadge(scan.tool)}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {scan.scan_type}
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(scan.status)}
                        </TableCell>
                        <TableCell>
                          {scan.status === 'running' && scan.progress ? (
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-blue-600 transition-all duration-300"
                                  style={{ width: `${scan.progress}%` }}
                                />
                              </div>
                              <span className="text-xs text-muted-foreground">{scan.progress}%</span>
                            </div>
                          ) : scan.status === 'completed' ? (
                            <span className="text-xs text-green-600">100%</span>
                          ) : (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(scan.created_at)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-center gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => viewScanResults(scan)}
                              disabled={scan.status !== 'completed'}
                              className="hover:bg-muted transition-colors"
                              title="View scan results"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => downloadResults(scan)}
                              disabled={scan.status !== 'completed' || !scan.results}
                              className="hover:bg-muted transition-colors"
                              title="Download results"
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Scan Results Dialog */}
      <Dialog open={isResultsDialogOpen} onOpenChange={setIsResultsDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              Scan Results - {selectedScan?.job_id}
            </DialogTitle>
            <DialogDescription>
              Detailed results for {selectedScan?.tool?.toUpperCase()} scan of {selectedScan?.target}
            </DialogDescription>
          </DialogHeader>
          
          {selectedScan && (
            <div className="space-y-4">
              {/* Scan Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-muted/50 rounded-lg">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Target className="h-4 w-4" />
                    Target
                  </div>
                  <p className="text-sm text-muted-foreground">{selectedScan.target}</p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Settings className="h-4 w-4" />
                    Tool
                  </div>
                  <p className="text-sm text-muted-foreground">{selectedScan.tool?.toUpperCase()}</p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Network className="h-4 w-4" />
                    Scan Type
                  </div>
                  <p className="text-sm text-muted-foreground">{selectedScan.scan_type}</p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Clock className="h-4 w-4" />
                    Started
                  </div>
                  <p className="text-sm text-muted-foreground">{formatDate(selectedScan.created_at)}</p>
                </div>
              </div>
              
              <Separator />
              
              {/* Results */}
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Scan Results</h4>
                <ScrollArea className="h-[400px] w-full border rounded-md">
                  <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                    {formatScanResults(selectedScan.results)}
                  </pre>
                </ScrollArea>
              </div>
              
              {/* Actions */}
              <div className="flex justify-end gap-2 pt-4">
                <Button
                  variant="outline"
                  onClick={() => downloadResults(selectedScan)}
                  disabled={!selectedScan.results}
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
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
