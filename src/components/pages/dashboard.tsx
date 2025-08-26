import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Link } from '@tanstack/react-router'
import { 
  Shield, 
  Activity, 
  AlertTriangle, 
  Clock, 
  Network,
  TrendingUp,
  Server,
  Play,
  History,
  Settings,
  BarChart3,
  Zap,
  CheckCircle,
  XCircle,
  Loader2
} from 'lucide-react'
import { useApp } from '@/context/app-context'
import { ConnectionStatus } from '@/components/custom/connection-status'
import SystemMonitor from '@/components/system-monitor'
export function Dashboard() {
  const { state } = useApp()
  
  // Calculate dashboard metrics
  const totalScans = state.scans.length
  const completedScans = state.scans.filter(scan => scan.status === 'completed').length
  const runningScans = state.scans.filter(scan => scan.status === 'running').length
  const failedScans = state.scans.filter(scan => scan.status === 'failed').length
  
  const recentScans = state.scans
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5)

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <Badge className="bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400 flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Completed
          </Badge>
        )
      case 'running':
        return (
          <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400 flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" />
            Running
          </Badge>
        )
      case 'failed':
        return (
          <Badge className="bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400 flex items-center gap-1">
            <XCircle className="w-3 h-3" />
            Failed
          </Badge>
        )
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const successRate = totalScans > 0 ? Math.round((completedScans / totalScans) * 100) : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor your network security posture and scan activities
          </p>
        </div>
        <div className="flex items-center gap-4">
          <ConnectionStatus />
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            <span className="text-sm font-medium">Cloud-X Security</span>
          </div>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-blue-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Scans</CardTitle>
            <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-full">
              <Activity className="h-4 w-4 text-blue-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">{totalScans}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Network security scans performed
            </p>
            <div className="mt-3">
              <Progress 
                value={Math.min((totalScans / 50) * 100, 100)} 
                className="h-2 bg-blue-100 dark:bg-blue-900/20" 
              />
              <p className="text-xs text-muted-foreground mt-1">
                {Math.min((totalScans / 50) * 100, 100).toFixed(0)}% of target (50)
              </p>
            </div>
          </CardContent>
        </Card>
        
        <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-orange-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Scans</CardTitle>
            <div className="p-2 bg-orange-100 dark:bg-orange-900/20 rounded-full">
              <Clock className="h-4 w-4 text-orange-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-orange-600">{runningScans}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Currently running scans
            </p>
            {runningScans > 0 && (
              <div className="mt-3 flex items-center gap-2 p-2 bg-orange-50 dark:bg-orange-900/10 rounded-md">
                <Zap className="h-4 w-4 text-orange-600 animate-pulse" />
                <span className="text-sm font-medium text-orange-600">Active Processing</span>
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-green-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-full">
              <TrendingUp className="h-4 w-4 text-green-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{successRate}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              Scan completion rate
            </p>
            <div className="mt-3">
              <Progress 
                value={successRate} 
                className="h-2 bg-green-100 dark:bg-green-900/20"
              />
              <p className="text-xs text-green-600 mt-1 font-medium">
                {successRate >= 80 ? 'Excellent' : successRate >= 60 ? 'Good' : 'Needs Improvement'}
              </p>
            </div>
          </CardContent>
        </Card>
        
        <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-red-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Scans</CardTitle>
            <div className="p-2 bg-red-100 dark:bg-red-900/20 rounded-full">
              <AlertTriangle className="h-4 w-4 text-red-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">{failedScans}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Require immediate attention
            </p>
            {failedScans > 0 ? (
              <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/10 rounded-md">
                <Badge variant="destructive" className="text-xs animate-pulse">
                  <AlertTriangle className="w-3 h-3 mr-1" />
                  Action Required
                </Badge>
              </div>
            ) : (
              <div className="mt-3 p-2 bg-green-50 dark:bg-green-900/10 rounded-md">
                <Badge className="text-xs bg-green-100 text-green-800">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  All Clear
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Recent Scans */}
        <Card className="col-span-4">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Scans</CardTitle>
                <CardDescription>
                  Latest network security scan activities
                </CardDescription>
              </div>
              <Link to="/apps/network/history">
                <Button variant="outline" size="sm">
                  <History className="mr-2 h-4 w-4" />
                  View All
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentScans.length === 0 ? (
                <div className="text-center py-6">
                  <Network className="mx-auto h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-2 text-sm font-semibold">No scans yet</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Start your first network scan to see results here.
                  </p>
                  <div className="mt-6">
                    <Link to="/apps/network/scan">
                      <Button>
                        <Play className="mr-2 h-4 w-4" />
                        Start Scan
                      </Button>
                    </Link>
                  </div>
                </div>
              ) : (
                recentScans.map((scan) => (
                  <div key={scan.job_id} className="flex items-center justify-between space-x-4 p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                    <div className="flex items-center space-x-4">
                      <div className="flex-shrink-0">
                        <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                          <Network className="h-4 w-4 text-blue-600" />
                        </div>
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">
                          {scan.target}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {scan.tool.toUpperCase()} • {scan.scan_type}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {scan.status === 'running' && scan.progress && (
                        <div className="text-xs text-muted-foreground">
                          {scan.progress}%
                        </div>
                      )}
                      {getStatusBadge(scan.status)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="col-span-3 hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-blue-600" />
              Quick Actions
            </CardTitle>
            <CardDescription>
              Common security tasks and operations
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link to="/apps/network/scan" className="block">
              <Button className="w-full justify-start hover:scale-105 transition-transform duration-200 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800" size="lg">
                <Play className="mr-2 h-4 w-4" />
                Start Network Scan
              </Button>
            </Link>
            <Link to="/apps/network/history" className="block">
              <Button className="w-full justify-start hover:scale-105 transition-transform duration-200" variant="outline" size="lg">
                <History className="mr-2 h-4 w-4" />
                View Scan History
              </Button>
            </Link>
            <Button className="w-full justify-start hover:scale-105 transition-transform duration-200" variant="outline" disabled size="lg">
              <BarChart3 className="mr-2 h-4 w-4" />
              Security Reports
              <Badge variant="secondary" className="ml-auto text-xs">
                Soon
              </Badge>
            </Button>
            <Link to="/settings" className="block">
              <Button className="w-full justify-start hover:scale-105 transition-transform duration-200" variant="outline" size="lg">
                <Settings className="mr-2 h-4 w-4" />
                Configure Settings
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            System Status
          </CardTitle>
          <CardDescription>
            Current status of backend services and connectivity
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Backend API</span>
                <Badge variant={state.isConnected ? "default" : "destructive"}>
                  {state.isConnected ? "Connected" : "Disconnected"}
                </Badge>
              </div>
              <Progress value={state.isConnected ? 100 : 0} className="h-2" />
              <p className="text-xs text-muted-foreground">
                Flask backend on {state.settings.apiBaseUrl}
              </p>
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Scanner Services</span>
                <Badge variant="default">Active</Badge>
              </div>
              <Progress value={85} className="h-2" />
              <p className="text-xs text-muted-foreground">
                Nmap, ZMap, Masscan available
              </p>
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Security Monitoring</span>
                <Badge variant="secondary">Standby</Badge>
              </div>
              <Progress value={60} className="h-2" />
              <p className="text-xs text-muted-foreground">
                Wazuh integration pending
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Monitor - Fixed position overlay */}
      <SystemMonitor />
    </div>
  )
}
