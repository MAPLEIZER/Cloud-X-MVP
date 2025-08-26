import { useState } from 'react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, Loader2, Play, Square } from 'lucide-react'
import { useApp } from '@/context/app-context'
import { ConnectionStatus } from '@/components/custom/connection-status'

const scanOptions = {
  nmap: [
    { value: 'default', label: 'Default Scan (-sV -T4)', requiresPort: false },
    { value: 'quick', label: 'Quick Scan (-T4 -F)', requiresPort: false },
    { value: 'intense', label: 'Intense Scan (-T4 -A -v)', requiresPort: false },
    { value: 'tcp', label: 'TCP Connect Scan (-sT)', requiresPort: false },
    { value: 'udp', label: 'UDP Scan (-sU)', requiresPort: false },
  ],
  zmap: [
    { value: 'tcp_syn', label: 'TCP SYN Scan', requiresPort: true },
    { value: 'icmp_echo', label: 'ICMP Echo Scan (Ping)', requiresPort: false },
  ],
  masscan: [
    { value: 'tcp_scan', label: 'Fast TCP Scan', requiresPort: true },
    { value: 'udp_scan', label: 'Fast UDP Scan', requiresPort: true },
    { value: 'ping_scan', label: 'Ping Scan', requiresPort: false },
  ],
}

export function NetworkScan() {
  const { state, startScan } = useApp()
  const [formData, setFormData] = useState({
    target: '',
    tool: 'nmap' as keyof typeof scanOptions,
    scanType: 'default',
    port: '',
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleToolChange = (selectedTool: keyof typeof scanOptions) => {
    setFormData(prev => ({
      ...prev,
      tool: selectedTool,
      scanType: scanOptions[selectedTool][0].value,
      port: '',
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    if (!formData.target) {
      setError('Please enter a target domain or IP address.')
      setIsLoading(false)
      return
    }

    const needsPort = scanOptions[formData.tool].find(opt => opt.value === formData.scanType)?.requiresPort

    if (needsPort && !formData.port) {
      setError('This scan type requires a port number.')
      setIsLoading(false)
      return
    }

    try {
      await startScan({
        target: formData.target,
        tool: formData.tool,
        scan_type: formData.scanType,
        port: needsPort ? formData.port : undefined,
      })

      // Navigate to scan history page
      window.location.href = '/apps/network/history'
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  const currentScanOptions = scanOptions[formData.tool]
  const needsPort = currentScanOptions.find(opt => opt.value === formData.scanType)?.requiresPort

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Network Scanner</h1>
          <p className="text-muted-foreground">
            Scan targets for network vulnerabilities and open ports
          </p>
        </div>
        <ConnectionStatus />
      </div>

      {/* Scan Form */}
      <Card>
        <CardHeader>
          <CardTitle>Configure Network Scan</CardTitle>
          <CardDescription>
            Select your target, scanning tool, and scan type to begin security analysis
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-6">
            {/* Target and Tool Row */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="target" className="text-sm font-medium">
                  Target
                </label>
                <Input
                  id="target"
                  placeholder="e.g., 192.168.1.1 or example.com"
                  value={formData.target}
                  onChange={(e) => setFormData(prev => ({ ...prev, target: e.target.value }))}
                  disabled={isLoading || !state.isConnected}
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="tool" className="text-sm font-medium">
                  Scanning Tool
                </label>
                <Select
                  value={formData.tool}
                  onValueChange={handleToolChange}
                  disabled={isLoading}
                >
                  <SelectTrigger id="tool">
                    <SelectValue placeholder="Select a tool" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="nmap">Nmap</SelectItem>
                    <SelectItem value="zmap">ZMap</SelectItem>
                    <SelectItem value="masscan">Masscan</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Scan Type and Port Row */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="scanType" className="text-sm font-medium">
                  Scan Type
                </label>
                <Select
                  value={formData.scanType}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, scanType: value }))}
                  disabled={isLoading}
                >
                  <SelectTrigger id="scanType">
                    <SelectValue placeholder="Select scan type" />
                  </SelectTrigger>
                  <SelectContent>
                    {currentScanOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {needsPort && (
                <div className="space-y-2">
                  <label htmlFor="port" className="text-sm font-medium">
                    Port
                  </label>
                  <Input
                    id="port"
                    placeholder="Enter port (e.g., 80)"
                    value={formData.port}
                    onChange={(e) => setFormData(prev => ({ ...prev, port: e.target.value }))}
                    disabled={isLoading}
                  />
                </div>
              )}
            </div>

            {/* Connection Status Alert */}
            <Alert variant={state.isConnected ? 'default' : 'destructive'}>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {state.isConnected === true
                  ? 'Connected to backend server'
                  : state.isConnected === false
                  ? 'Disconnected from backend server'
                  : 'Checking connection...'}
              </AlertDescription>
            </Alert>

            {/* Error Alert */}
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Loading State */}
            {isLoading && (
              <Alert>
                <Loader2 className="h-4 w-4 animate-spin" />
                <AlertDescription>Starting scan...</AlertDescription>
              </Alert>
            )}
          </CardContent>
          <CardFooter className="flex justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                Tool: {formData.tool.toUpperCase()}
              </Badge>
              <Badge variant="outline" className="text-xs">
                Type: {currentScanOptions.find(opt => opt.value === formData.scanType)?.label}
              </Badge>
            </div>
            <Button
              type="submit"
              disabled={isLoading || !state.isConnected}
              className="min-w-32"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Start Scan
                </>
              )}
            </Button>
          </CardFooter>
        </form>
      </Card>

      {/* Active Scans */}
      {state.scans.filter(scan => scan.status === 'running' || scan.status === 'submitted').length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Active Scans</CardTitle>
            <CardDescription>
              Currently running network scans
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {state.scans
                .filter(scan => scan.status === 'running' || scan.status === 'submitted')
                .map((scan) => (
                  <div key={scan.job_id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center space-x-2">
                        <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                        <div>
                          <p className="font-medium">{scan.target}</p>
                          <p className="text-sm text-muted-foreground">
                            {scan.tool} • {scan.scan_type}
                            {scan.progress && ` • ${scan.progress}%`}
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className="bg-blue-100 text-blue-800">
                        {scan.status}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          // Stop scan functionality (we'll implement this)
                        }}
                      >
                        <Square className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
