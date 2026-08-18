import { useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { apiClient } from '@/lib/api-client'
import { installClientErrorReporting } from '@/lib/error-reporting'

export function ApiAuthBridge() {
  const { getToken, isLoaded } = useAuth()

  useEffect(() => {
    if (!isLoaded) {
      return
    }

    apiClient.setTokenProvider(() => getToken())
    const uninstallErrorReporting = installClientErrorReporting()

    return () => {
      uninstallErrorReporting()
      apiClient.setTokenProvider(null)
    }
  }, [getToken, isLoaded])

  return null
}
