import { Wifi, WifiOff, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useConnection } from '@/hooks/use-connection'

interface ConnectionStatusProps {
  className?: string
  showText?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export function ConnectionStatus({
  className,
  showText = true,
  size = 'md',
}: ConnectionStatusProps) {
  const { isConnected, isChecking, checkConnection, lastChecked } =
    useConnection()

  const sizeClasses = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  }

  const getStatusColor = () => {
    if (isChecking) return 'text-gray-500'
    if (isConnected === true) return 'text-green-600'
    if (isConnected === false) return 'text-red-600'
    return 'text-gray-400'
  }

  const getStatusBg = () => {
    if (isChecking) return 'bg-gray-100'
    if (isConnected === true) return 'bg-green-100'
    if (isConnected === false) return 'bg-red-100'
    return 'bg-gray-50'
  }

  const getStatusText = () => {
    if (isChecking) return 'Checking...'
    if (isConnected === true) return 'Connected'
    if (isConnected === false) return 'Disconnected'
    return 'Unknown'
  }

  const getIcon = () => {
    if (isChecking)
      return <Loader2 className={cn(sizeClasses[size], 'animate-spin')} />
    if (isConnected === true) return <Wifi className={sizeClasses[size]} />
    return <WifiOff className={sizeClasses[size]} />
  }

  return (
    <div
      className={cn(
        'flex cursor-pointer items-center gap-2 rounded-full px-3 py-2 text-sm font-medium transition-colors',
        getStatusColor(),
        getStatusBg(),
        className
      )}
      onClick={checkConnection}
      title={
        lastChecked
          ? `Last checked: ${lastChecked.toLocaleTimeString()}`
          : 'Click to check connection'
      }
    >
      {getIcon()}
      {showText && <span>{getStatusText()}</span>}
    </div>
  )
}
