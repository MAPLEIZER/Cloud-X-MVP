import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/_protected/apps/network')({
  component: NetworkLayout,
})

function NetworkLayout() {
  return <Outlet />
}
