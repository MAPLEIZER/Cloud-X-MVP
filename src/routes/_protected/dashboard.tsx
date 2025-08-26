import { createFileRoute } from '@tanstack/react-router'
import { Dashboard } from '@/components/pages/dashboard'

export const Route = createFileRoute('/_protected/dashboard')({
  component: Dashboard,
})
