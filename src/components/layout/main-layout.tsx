import { Outlet } from '@tanstack/react-router'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/layout/app-sidebar'
import { Header } from '@/components/layout/header'
import { CommandMenu } from '@/components/command-menu'

export function MainLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <Header fixed>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold">Cloud-X Security</h1>
          </div>
        </Header>
        <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
          <Outlet />
        </div>
      </SidebarInset>
      <CommandMenu />
    </SidebarProvider>
  )
}
