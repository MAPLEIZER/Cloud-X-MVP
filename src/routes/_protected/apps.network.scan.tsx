import { createFileRoute } from '@tanstack/react-router'
import { NetworkScan } from '@/components/pages/network/scan'

export const Route = createFileRoute('/_protected/apps/network/scan')({
  component: NetworkScan,
})
