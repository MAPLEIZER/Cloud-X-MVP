# Cloud-X Security Dashboard Setup Guide

## Quick Start

1. **Clone and Install Dependencies**
   ```bash
   cd "C:\Users\ADMIN\Downloads\Austin\Cloud-X Dashboard"
   pnpm install
   ```

2. **Configure Environment Variables**
   - Copy `.env.example` to `.env.local`
   - Get your Clerk publishable key from [Clerk Dashboard](https://dashboard.clerk.com)
   - Update the `.env.local` file:
   ```
   VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_actual_key_here
   VITE_API_BASE_URL=http://192.168.100.37:5001
   ```

3. **Start Development Server**
   ```bash
   pnpm dev
   ```
   The app will be available at `http://localhost:5173`

## Clerk Authentication Setup

### For Development/Testing:
1. Create a free Clerk account at [clerk.com](https://clerk.com)
2. Create a new application
3. In your Clerk dashboard:
   - Go to **Configure > Domains**
   - Add `localhost:5173` as an allowed domain
   - Copy your publishable key to `.env.local`

### Authentication Flow:
- **Sign In**: `/sign-in` - Clerk-powered sign-in page
- **Sign Up**: `/sign-up` - Clerk-powered registration page
- **Protected Routes**: All `/apps/*` routes require authentication
- **Dashboard**: Main landing page after authentication

## Project Structure

```
src/
├── components/
│   ├── auth/           # Authentication components
│   ├── layout/         # Layout components (sidebar, header)
│   ├── pages/          # Page components
│   │   ├── network/    # Network scanner pages
│   │   └── dashboard/  # Dashboard widgets
│   └── ui/            # ShadcnUI components
├── routes/            # TanStack Router routes
│   ├── _protected/    # Protected routes
│   │   ├── apps/      # App routes
│   │   └── dashboard/ # Dashboard route
│   ├── sign-in/       # Auth routes
│   └── sign-up/
├── context/           # React context providers
├── lib/              # Utilities and API client
└── types/            # TypeScript type definitions
```

## Available Routes

### Public Routes:
- `/sign-in` - Sign in page
- `/sign-up` - Sign up page

### Protected Routes (require authentication):
- `/dashboard` - Main dashboard with security metrics
- `/apps/network/scan` - Network scanner interface
- `/apps/network/history` - Scan history and results
- `/settings` - Application settings
- `/documentation` - Help and documentation
- `/billing` - Billing and subscription management

## Backend Integration

The frontend connects to a Flask backend running at `http://192.168.100.37:5001`.

### API Endpoints:
- `GET /api/health` - Backend health check
- `POST /api/scan` - Start new network scan
- `GET /api/scans` - Get scan history
- `GET /api/scan/:id` - Get specific scan details

### Network Scanning Tools:
- **Nmap** - Comprehensive network discovery and security auditing
- **ZMap** - Fast internet-wide network scanner
- **Masscan** - High-speed port scanner

## Features Implemented

✅ **Authentication**: Clerk-based auth with protected routes  
✅ **Dashboard**: Security metrics and overview widgets  
✅ **Network Scanner**: Full-featured scanning interface  
✅ **Scan History**: Results management and filtering  
✅ **Mobile Responsive**: Mobile-first responsive design  
✅ **Real-time Status**: Backend connectivity monitoring  

## Next Steps

1. **Environment Setup**: Configure your `.env.local` file with actual Clerk keys
2. **Backend Connection**: Ensure Flask backend is running on `192.168.100.37:5001`
3. **Database Migration**: Plan PostgreSQL migration from SQLite
4. **Wazuh Integration**: Implement security monitoring components
5. **Advanced Features**: Add Downloads app, Advanced tools, etc.

## Troubleshooting

### Common Issues:

1. **Clerk Authentication Errors**
   - Verify publishable key in `.env.local`
   - Check domain configuration in Clerk dashboard
   - Ensure localhost:5173 is added to allowed domains

2. **Backend Connection Issues**
   - Verify Flask backend is running on `192.168.100.37:5001`
   - Check network connectivity to backend server
   - Review CORS settings if needed

3. **TypeScript Errors**
   - Most route typing errors will resolve as route structure completes
   - Run `pnpm run type-check` to identify issues

4. **Build Issues**
   - Clear node_modules and reinstall: `rm -rf node_modules && pnpm install`
   - Check for missing dependencies

## Development Commands

```bash
# Start development server
pnpm dev

# Build for production
pnpm build

# Preview production build
pnpm preview

# Type checking
pnpm run type-check

# Linting
pnpm run lint
```
