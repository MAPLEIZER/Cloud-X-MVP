import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Settings as SettingsIcon, Save, Server, Bell, Palette } from 'lucide-react'
import { CloudXLogo } from '@/assets/cloud-x-logo'
import { useApp } from '@/context/app-context'
import { useTheme } from '@/context/theme-provider'
import { toast } from 'sonner'

export function Settings() {
  const { state, updateSettings } = useApp()
  const { theme, setTheme: setAppTheme } = useTheme()
  const [apiUrl, setApiUrl] = useState(state.settings.apiBaseUrl)
  const [autoConnect, setAutoConnect] = useState(state.settings.autoConnect)
  const [scanNotifications, setScanNotifications] = useState(state.settings.notifications.scanComplete)
  const [alertNotifications, setAlertNotifications] = useState(state.settings.notifications.securityAlerts)
  const [systemNotifications, setSystemNotifications] = useState(state.settings.notifications.systemStatus)
  const [refreshInterval, setRefreshInterval] = useState(state.settings.refreshInterval.toString())

  const handleSave = () => {
    updateSettings({
      apiBaseUrl: apiUrl,
      autoConnect,
      notifications: {
        scanComplete: scanNotifications,
        securityAlerts: alertNotifications,
        systemStatus: systemNotifications,
      },
      refreshInterval: parseInt(refreshInterval),
    })
    toast.success('Settings saved successfully!')
  }

  const handleThemeChange = (newTheme: string) => {
    setAppTheme(newTheme as 'light' | 'dark' | 'system')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SettingsIcon className="h-6 w-6" />
          <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        </div>
        <CloudXLogo className="h-6 w-auto" width={24} height={24} />
      </div>

      {/* API Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            Backend Configuration
          </CardTitle>
          <CardDescription>
            Configure your backend API connection and sync settings
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="api-url">Backend API URL</Label>
            <Input
              id="api-url"
              placeholder="http://192.168.100.37:5001"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              The URL of your Cloud-X Flask backend server
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Switch 
              id="auto-connect" 
              checked={autoConnect}
              onCheckedChange={setAutoConnect}
            />
            <Label htmlFor="auto-connect">Auto-connect on startup</Label>
          </div>
          <div className="space-y-2">
            <Label htmlFor="refresh-interval">Data Refresh Interval (seconds)</Label>
            <Select value={refreshInterval} onValueChange={setRefreshInterval}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5">5 seconds</SelectItem>
                <SelectItem value="10">10 seconds</SelectItem>
                <SelectItem value="30">30 seconds</SelectItem>
                <SelectItem value="60">1 minute</SelectItem>
                <SelectItem value="300">5 minutes</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Notifications
          </CardTitle>
          <CardDescription>
            Manage your notification preferences for scans and alerts
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Switch 
              id="scan-notifications" 
              checked={scanNotifications}
              onCheckedChange={setScanNotifications}
            />
            <Label htmlFor="scan-notifications">Network scan completion notifications</Label>
          </div>
          <div className="flex items-center space-x-2">
            <Switch 
              id="alert-notifications" 
              checked={alertNotifications}
              onCheckedChange={setAlertNotifications}
            />
            <Label htmlFor="alert-notifications">Security alert notifications</Label>
          </div>
          <div className="flex items-center space-x-2">
            <Switch 
              id="system-notifications" 
              checked={systemNotifications}
              onCheckedChange={setSystemNotifications}
            />
            <Label htmlFor="system-notifications">System status notifications</Label>
          </div>
        </CardContent>
      </Card>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Appearance
          </CardTitle>
          <CardDescription>
            Customize the look and feel of the dashboard
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="theme">Theme</Label>
            <Select value={theme} onValueChange={handleThemeChange}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="dark">Dark</SelectItem>
                <SelectItem value="system">System</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} className="flex items-center gap-2">
          <Save className="h-4 w-4" />
          Save Settings
        </Button>
      </div>
    </div>
  )
}
