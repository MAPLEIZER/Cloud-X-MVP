import { createFileRoute, Navigate } from '@tanstack/react-router'

export const Route = createFileRoute('/_protected/')({
  component: () => <Navigate to='/dashboard' />,
})
