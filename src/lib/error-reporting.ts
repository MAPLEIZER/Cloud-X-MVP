import { apiClient, type ClientErrorReport } from '@/lib/api-client'

const SECRET_VALUE_RE =
  /\b(password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*([^\s,;]+)/gi
const BEARER_RE = /\bBearer\s+[A-Za-z0-9._~+/=-]+/gi
const URL_QUERY_RE = /(https?:\/\/[^\s?#)]+)\?[^\s)]+/gi

function redact(value: string, maximum: number): string {
  return value
    .replace(BEARER_RE, 'Bearer [REDACTED]')
    .replace(SECRET_VALUE_RE, '$1=[REDACTED]')
    .replace(URL_QUERY_RE, '$1?[REDACTED]')
    .slice(0, maximum)
}

function currentPath(): string {
  return window.location.pathname.slice(0, 1024)
}

function normalizeError(value: unknown): Pick<ClientErrorReport, 'name' | 'message' | 'stack'> {
  if (value instanceof Error) {
    return {
      name: redact(value.name || 'Error', 128),
      message: redact(value.message || 'Frontend runtime error', 2048),
      stack: value.stack ? redact(value.stack, 12000) : undefined,
    }
  }

  return {
    name: 'UnhandledValue',
    message: redact(String(value), 2048),
  }
}

function submit(payload: ClientErrorReport): void {
  // Never create a second unhandled rejection when the telemetry endpoint itself
  // is unavailable, unauthenticated or intentionally disabled in development.
  void apiClient.reportClientError(payload).catch(() => undefined)
}

export function installClientErrorReporting(): () => void {
  const onError = (event: ErrorEvent) => {
    const normalized = normalizeError(event.error ?? event.message)
    submit({
      ...normalized,
      source: 'window.error',
      path: currentPath(),
      line: Number.isInteger(event.lineno) ? event.lineno : undefined,
      column: Number.isInteger(event.colno) ? event.colno : undefined,
    })
  }

  const onUnhandledRejection = (event: PromiseRejectionEvent) => {
    const normalized = normalizeError(event.reason)
    submit({
      ...normalized,
      source: 'unhandledrejection',
      path: currentPath(),
    })
  }

  window.addEventListener('error', onError)
  window.addEventListener('unhandledrejection', onUnhandledRejection)

  return () => {
    window.removeEventListener('error', onError)
    window.removeEventListener('unhandledrejection', onUnhandledRejection)
  }
}
