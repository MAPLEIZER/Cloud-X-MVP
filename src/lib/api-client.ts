// API Response Types
export interface ScanParams {
  target: string
  tool: 'nmap' | 'zmap' | 'masscan'
  scan_type: string
  port?: string
}

export interface ScanResponse {
  job_id: string
  status: string
}

export interface ScanStatus {
  job_id: string
  tool: string
  target: string
  scan_type: string
  status:
    | 'submitted'
    | 'queued'
    | 'running'
    | 'stopping'
    | 'completed'
    | 'failed'
    | 'stopped'
  progress?: number
  results?: Record<string, unknown>
  created_at: string
}

export interface HealthStatus {
  status: 'ok' | 'error'
}

export interface SyncStatus {
  status: 'active' | 'inactive' | 'error'
  reason?: string
}

export interface SecurityEngineStatus {
  provider: 'wazuh'
  manager_connected: boolean
  manager_version?: string | null
  manager_host?: string | null
  indexer_configured: boolean
  indexer_status?: string | null
}

export interface SecurityOverview {
  provider: 'wazuh'
  agents: {
    total: number
    active: number
    disconnected: number
  }
  alerts: {
    sample_size: number
    critical: number
    high: number
    latest_at?: string | null
    available: boolean
  }
}

export interface SecurityAgent {
  id: string
  name: string
  ip?: string | null
  status: string
  groups: string[]
  version?: string | null
  node?: string | null
  last_seen?: string | null
  os: {
    name?: string | null
    version?: string | null
    platform?: string | null
    arch?: string | null
  }
}

export interface SecurityAlert {
  id: string
  timestamp?: string | null
  level: number
  rule_id: string
  description: string
  groups: string[]
  mitre_ids: string[]
  agent: {
    id: string
    name?: string | null
    ip?: string | null
  }
  manager?: string | null
  location?: string | null
}

export interface SecurityScaPolicy {
  policy_id: string
  name: string
  description?: string | null
  passed: number
  failed: number
  invalid: number
  total: number
  score?: number | null
  last_scan?: string | null
}

export interface SecurityFimRecord {
  path?: string | null
  type?: string | null
  size?: number | null
  permissions?: string | null
  owner?: string | null
  group?: string | null
  sha256?: string | null
  changes: number
  modified_at?: string | null
  observed_at?: string | null
}

type TokenProvider = () => Promise<string | null>

export class CloudXApiError extends Error {
  status: number
  code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'CloudXApiError'
    this.status = status
    this.code = code
  }
}

class CloudXApiClient {
  private baseURL: string
  private timeout: number
  private tokenProvider: TokenProvider | null = null

  constructor(
    baseURL: string = import.meta.env.VITE_API_BASE_URL ||
      'http://localhost:5001',
    timeout: number = 30000
  ) {
    this.baseURL = baseURL
    this.timeout = timeout
  }

  setTokenProvider(provider: TokenProvider | null): void {
    this.tokenProvider = provider
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), this.timeout)

    try {
      const headers = new Headers(options.headers)

      if (options.body && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json')
      }

      if (this.tokenProvider) {
        const token = await this.tokenProvider()
        if (token) {
          headers.set('Authorization', `Bearer ${token}`)
        }
      }

      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        headers,
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorData = (await response.json().catch(() => ({
          error: 'Unknown error',
        }))) as { error?: string; code?: string }
        throw new CloudXApiError(
          errorData.error || `HTTP ${response.status}`,
          response.status,
          errorData.code
        )
      }

      return await response.json()
    } catch (error) {
      clearTimeout(timeoutId)
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error('Request timeout')
        }
        throw error
      }
      throw new Error('Unknown error occurred')
    }
  }

  async checkHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/api/health')
  }

  async ping(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/api/ping')
  }

  async getSyncStatus(): Promise<SyncStatus> {
    return this.request<SyncStatus>('/api/sync-status')
  }

  async startScan(params: ScanParams): Promise<ScanResponse> {
    return this.request<ScanResponse>('/api/scans', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }

  async getScanStatus(jobId: string): Promise<ScanStatus> {
    return this.request<ScanStatus>(`/api/scans/${jobId}`)
  }

  async stopScan(jobId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/scans/${jobId}/stop`, {
      method: 'POST',
    })
  }

  async deleteScan(jobId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/scans/${jobId}`, {
      method: 'DELETE',
    })
  }

  async getScanHistory(): Promise<ScanStatus[]> {
    return this.request<ScanStatus[]>('/api/scans')
  }

  async getSecurityStatus(): Promise<SecurityEngineStatus> {
    return this.request<SecurityEngineStatus>('/api/security/status')
  }

  async getSecurityOverview(): Promise<SecurityOverview> {
    return this.request<SecurityOverview>('/api/security/overview')
  }

  async getSecurityAgents(limit: number = 100): Promise<SecurityAgent[]> {
    return this.request<SecurityAgent[]>(`/api/security/agents?limit=${limit}`)
  }

  async getSecurityAlerts(limit: number = 50): Promise<SecurityAlert[]> {
    return this.request<SecurityAlert[]>(`/api/security/alerts?limit=${limit}`)
  }

  async getSecuritySca(
    agentId: string,
    limit: number = 100
  ): Promise<SecurityScaPolicy[]> {
    return this.request<SecurityScaPolicy[]>(
      `/api/security/sca?agent_id=${encodeURIComponent(agentId)}&limit=${limit}`
    )
  }

  async getSecurityFim(
    agentId: string,
    limit: number = 100
  ): Promise<SecurityFimRecord[]> {
    return this.request<SecurityFimRecord[]>(
      `/api/security/fim?agent_id=${encodeURIComponent(agentId)}&limit=${limit}`
    )
  }

  setBaseURL(url: string): void {
    this.baseURL = url
  }

  getBaseURL(): string {
    return this.baseURL
  }
}

export const apiClient = new CloudXApiClient()
export default CloudXApiClient
