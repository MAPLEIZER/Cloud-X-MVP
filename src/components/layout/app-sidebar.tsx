import { useState } from 'react'
import { useLocation, Link } from '@tanstack/react-router'
import { 
  LayoutDashboard, 
  Network, 
  Download, 
  Shield, 
  Settings2, 
  Settings, 
  BookOpen, 
  CreditCard,
  ChevronDown,
  ChevronRight,
  History,
  Scan
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { 
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter
} from '@/components/ui/sidebar'
import { ConnectionStatus } from '@/components/custom/connection-status'
import { NavUser } from '@/components/layout/nav-user'

const navigationItems = [
  {
    title: 'Dashboard',
    url: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: 'Apps',
    icon: Settings2,
    items: [
      {
        title: 'Network',
        icon: Network,
        items: [
          {
            title: 'Scan',
            url: '/apps/network/scan',
            icon: Scan,
          },
          {
            title: 'History',
            url: '/apps/network/history',
            icon: History,
          },
        ],
      },
      {
        title: 'Downloads',
        url: '/apps/downloads',
        icon: Download,
      },
      {
        title: 'Wazuh',
        url: '/apps/wazuh',
        icon: Shield,
      },
      {
        title: 'Advanced',
        url: '/apps/advanced',
        icon: Settings2,
      },
    ],
  },
  {
    title: 'Settings',
    url: '/settings',
    icon: Settings,
  },
  {
    title: 'Documentation',
    url: '/documentation',
    icon: BookOpen,
  },
  {
    title: 'Billing',
    url: '/billing',
    icon: CreditCard,
  },
]

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const location = useLocation()
  const [expandedItems, setExpandedItems] = useState<string[]>(['Apps'])

  const toggleExpanded = (title: string) => {
    setExpandedItems(prev => 
      prev.includes(title) 
        ? prev.filter(item => item !== title)
        : [...prev, title]
    )
  }

  const isActive = (url: string) => {
    return location.pathname === url || location.pathname.startsWith(url + '/')
  }

  const renderMenuItem = (item: typeof navigationItems[0], level = 0) => {
    const hasSubItems = item.items && item.items.length > 0
    const isExpanded = expandedItems.includes(item.title)
    const isItemActive = item.url ? isActive(item.url) : false

    if (hasSubItems) {
      return (
        <SidebarMenuItem key={item.title}>
          <SidebarMenuButton
            onClick={() => toggleExpanded(item.title)}
            className={cn(
              'w-full justify-between',
              level > 0 && 'ml-4'
            )}
          >
            <div className="flex items-center">
              {item.icon && <item.icon className="mr-2 h-4 w-4" />}
              <span>{item.title}</span>
            </div>
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </SidebarMenuButton>
          {isExpanded && (
            <div className="ml-4 space-y-1">
              {item.items?.map((subItem) => (
                <div key={subItem.title}>
                  {renderMenuItem(subItem, level + 1)}
                </div>
              ))}
            </div>
          )}
        </SidebarMenuItem>
      )
    }

    if (item.url) {
      return (
        <SidebarMenuItem key={item.title}>
          <SidebarMenuButton asChild isActive={isItemActive}>
            <Link to={item.url} className={cn(level > 1 && 'ml-4')}>
              {item.icon && <item.icon className="mr-2 h-4 w-4" />}
              <span>{item.title}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      )
    }

    return null
  }

  return (
    <Sidebar {...props} className="border-r">
      <SidebarHeader className="border-b px-4 py-4">
        <div className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-blue-600" />
          <span className="font-bold text-lg">Cloud-X</span>
        </div>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navigationItems.map((item) => renderMenuItem(item))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t p-4">
        <div className="space-y-3">
          <ConnectionStatus size="sm" />
          <NavUser />
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
