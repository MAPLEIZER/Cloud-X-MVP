import { createFileRoute } from '@tanstack/react-router'
import { ComingSoon } from '@/components/coming-soon'

export const Route = createFileRoute('/_protected/apps/wazuh')({
  component: ComingSoon,
})
