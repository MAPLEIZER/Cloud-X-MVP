import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/_protected/apps')({
  component: AppsLayout,
})

function AppsLayout() {
  return <Outlet />
}
