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
  status: 'submitted' | 'running' | 'completed' | 'failed' | 'stopped'
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

class CloudXApiClient {
  private baseURL: string
  private timeout: number

  constructor(
    baseURL: string = import.meta.env.VITE_API_BASE_URL ||
      'http://localhost:5001',
    timeout: number = 30000
  ) {
    this.baseURL = baseURL
    this.timeout = timeout
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), this.timeout)

    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ error: 'Unknown error' }))
        throw new Error(errorData.error || `HTTP ${response.status}`)
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

  // Health and Status
  async checkHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/api/health')
  }

  async ping(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/api/ping')
  }

  async getSyncStatus(): Promise<SyncStatus> {
    return this.request<SyncStatus>('/api/sync-status')
  }

  // Scan Management
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

  // Configuration
  setBaseURL(url: string): void {
    this.baseURL = url
  }

  getBaseURL(): string {
    return this.baseURL
  }
}

// Export singleton instance
export const apiClient = new CloudXApiClient()
export default CloudXApiClient
