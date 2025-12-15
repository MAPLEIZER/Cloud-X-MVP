# Cloud-X Frontend Documentation

This document provides an overview of the Cloud-X Security Dashboard frontend architecture, components, and development workflow.

## Tech Stack

| Technology | Purpose |
|------------|---------|
| **Vite** | Build tool and development server |
| **React 19** | UI framework |
| **TypeScript** | Type-safe JavaScript |
| **TailwindCSS 4** | Utility-first CSS framework |
| **TanStack Router** | File-based routing with automatic code splitting |
| **TanStack Query** | Server state management and data fetching |
| **Zustand** | Client-side state management |
| **ShadcnUI / Radix** | Accessible UI component primitives |
| **Recharts** | Data visualization |
| **Framer Motion** | Animations |

---

## Project Structure

```
src/
├── assets/             # Static assets (images, icons)
├── components/
│   ├── auth/           # Authentication-related components (SignIn, SignUp)
│   ├── custom/         # Custom reusable components
│   ├── layout/         # Layout components (Sidebar, Header, AppShell)
│   ├── pages/          # Page-specific components
│   ├── skeletons/      # Loading skeleton components
│   └── ui/             # ShadcnUI base components (Button, Card, Input, etc.)
├── config/             # Application configuration
├── context/            # React Context providers
│   ├── app-context.tsx       # Main application state
│   ├── theme-provider.tsx    # Dark/light theme management
│   ├── servers-context.tsx   # Server/node management
│   └── ...
├── hooks/              # Custom React hooks
├── lib/
│   ├── api-client.ts   # Backend API client (fetch-based)
│   ├── cookies.ts      # Cookie utilities
│   └── utils.ts        # General utilities (cn for classnames)
├── pages/              # Legacy page components (being migrated to routes)
├── routes/             # TanStack Router file-based routes
│   ├── __root.tsx      # Root layout
│   ├── _protected.tsx  # Protected route wrapper
│   ├── _protected/     # Protected child routes
│   │   ├── dashboard.tsx
│   │   ├── apps.network.scan.tsx
│   │   ├── apps.network.history.tsx
│   │   ├── apps.wazuh.tsx
│   │   ├── servers.tsx
│   │   └── ...
│   ├── sign-in.tsx
│   └── sign-up.tsx
├── stores/             # Zustand stores for client state
├── styles/             # Global CSS styles
├── types/              # TypeScript type definitions
└── utils/              # Utility functions
```

---

## Routing

Cloud-X uses **TanStack Router** with file-based routing and automatic code splitting.

### Route Structure

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `_protected/index.tsx` | Redirects to dashboard |
| `/dashboard` | `_protected/dashboard.tsx` | Main dashboard overview |
| `/apps/network/scan` | `_protected/apps.network.scan.tsx` | Network scanning interface |
| `/apps/network/history` | `_protected/apps.network.history.tsx` | Scan history and results |
| `/apps/wazuh` | `_protected/apps.wazuh.tsx` | Wazuh agent management |
| `/servers` | `_protected/servers.tsx` | Server/node management |
| `/settings` | `_protected/settings.tsx` | User settings |
| `/sign-in` | `sign-in.tsx` | Authentication page |
| `/sign-up` | `sign-up.tsx` | Registration page |

### Protected Routes

Routes under `_protected/` require authentication. The `_protected.tsx` component wraps these routes with an auth check.

---

## API Client

The frontend communicates with the Flask backend via a custom API client located at `src/lib/api-client.ts`.

### Configuration

```typescript
// Default configuration
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';
```

Set `VITE_API_BASE_URL` in your `.env.local` file to point to your backend:

```env
VITE_API_BASE_URL=http://your-backend-ip:5001
```

### Available Methods

| Method | Endpoint | Description |
|--------|----------|-------------|
| `checkHealth()` | `GET /api/health` | Check backend health |
| `ping()` | `GET /api/ping` | Simple connectivity check |
| `getSyncStatus()` | `GET /api/sync-status` | Check file sync status |
| `startScan(params)` | `POST /api/scans` | Start a new network scan |
| `getScanStatus(jobId)` | `GET /api/scans/:jobId` | Get status of a specific scan |
| `stopScan(jobId)` | `POST /api/scans/:jobId/stop` | Stop a running scan |
| `deleteScan(jobId)` | `DELETE /api/scans/:jobId` | Delete a scan record |
| `getScanHistory()` | `GET /api/scans` | Get all scan records |

---

## Context Providers

The application uses several React Context providers for global state:

| Provider | File | Purpose |
|----------|------|---------|
| `AppContext` | `app-context.tsx` | Core application state (user, connection status) |
| `ThemeProvider` | `theme-provider.tsx` | Dark/light mode toggle |
| `ServersContext` | `servers-context.tsx` | Manage connected servers/nodes |
| `LayoutProvider` | `layout-provider.tsx` | Sidebar collapse state |
| `DirectionProvider` | `direction-provider.tsx` | RTL/LTR support |
| `FontProvider` | `font-provider.tsx` | Font customization |
| `SearchProvider` | `search-provider.tsx` | Global search state |

---

## Key Components

### Layout Components (`components/layout/`)

- **`AppShell`**: Main application wrapper with sidebar and header
- **`Sidebar`**: Navigation sidebar with collapsible menu
- **`Header`**: Top header with user menu, theme toggle, and notifications

### Feature Components

- **`SystemMonitor`** (`components/system-monitor.tsx`): Real-time system metrics display (CPU, Memory, Disk, Network)
- **`ConfigDrawer`** (`components/config-drawer.tsx`): Scan configuration panel
- **`CommandMenu`** (`components/command-menu.tsx`): Keyboard shortcut command palette (Cmd/Ctrl+K)

### UI Components (`components/ui/`)

All base UI components are from ShadcnUI/Radix:
- `Button`, `Card`, `Input`, `Select`, `Dialog`, `Dropdown`, `Tabs`, `Table`, `Tooltip`, etc.

---

## Development

### Prerequisites

- Node.js 18+
- pnpm (recommended) or npm

### Getting Started

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Start with backend (Windows)
pnpm dev:all
```

### Build for Production

```bash
pnpm build
pnpm preview
```

### Linting & Formatting

```bash
# Check code style
pnpm lint
pnpm format:check

# Fix code style
pnpm format
```

### Code Quality

```bash
# Find unused exports/dependencies
pnpm knip
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API URL | `http://localhost:5001` |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk authentication key (if using Clerk) | - |

Create a `.env.local` file in the project root to override defaults.
