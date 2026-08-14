import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
  FileSearch,
  HardDrive,
  RefreshCw,
  Server,
  ShieldCheck,
  ShieldOff,
} from 'lucide-react'
import {
  apiClient,
  CloudXApiError,
  type SecurityAgent,
  type SecurityAlert,
} from '@/lib/api-client'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

function formatTimestamp(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function agentStatusBadge(status: string) {
  if (status === 'active') return <Badge>Active</Badge>
  if (status === 'disconnected' || status === 'never_connected') {
    return <Badge variant='destructive'>{status.replace('_', ' ')}</Badge>
  }
  return <Badge variant='secondary'>{status || 'unknown'}</Badge>
}

function severityBadge(level: number) {
  if (level >= 12) return <Badge variant='destructive'>Critical · {level}</Badge>
  if (level >= 8) return <Badge>High · {level}</Badge>
  if (level >= 5) return <Badge variant='secondary'>Medium · {level}</Badge>
  return <Badge variant='outline'>Low · {level}</Badge>
}

function queryMessage(error: unknown) {
  if (error instanceof CloudXApiError) {
    if (error.code === 'security_engine_not_configured') {
      return 'Wazuh is not configured on the Cloud-X backend yet.'
    }
    if (error.code === 'security_engine_upstream_error') {
      return 'Cloud-X is configured for Wazuh, but the upstream service is currently unavailable.'
    }
  }
  return error instanceof Error ? error.message : 'Unable to load security data.'
}

function AgentSelector({
  agents,
  value,
  onChange,
}: {
  agents: SecurityAgent[]
  value: string
  onChange: (value: string) => void
}) {
  if (agents.length === 0) {
    return <p className='text-muted-foreground text-sm'>No Wazuh agents available.</p>
  }

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className='w-full sm:w-[320px]'>
        <SelectValue placeholder='Choose a Wazuh endpoint' />
      </SelectTrigger>
      <SelectContent>
        {agents.map((agent) => (
          <SelectItem key={agent.id} value={agent.id}>
            {agent.name} · {agent.id}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function WazuhDashboard() {
  const queryClient = useQueryClient()
  const [selectedAgentId, setSelectedAgentId] = useState('')

  const statusQuery = useQuery({
    queryKey: ['security-engine', 'status'],
    queryFn: () => apiClient.getSecurityStatus(),
    retry: false,
    refetchInterval: 30_000,
  })

  const engineReady = statusQuery.isSuccess
  const overviewQuery = useQuery({
    queryKey: ['security-engine', 'overview'],
    queryFn: () => apiClient.getSecurityOverview(),
    enabled: engineReady,
    retry: false,
    refetchInterval: 15_000,
  })
  const agentsQuery = useQuery({
    queryKey: ['security-engine', 'agents'],
    queryFn: () => apiClient.getSecurityAgents(200),
    enabled: engineReady,
    retry: false,
    refetchInterval: 30_000,
  })
  const alertsQuery = useQuery({
    queryKey: ['security-engine', 'alerts'],
    queryFn: () => apiClient.getSecurityAlerts(50),
    enabled: engineReady && statusQuery.data?.indexer_configured === true,
    retry: false,
    refetchInterval: 15_000,
  })

  const agents = agentsQuery.data ?? []
  const alerts = alertsQuery.data ?? []

  useEffect(() => {
    if (!selectedAgentId && agents.length > 0) {
      setSelectedAgentId(agents[0].id)
    }
    if (
      selectedAgentId &&
      agents.length > 0 &&
      !agents.some((agent) => agent.id === selectedAgentId)
    ) {
      setSelectedAgentId(agents[0].id)
    }
  }, [agents, selectedAgentId])

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId),
    [agents, selectedAgentId]
  )

  const scaQuery = useQuery({
    queryKey: ['security-engine', 'sca', selectedAgentId],
    queryFn: () => apiClient.getSecuritySca(selectedAgentId, 200),
    enabled: engineReady && Boolean(selectedAgentId),
    retry: false,
    refetchInterval: 60_000,
  })
  const fimQuery = useQuery({
    queryKey: ['security-engine', 'fim', selectedAgentId],
    queryFn: () => apiClient.getSecurityFim(selectedAgentId, 200),
    enabled: engineReady && Boolean(selectedAgentId),
    retry: false,
    refetchInterval: 60_000,
  })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['security-engine'] })
  }

  if (statusQuery.isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className='flex items-center gap-2'>
            <RefreshCw className='h-5 w-5 animate-spin' />
            Checking Wazuh connection
          </CardTitle>
          <CardDescription>
            Cloud-X is validating the configured security-engine connection.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (statusQuery.isError) {
    return (
      <div className='space-y-6'>
        <div>
          <h1 className='text-3xl font-bold tracking-tight'>Wazuh Security</h1>
          <p className='text-muted-foreground'>
            Endpoint monitoring, alerts, SCA and file integrity through Cloud-X.
          </p>
        </div>
        <Alert variant='destructive'>
          <ShieldOff />
          <AlertTitle>Security engine unavailable</AlertTitle>
          <AlertDescription>
            <p>{queryMessage(statusQuery.error)}</p>
            <p>
              Configure the backend WAZUH_API_* settings first. Alert data also
              requires the separate WAZUH_INDEXER_* settings. Cloud-X keeps
              those credentials server-side.
            </p>
          </AlertDescription>
        </Alert>
        <Card>
          <CardHeader>
            <CardTitle>Canonical endpoint onboarding</CardTitle>
            <CardDescription>
              Use the standalone cloudx-security-agent package as the endpoint
              enrollment source of truth; the Flask deployment copies are a
              compatibility path, not a second agent product.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (!statusQuery.data) {
    return null
  }

  const status = statusQuery.data
  const overview = overviewQuery.data

  return (
    <div className='space-y-6'>
      <div className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div>
          <div className='flex items-center gap-2'>
            <ShieldCheck className='h-7 w-7' />
            <h1 className='text-3xl font-bold tracking-tight'>Wazuh Security</h1>
          </div>
          <p className='text-muted-foreground mt-1'>
            Normalized endpoint health, alerts, configuration assessment and
            file integrity from the Cloud-X SecurityEngine adapter.
          </p>
        </div>
        <Button variant='outline' onClick={refresh}>
          <RefreshCw className='mr-2 h-4 w-4' />
          Refresh
        </Button>
      </div>

      <div className='grid gap-4 md:grid-cols-2 xl:grid-cols-4'>
        <Card>
          <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
            <CardTitle className='text-sm font-medium'>Managed endpoints</CardTitle>
            <HardDrive className='text-muted-foreground h-4 w-4' />
          </CardHeader>
          <CardContent>
            <div className='text-3xl font-bold'>{overview?.agents.total ?? '—'}</div>
            <p className='text-muted-foreground text-xs'>
              {overview?.agents.active ?? 0} active ·{' '}
              {overview?.agents.disconnected ?? 0} disconnected
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
            <CardTitle className='text-sm font-medium'>Critical alerts</CardTitle>
            <AlertTriangle className='text-muted-foreground h-4 w-4' />
          </CardHeader>
          <CardContent>
            <div className='text-3xl font-bold'>{overview?.alerts.critical ?? '—'}</div>
            <p className='text-muted-foreground text-xs'>
              {overview?.alerts.high ?? 0} high in the latest bounded sample
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
            <CardTitle className='text-sm font-medium'>Wazuh Manager</CardTitle>
            <Server className='text-muted-foreground h-4 w-4' />
          </CardHeader>
          <CardContent>
            <div className='flex items-center gap-2'>
              <Badge>Connected</Badge>
              {status.manager_version && (
                <span className='text-sm font-medium'>{status.manager_version}</span>
              )}
            </div>
            <p className='text-muted-foreground mt-2 text-xs'>
              {status.manager_host || 'Manager API authenticated'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
            <CardTitle className='text-sm font-medium'>Wazuh Indexer</CardTitle>
            <Activity className='text-muted-foreground h-4 w-4' />
          </CardHeader>
          <CardContent>
            {status.indexer_configured ? (
              <>
                <div className='flex items-center gap-2'>
                  <Badge>{status.indexer_status || 'Connected'}</Badge>
                </div>
                <p className='text-muted-foreground mt-2 text-xs'>
                  Recent alert search enabled
                </p>
              </>
            ) : (
              <>
                <Badge variant='secondary'>Not configured</Badge>
                <p className='text-muted-foreground mt-2 text-xs'>
                  Agent/SCA/FIM remain available; alerts require Indexer access.
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {overviewQuery.isError && (
        <Alert variant='destructive'>
          <AlertTriangle />
          <AlertTitle>Overview refresh failed</AlertTitle>
          <AlertDescription>{queryMessage(overviewQuery.error)}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue='agents'>
        <TabsList className='grid h-auto w-full grid-cols-2 sm:w-fit sm:grid-cols-4'>
          <TabsTrigger value='agents'>Agents</TabsTrigger>
          <TabsTrigger value='alerts'>Alerts</TabsTrigger>
          <TabsTrigger value='sca'>SCA</TabsTrigger>
          <TabsTrigger value='fim'>FIM</TabsTrigger>
        </TabsList>

        <TabsContent value='agents'>
          <Card>
            <CardHeader>
              <CardTitle>Endpoint inventory</CardTitle>
              <CardDescription>
                Connection state and operating-system inventory normalized from
                the Wazuh Manager API.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {agentsQuery.isError ? (
                <Alert variant='destructive'>
                  <AlertTriangle />
                  <AlertTitle>Unable to load agents</AlertTitle>
                  <AlertDescription>{queryMessage(agentsQuery.error)}</AlertDescription>
                </Alert>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Agent</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>IP</TableHead>
                      <TableHead>OS</TableHead>
                      <TableHead>Groups</TableHead>
                      <TableHead>Last seen</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {agents.map((agent) => (
                      <TableRow
                        key={agent.id}
                        className='cursor-pointer'
                        onClick={() => setSelectedAgentId(agent.id)}
                      >
                        <TableCell>
                          <div className='font-medium'>{agent.name}</div>
                          <div className='text-muted-foreground text-xs'>ID {agent.id}</div>
                        </TableCell>
                        <TableCell>{agentStatusBadge(agent.status)}</TableCell>
                        <TableCell>{agent.ip || '—'}</TableCell>
                        <TableCell>
                          {[agent.os.name, agent.os.version].filter(Boolean).join(' ') || '—'}
                        </TableCell>
                        <TableCell>{agent.groups.join(', ') || '—'}</TableCell>
                        <TableCell>{formatTimestamp(agent.last_seen)}</TableCell>
                      </TableRow>
                    ))}
                    {agents.length === 0 && !agentsQuery.isLoading && (
                      <TableRow>
                        <TableCell colSpan={6} className='text-muted-foreground text-center'>
                          No Wazuh agents returned by the Manager.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value='alerts'>
          <Card>
            <CardHeader>
              <CardTitle>Recent security alerts</CardTitle>
              <CardDescription>
                Latest bounded sample from the Wazuh Indexer alert indices.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!status.indexer_configured ? (
                <Alert>
                  <Activity />
                  <AlertTitle>Indexer not configured</AlertTitle>
                  <AlertDescription>
                    Add WAZUH_INDEXER_* backend settings to enable alert search.
                    Manager credentials alone are intentionally not reused.
                  </AlertDescription>
                </Alert>
              ) : alertsQuery.isError ? (
                <Alert variant='destructive'>
                  <AlertTriangle />
                  <AlertTitle>Unable to load alerts</AlertTitle>
                  <AlertDescription>{queryMessage(alertsQuery.error)}</AlertDescription>
                </Alert>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Severity</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Agent</TableHead>
                      <TableHead>Rule / MITRE</TableHead>
                      <TableHead>Time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {alerts.map((alert: SecurityAlert) => (
                      <TableRow key={alert.id || `${alert.rule_id}-${alert.timestamp}`}>
                        <TableCell>{severityBadge(alert.level)}</TableCell>
                        <TableCell className='max-w-[360px] whitespace-normal'>
                          <div className='font-medium'>{alert.description}</div>
                          <div className='text-muted-foreground text-xs'>
                            {alert.location || alert.manager || 'Wazuh'}
                          </div>
                        </TableCell>
                        <TableCell>{alert.agent.name || alert.agent.id || '—'}</TableCell>
                        <TableCell>
                          <div>{alert.rule_id || '—'}</div>
                          <div className='text-muted-foreground text-xs'>
                            {alert.mitre_ids.join(', ') || 'No MITRE mapping'}
                          </div>
                        </TableCell>
                        <TableCell>{formatTimestamp(alert.timestamp)}</TableCell>
                      </TableRow>
                    ))}
                    {alerts.length === 0 && !alertsQuery.isLoading && (
                      <TableRow>
                        <TableCell colSpan={5} className='text-muted-foreground text-center'>
                          No recent alerts in the current sample.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value='sca'>
          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                <FileCheck2 className='h-5 w-5' />
                Security Configuration Assessment
              </CardTitle>
              <CardDescription>
                Policy summaries for a selected Wazuh endpoint.
              </CardDescription>
              <AgentSelector
                agents={agents}
                value={selectedAgentId}
                onChange={setSelectedAgentId}
              />
            </CardHeader>
            <CardContent>
              {scaQuery.isError ? (
                <Alert variant='destructive'>
                  <AlertTriangle />
                  <AlertTitle>Unable to load SCA</AlertTitle>
                  <AlertDescription>{queryMessage(scaQuery.error)}</AlertDescription>
                </Alert>
              ) : (
                <div className='space-y-3'>
                  {scaQuery.data?.map((policy) => (
                    <div key={policy.policy_id} className='rounded-lg border p-4'>
                      <div className='flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between'>
                        <div>
                          <div className='font-medium'>{policy.name}</div>
                          <div className='text-muted-foreground text-xs'>
                            {policy.policy_id} · {formatTimestamp(policy.last_scan)}
                          </div>
                        </div>
                        {policy.score != null && (
                          <Badge variant={policy.score >= 80 ? 'default' : 'secondary'}>
                            Score {policy.score.toFixed(1)}%
                          </Badge>
                        )}
                      </div>
                      <div className='mt-3 grid grid-cols-3 gap-3 text-sm'>
                        <div>
                          <div className='text-muted-foreground text-xs'>Passed</div>
                          <div className='font-semibold'>{policy.passed}</div>
                        </div>
                        <div>
                          <div className='text-muted-foreground text-xs'>Failed</div>
                          <div className='font-semibold'>{policy.failed}</div>
                        </div>
                        <div>
                          <div className='text-muted-foreground text-xs'>Total</div>
                          <div className='font-semibold'>{policy.total}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                  {selectedAgent && scaQuery.data?.length === 0 && (
                    <p className='text-muted-foreground text-sm'>
                      No SCA policy results returned for {selectedAgent.name}.
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value='fim'>
          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                <FileSearch className='h-5 w-5' />
                File Integrity Monitoring
              </CardTitle>
              <CardDescription>
                Recent normalized FIM state for a selected Wazuh endpoint.
              </CardDescription>
              <AgentSelector
                agents={agents}
                value={selectedAgentId}
                onChange={setSelectedAgentId}
              />
            </CardHeader>
            <CardContent>
              {fimQuery.isError ? (
                <Alert variant='destructive'>
                  <AlertTriangle />
                  <AlertTitle>Unable to load FIM</AlertTitle>
                  <AlertDescription>{queryMessage(fimQuery.error)}</AlertDescription>
                </Alert>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Path</TableHead>
                      <TableHead>Owner</TableHead>
                      <TableHead>Changes</TableHead>
                      <TableHead>SHA-256</TableHead>
                      <TableHead>Observed</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {fimQuery.data?.map((record, index) => (
                      <TableRow key={`${record.path}-${record.sha256}-${index}`}>
                        <TableCell className='max-w-[360px] whitespace-normal font-mono text-xs'>
                          {record.path || '—'}
                        </TableCell>
                        <TableCell>
                          {[record.owner, record.group].filter(Boolean).join(':') || '—'}
                        </TableCell>
                        <TableCell>{record.changes}</TableCell>
                        <TableCell className='max-w-[220px] truncate font-mono text-xs'>
                          {record.sha256 || '—'}
                        </TableCell>
                        <TableCell>
                          {formatTimestamp(record.observed_at || record.modified_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                    {selectedAgent && fimQuery.data?.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className='text-muted-foreground text-center'>
                          No FIM records returned for {selectedAgent.name}.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Alert>
        <CheckCircle2 />
        <AlertTitle>Cloud-X owns the product contract</AlertTitle>
        <AlertDescription>
          This page consumes normalized Cloud-X security objects. Wazuh Manager
          and Indexer credentials, JWTs, response envelopes and raw search APIs
          remain server-side behind the SecurityEngine adapter.
        </AlertDescription>
      </Alert>
    </div>
  )
}
