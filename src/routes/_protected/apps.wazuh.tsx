import { createFileRoute } from '@tanstack/react-router'
import { WazuhDashboard } from '@/components/pages/wazuh-dashboard'

export const Route = createFileRoute('/_protected/apps/wazuh')({
  component: WazuhDashboard,
})
