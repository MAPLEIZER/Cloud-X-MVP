import React, {
  createContext,
  useContext,
  useReducer,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'
import { apiClient, type ScanStatus, type ScanParams } from '@/lib/api-client'

// State Types
interface AppState {
  isConnected: boolean | null
  scans: ScanStatus[]
  activeScan: ScanStatus | null
  settings: {
    apiBaseUrl: string
    autoConnect: boolean
    notifications: {
      scanComplete: boolean
      securityAlerts: boolean
      systemStatus: boolean
    }
    refreshInterval: number
  }
  loading: {
    scans: boolean
    connection: boolean
  }
  error: string | null
}

// Action Types
type AppAction =
  | { type: 'SET_CONNECTION_STATUS'; payload: boolean | null }
  | { type: 'SET_SCANS'; payload: ScanStatus[] }
  | { type: 'ADD_SCAN'; payload: ScanStatus }
  | { type: 'UPDATE_SCAN'; payload: ScanStatus }
  | { type: 'SET_ACTIVE_SCAN'; payload: ScanStatus | null }
  | { type: 'SET_SETTINGS'; payload: Partial<AppState['settings']> }
  | {
    type: 'SET_LOADING'
    payload: { key: keyof AppState['loading']; value: boolean }
  }
  | { type: 'SET_ERROR'; payload: string | null }

// Initial State
const initialState: AppState = {
  isConnected: null,
  scans: [],
  activeScan: null,
  settings: {
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001',
    autoConnect: true,
    notifications: {
      scanComplete: true,
      securityAlerts: true,
      systemStatus: false,
    },
    refreshInterval: 10,
  },
  loading: {
    scans: false,
    connection: false,
  },
  error: null,
}

// Reducer
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_CONNECTION_STATUS':
      return { ...state, isConnected: action.payload }

    case 'SET_SCANS':
      return { ...state, scans: action.payload }

    case 'ADD_SCAN':
      return { ...state, scans: [action.payload, ...state.scans] }

    case 'UPDATE_SCAN':
      return {
        ...state,
        scans: state.scans.map((scan) =>
          scan.job_id === action.payload.job_id ? action.payload : scan
        ),
        activeScan:
          state.activeScan?.job_id === action.payload.job_id
            ? action.payload
            : state.activeScan,
      }

    case 'SET_ACTIVE_SCAN':
      return { ...state, activeScan: action.payload }

    case 'SET_SETTINGS': {
      const newSettings = { ...state.settings, ...action.payload }
      // Persist to localStorage
      localStorage.setItem('cloudx-settings', JSON.stringify(newSettings))
      // Update API client base URL if changed
      if (action.payload.apiBaseUrl) {
        apiClient.setBaseURL(action.payload.apiBaseUrl)
      }
      return { ...state, settings: newSettings }
    }

    case 'SET_LOADING':
      return {
        ...state,
        loading: {
          ...state.loading,
          [action.payload.key]: action.payload.value,
        },
      }

    case 'SET_ERROR':
      return { ...state, error: action.payload }

    default:
      return state
  }
}

// Context
interface AppContextType {
  state: AppState
  dispatch: React.Dispatch<AppAction>
  // Helper functions
  checkConnection: () => Promise<void>
  fetchScans: () => Promise<void>
  startScan: (params: ScanParams) => Promise<string>
  stopScan: (jobId: string) => Promise<void>
  deleteScan: (jobId: string) => Promise<void>
  updateSettings: (settings: Partial<AppState['settings']>) => void
}

const AppContext = createContext<AppContextType | undefined>(undefined)

// Provider Component
interface AppProviderProps {
  children: ReactNode
}

export function AppProvider({ children }: AppProviderProps) {
  const [state, dispatch] = useReducer(appReducer, initialState)

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedSettings = localStorage.getItem('cloudx-settings')
    if (savedSettings) {
      try {
        const settings = JSON.parse(savedSettings)
        dispatch({ type: 'SET_SETTINGS', payload: settings })
      } catch (_error) {
        // Failed to load settings from localStorage - use defaults
      }
    }
  }, [])

  // Helper Functions
  const checkConnection = async () => {
    dispatch({
      type: 'SET_LOADING',
      payload: { key: 'connection', value: true },
    })
    try {
      await apiClient.checkHealth()
      dispatch({ type: 'SET_CONNECTION_STATUS', payload: true })
      dispatch({ type: 'SET_ERROR', payload: null })
    } catch (error) {
      dispatch({ type: 'SET_CONNECTION_STATUS', payload: false })
      dispatch({
        type: 'SET_ERROR',
        payload: error instanceof Error ? error.message : 'Connection failed',
      })
    } finally {
      dispatch({
        type: 'SET_LOADING',
        payload: { key: 'connection', value: false },
      })
    }
  }

  const fetchScans = useCallback(async () => {
    if (!state.isConnected) return

    dispatch({ type: 'SET_LOADING', payload: { key: 'scans', value: true } })
    try {
      const scans = await apiClient.getScanHistory()
      dispatch({ type: 'SET_SCANS', payload: scans })
      dispatch({ type: 'SET_ERROR', payload: null })
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        payload:
          error instanceof Error ? error.message : 'Failed to fetch scans',
      })
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { key: 'scans', value: false } })
    }
  }, [state.isConnected])

  // Auto-refresh scans when enabled
  useEffect(() => {
    if (!state.isConnected) return

    const interval = setInterval(() => {
      fetchScans()
    }, state.settings.refreshInterval * 1000)

    return () => clearInterval(interval)
  }, [state.isConnected, state.settings.refreshInterval, fetchScans])

  const startScan = async (params: ScanParams): Promise<string> => {
    try {
      const response = await apiClient.startScan(params)
      // Fetch updated scans list
      fetchScans()
      return response.job_id
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to start scan'
      dispatch({ type: 'SET_ERROR', payload: errorMessage })
      throw error
    }
  }

  const stopScan = async (jobId: string) => {
    try {
      await apiClient.stopScan(jobId)
      // Fetch updated scans list
      fetchScans()
      dispatch({ type: 'SET_ERROR', payload: null })
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        payload: error instanceof Error ? error.message : 'Failed to stop scan',
      })
      throw error
    }
  }

  const deleteScan = async (jobId: string) => {
    try {
      await apiClient.deleteScan(jobId)
      // Fetch updated scans list
      fetchScans()
      dispatch({ type: 'SET_ERROR', payload: null })
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        payload:
          error instanceof Error ? error.message : 'Failed to delete scan',
      })
      throw error
    }
  }

  const updateSettings = (settings: Partial<AppState['settings']>) => {
    dispatch({ type: 'SET_SETTINGS', payload: settings })
  }

  // Check connection on mount
  useEffect(() => {
    checkConnection()
  }, [])

  const contextValue: AppContextType = {
    state,
    dispatch,
    checkConnection,
    fetchScans,
    startScan,
    stopScan,
    deleteScan,
    updateSettings,
  }

  return (
    <AppContext.Provider value={contextValue}>{children}</AppContext.Provider>
  )
}

// Custom Hook
export function useApp() {
  const context = useContext(AppContext)
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider')
  }
  return context
}

export default AppContext
