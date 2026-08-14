import { useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { apiClient } from '@/lib/api-client'

export function ApiAuthBridge() {
  const { getToken, isLoaded } = useAuth()

  useEffect(() => {
    if (!isLoaded) {
      return
    }

    apiClient.setTokenProvider(() => getToken())

    return () => {
      apiClient.setTokenProvider(null)
    }
  }, [getToken, isLoaded])

  return null
}
