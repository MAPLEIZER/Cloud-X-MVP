export interface CloudXRuntimeConfig {
  apiBaseUrl?: string
  clerkPublishableKey?: string
}

declare global {
  interface Window {
    __CLOUDX_CONFIG__?: CloudXRuntimeConfig
  }
}

function runtimeConfig(): CloudXRuntimeConfig {
  if (typeof window === 'undefined') return {}
  return window.__CLOUDX_CONFIG__ ?? {}
}

export function getApiBaseUrl(): string {
  const configured = runtimeConfig().apiBaseUrl
  if (configured !== undefined) return configured
  if (import.meta.env.VITE_API_BASE_URL !== undefined) {
    return import.meta.env.VITE_API_BASE_URL
  }
  return import.meta.env.PROD ? '' : 'http://localhost:5001'
}

export function getClerkPublishableKey(): string | undefined {
  return (
    runtimeConfig().clerkPublishableKey ??
    import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
  )
}
