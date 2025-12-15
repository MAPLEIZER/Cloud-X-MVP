// Navigation Types
export interface NavItem {
  title: string
  href: string
  icon?: React.ComponentType<{ className?: string }>
  children?: NavItem[]
  badge?: string | number
  disabled?: boolean
}

// User Types
export interface User {
  id: string
  name: string
  email: string
  avatar?: string
  role: 'admin' | 'analyst' | 'viewer'
}

// Scan Types (matching backend)
export interface ScanParams {
  target: string
  tool: 'nmap' | 'zmap' | 'masscan'
  scan_type: string
  port?: string
}

export interface ScanResult {
  job_id: string
  tool: string
  target: string
  scan_type: string
  status: 'submitted' | 'running' | 'completed' | 'failed' | 'stopped'
  progress?: number
  results?: unknown
  created_at: string
}

// Dashboard Widget Types
export interface SecurityMetric {
  id: string
  title: string
  value: string | number
  change?: number
  changeType?: 'increase' | 'decrease'
  icon?: React.ComponentType<{ className?: string }>
  color?: 'green' | 'red' | 'yellow' | 'blue'
}

export interface Alert {
  id: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  description: string
  timestamp: string
  source: 'wazuh' | 'network' | 'system'
  acknowledged?: boolean
}

// Wazuh Types
export interface WazuhAgent {
  id: string
  name: string
  ip: string
  status: 'active' | 'disconnected' | 'never_connected'
  os: string
  version: string
  last_keep_alive: string
  group?: string[]
}

export interface WazuhAlert extends Alert {
  agent_id?: string
  rule_id: number
  rule_description: string
  rule_level: number
  location?: string
  full_log?: string
}

// Network Types
export interface NetworkHost {
  ip: string
  hostname?: string
  ports: NetworkPort[]
  os?: string
  status: 'up' | 'down' | 'unknown'
}

export interface NetworkPort {
  port: number
  protocol: 'tcp' | 'udp'
  state: 'open' | 'closed' | 'filtered'
  service?: string
  version?: string
  vulnerability?: string[]
}

// Settings Types
export interface AppSettings {
  apiEndpoint: string
  notifications: boolean
  autoRefresh: boolean
  theme: 'light' | 'dark' | 'system'
  wazuhApiUrl?: string
  wazuhApiKey?: string
  refreshInterval: number
}

// API Response Types
export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number
    limit: number
    total: number
    totalPages: number
  }
}

// Chart Data Types
export interface ChartDataPoint {
  name: string
  value: number
  timestamp?: string
}

export interface TimeSeriesData {
  timestamp: string
  value: number
  label?: string
}

// File/Download Types
export interface DownloadItem {
  id: string
  filename: string
  size: number
  type: 'report' | 'tool' | 'patch' | 'script'
  uploadedBy: string
  uploadedAt: string
  downloadCount: number
  description?: string
  tags?: string[]
}

// Script/Automation Types
export interface Script {
  id: string
  name: string
  description: string
  type: 'bash' | 'python' | 'powershell'
  content: string
  parameters?: ScriptParameter[]
  createdBy: string
  createdAt: string
  lastRun?: string
  status: 'active' | 'disabled' | 'deprecated'
}

export interface ScriptParameter {
  name: string
  type: 'string' | 'number' | 'boolean' | 'select'
  required: boolean
  default?: string | number | boolean
  options?: string[]
  description?: string
}

// Billing Types
export interface BillingPlan {
  id: string
  name: string
  price: number
  interval: 'month' | 'year'
  features: string[]
  limits: {
    agents: number
    scans: number
    storage: number // in GB
  }
}

export interface Usage {
  agents: number
  scans: number
  storage: number
  period: string
}

export interface Invoice {
  id: string
  amount: number
  currency: string
  status: 'paid' | 'pending' | 'failed'
  date: string
  dueDate: string
  downloadUrl?: string
}
