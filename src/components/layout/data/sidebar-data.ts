import {
  LayoutDashboard,
  Network,
  Download,
  Shield,
  Settings,
  FileText,
  CreditCard,
  History,
  Search,
  Activity,
} from 'lucide-react'
import { CloudXLogo } from '@/assets/cloud-x-logo'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: 'Cloud-X Admin',
    email: 'admin@cloudx-security.com',
    avatar: '/avatars/cloudx-admin.jpg',
  },
  teams: [
    {
      name: 'Cloud-X Security',
      logo: CloudXLogo,
      plan: 'Enterprise',
    },
  ],
  navGroups: [
    {
      title: 'Main',
      items: [
        {
          title: 'Dashboard',
          url: '/',
          icon: LayoutDashboard,
        },
        {
          title: 'Network',
          icon: Network,
          items: [
            {
              title: 'Scan',
              url: '/network/scan',
              icon: Search,
            },
            {
              title: 'History',
              url: '/network/history',
              icon: History,
            },
          ],
        },
        {
          title: 'Downloads',
          url: '/downloads',
          icon: Download,
        },
        {
          title: 'Wazuh',
          url: '/wazuh',
          icon: Shield,
        },
        {
          title: 'Advanced',
          url: '/advanced',
          icon: Activity,
        },
      ],
    },
    {
      title: 'Configuration',
      items: [
        {
          title: 'Settings',
          url: '/settings',
          icon: Settings,
        },
        {
          title: 'Documentation',
          url: '/documentation',
          icon: FileText,
        },
        {
          title: 'Billing',
          url: '/billing',
          icon: CreditCard,
        },
      ],
    },
  ],
}
