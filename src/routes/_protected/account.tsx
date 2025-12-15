import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_protected/account')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/_protected/account"!</div>
}
