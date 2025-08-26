import { createFileRoute } from '@tanstack/react-router'
import { NetworkHistory } from '@/components/pages/network/history'

export const Route = createFileRoute('/_protected/apps/network/history')({
  component: NetworkHistory,
})
