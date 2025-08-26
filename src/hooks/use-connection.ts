import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/lib/api-client';

interface ConnectionState {
  isConnected: boolean | null;
  isChecking: boolean;
  lastChecked: Date | null;
  error: string | null;
}

export function useConnection() {
  const [state, setState] = useState<ConnectionState>({
    isConnected: null,
    isChecking: false,
    lastChecked: null,
    error: null,
  });

  const checkConnection = useCallback(async () => {
    setState(prev => ({ ...prev, isChecking: true, error: null }));
    
    try {
      await apiClient.checkHealth();
      setState(prev => ({
        ...prev,
        isConnected: true,
        isChecking: false,
        lastChecked: new Date(),
        error: null,
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        isConnected: false,
        isChecking: false,
        lastChecked: new Date(),
        error: error instanceof Error ? error.message : 'Connection failed',
      }));
    }
  }, []);

  // Auto-check connection on mount and periodically
  useEffect(() => {
    checkConnection();
    
    const interval = setInterval(checkConnection, 30000); // Check every 30 seconds
    
    return () => clearInterval(interval);
  }, [checkConnection]);

  return {
    ...state,
    checkConnection,
  };
}
