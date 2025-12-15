import React, { createContext, useContext, useState, useEffect } from 'react'

export interface ServerNode {
  id: string
  name: string
  url: string
  status: 'active' | 'offline' | 'unknown'
  lastSeen?: number
}

interface ServersContextType {
  servers: ServerNode[]
  activeServerId: string | null
  addServer: (server: Omit<ServerNode, 'id' | 'status'>) => void
  removeServer: (id: string) => void
  setActiveServer: (id: string) => void
  refreshServerStatus: (id: string) => Promise<void>
}

const ServersContext = createContext<ServersContextType | null>(null)

export function ServersProvider({ children }: { children: React.ReactNode }) {
  const [servers, setServers] = useState<ServerNode[]>(() => {
    const saved = localStorage.getItem('cloudx_servers')
    return saved
      ? JSON.parse(saved)
      : [
        {
          id: 'local',
          name: 'Primary Node',
          url: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001',
          status: 'unknown',
        },
      ]
  })

  // Default to first server
  const [activeServerId, setActiveServerId] = useState<string | null>(
    servers[0]?.id || null
  )

  useEffect(() => {
    localStorage.setItem('cloudx_servers', JSON.stringify(servers))
  }, [servers])

  const addServer = (newServer: Omit<ServerNode, 'id' | 'status'>) => {
    const id = crypto.randomUUID()
    setServers((prev) => [...prev, { ...newServer, id, status: 'unknown' }])
  }

  const removeServer = (id: string) => {
    setServers((prev) => prev.filter((s) => s.id !== id))
    if (activeServerId === id) {
      setActiveServerId(servers.find((s) => s.id !== id)?.id || null)
    }
  }

  const setActiveServer = (id: string) => {
    setActiveServerId(id)
    // Here we would ideally update the generic API client to point to this new URL
    // For now, we just track it
  }

  const refreshServerStatus = async (id: string) => {
    const server = servers.find((s) => s.id === id)
    if (!server) return

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000)

      const res = await fetch(`${server.url}/api/health`, {
        signal: controller.signal,
      })
      clearTimeout(timeoutId)

      if (res.ok) {
        setServers((prev) =>
          prev.map((s) =>
            s.id === id ? { ...s, status: 'active', lastSeen: Date.now() } : s
          )
        )
      } else {
        setServers((prev) =>
          prev.map((s) => (s.id === id ? { ...s, status: 'offline' } : s))
        )
      }
    } catch (_e) {
      setServers((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status: 'offline' } : s))
      )
    }
  }

  // Periodically refresh all?
  useEffect(() => {
    const interval = setInterval(() => {
      servers.forEach((s) => refreshServerStatus(s.id))
    }, 30000)
    return () => clearInterval(interval)
  }, [servers.length]) // Just length dep to avoid deep loop, simplified

  return (
    <ServersContext.Provider
      value={{
        servers,
        activeServerId,
        addServer,
        removeServer,
        setActiveServer,
        refreshServerStatus,
      }}
    >
      {children}
    </ServersContext.Provider>
  )
}

export function useServers() {
  const context = useContext(ServersContext)
  if (!context)
    throw new Error('useServers must be used within ServersProvider')
  return context
}
