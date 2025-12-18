# Cloud-X Security Dashboard

<div align="center">
  <img src="/images/logo.png" alt="Cloud-X Security Logo" width="200"/>
  <h3>Enterprise-Grade Security Platform for SMBs</h3>
</div>

**Cloud-X Security** is a unified security dashboard designed to bring enterprise-level monitoring, detection, and response capabilities to Small and Medium Businesses (SMBs) at an affordable scale. It combines powerful open-source tools with custom modules into a single pane of glass.

## 🚀 Key Features

- **Unified Dashboard**: Real-time overview of your security posture, network health, and active threats.
- **Network Scanning**: Integrated Nmap/Masscan/Zmap functionality to discover open ports and vulnerabilities (`/api/scans`).
- **Agent Management**: Centralized deployment and monitoring of Wazuh agents across Windows, Linux, and macOS.
- **Real-time Alerts**: Instant notifications for critical security events.
- **Modular Architecture**: Extensible design support for future modules like NIDS, DLP, and AI Analytics.

## 🛠️ Tech Stack

- **Frontend**: [Vite](https://vitejs.dev/) + [React](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **UI Framework**: [ShadcnUI](https://ui.shadcn.com/) (TailwindCSS + RadixUI)
- **Routing**: [TanStack Router](https://tanstack.com/router/latest)
- **Backend**: Flask (Python) with Celery & Redis for async tasks
- **Core Engine**: Wazuh SIEM (Integration in progress)

## 📂 Project Structure

```
Cloud-X-MVP/
├── src/                        # Frontend Source Code (React + TypeScript)
│   ├── components/
│   │   ├── ui/                 # ShadcnUI base components
│   │   ├── layout/             # Layouts (Sidebar, Header, AppShell)
│   │   └── pages/              # Page-specific components
│   ├── routes/                 # TanStack Router file-based routes
│   │   ├── _protected/         # Protected routes (dashboard, apps, etc.)
│   │   └── sign-in.tsx         # Authentication routes
│   ├── lib/                    # API client and utilities
│   ├── context/                # React Context providers
│   ├── hooks/                  # Custom React hooks
│   └── assets/                 # Images and static files
├── cloudx-flask-backend/       # Backend API (Flask + Python)
│   ├── app.py                  # Main Flask application
│   ├── deployer.py             # Agent deployment logic (SSH/WinRM)
│   ├── scripts/                # Agent installation scripts
│   │   ├── windows/            # PowerShell modules, certs
│   │   ├── linux/              # Bash scripts, threat removal
│   │   └── mac/                # macOS installation scripts
│   └── scanners/               # Network scanning modules (Nmap, ZMap, Masscan)
├── cloudx-security-agent/      # Agent configuration & documentation
│   ├── documentation/          # Agent integration guides
│   └── wazuh-configs/          # Wazuh agent configurations
└── Documentation/              # Project Documentation
    ├── INDEX.md                # Central documentation index
    ├── FRONTEND.md             # Frontend architecture guide
    ├── BACKEND_AGENTS.md       # Backend & Agent technical docs
    ├── BACKEND_CONFIG.md       # Backend setup and configuration
    ├── project-description.md  # Vision & Roadmap details
    └── prohect-wireframe.md    # UI Wireframes
```

## ⚡ Getting Started

### Prerequisites

- Node.js & npm/pnpm
- Python 3.10+
- Redis server (for backend tasks)
- Docker + Docker Compose (optional, for the Docker install path)

### Installation

#### Option A: Local development (run from source)

1.  **Clone the repository**

    ```bash
    git clone https://github.com/MAPLEIZER/Cloud-X-MVP.git
    cd Cloud-X-MVP
    ```

2.  **Install frontend dependencies**

    ```bash
    pnpm install
    # or
    npm install
    ```

3.  **Set up the backend (Python)**

    See `cloudx-flask-backend/README.md` for full details.

    ```bash
    cd cloudx-flask-backend
    python -m venv venv
    # Windows PowerShell:
    .\\venv\\Scripts\\Activate.ps1
    # macOS/Linux:
    # source venv/bin/activate
    pip install -r requirements.txt
    cd ..
    ```

4.  **Start the backend**

    ```bash
    # Backend must be set up first (venv + requirements)
    npm run dev:backend
    ```

5.  **Start the frontend**

    ```bash
    pnpm dev
    # or
    npm run dev
    ```

6.  **Run both (recommended)**
    ```bash
    pnpm dev:all
    # or
    npm run dev:all
    ```

#### Option B: Docker (pull prebuilt images from GHCR)

This runs the published images built by GitHub Actions (faster than building locally).

1.  **Start the backend**
    ```bash
    docker compose -f cloudx-flask-backend/docker-compose.yml up -d
    ```

2.  **Start the frontend**
    ```bash
    docker compose -f deploy/frontend/docker-compose.yml up -d
    ```

3.  **Verify**
   - Frontend: `http://localhost:3000`
   - Backend health: `http://localhost:5001/api/health`

Notes:
- Images are `ghcr.io/mapleizer/cloudx-backend:latest` and `ghcr.io/mapleizer/cloudx-frontend:latest`.
- The frontend API base URL is baked into the image at build time; see `Documentation/GITHUB_DOCKER_BUILDS.md`.

## 🔮 Future Roadmap

We are actively building the next generation of Cloud-X with focus on:

- **NIDS/IDPS**: Network Intrusion Detection
- **DLP**: Data Loss Prevention
- **AI Analytics**: Automated Threat Hunting

See [ROADMAP.md](./ROADMAP.md) for the detailed development plan.

## 📄 License

[MIT License](LICENSE)
