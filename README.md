# Cloud-X Security Dashboard

<div align="center">
  <img src="/images/logo.png" alt="Cloud-X Security Logo" width="200"/>
  <h3>Enterprise-Grade Security Platform for SMBs</h3>
</div>

**Cloud-X Security** is a unified security dashboard designed to bring enterprise-level monitoring, detection, and response capabilities to Small and Medium Businesses (SMBs) at an affordable scale. It combines powerful open-source tools with custom modules into a single pane of glass.

## 📊 Project Status (June 2026)

Cloud-X is currently a **working single-tenant prototype**. The frontend shell and the network-scanning engine are real and functional; the work that turns it into a multi-tenant SaaS — server-side authentication, tenant isolation, the Wazuh SIEM core, durable async, and billing — is in active planning/build.

> **SaaS-readiness: ~18%.** The app runs as a functional prototype on a trusted network. Server-side authentication, tenant isolation, and production hardening are in progress **before any public or multi-tenant deployment.**

| Area | Status |
|---|---|
| Frontend shell · routing · theming · Clerk sign-in | ✅ Built |
| Network scanning (Nmap / ZMap / Masscan) | ✅ Built |
| System monitor | 🟡 Partial |
| Agent deployment (Linux/macOS SSH) | 🟡 Partial |
| Agent deployment (Windows WinRM) | ⚪ Scaffold |
| Wazuh "single pane" (SIEM core) | ⚪ Not built — top priority |
| Advanced tools / Billing / Multi-node | ⚪ Not built |

📄 **Full audit & two-phase roadmap:** [`Documentation/SAAS_READINESS.md`](Documentation/SAAS_READINESS.md) · visual report: [`Documentation/SAAS_READINESS_AUDIT.html`](Documentation/SAAS_READINESS_AUDIT.html)

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
- **Auth**: [Clerk](https://clerk.com/) (frontend; server-side verification planned — see roadmap)
- **Backend**: Flask (Python). Background scans currently run on worker threads; migrating to a Redis-backed task queue (Celery/RQ).
- **Core Engine**: Wazuh SIEM (connector planned — see roadmap)

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
    ├── SAAS_READINESS.md       # SaaS-readiness audit & two-phase roadmap
    ├── ROADMAP.md              # High-level feature roadmap
    ├── IMPLEMENTATION_PLAN.md  # Detailed execution plan
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

### Installation

1.  **Clone the repository**

    ```bash
    git clone https://github.com/MAPLEIZER/Cloud-X-MVP.git
    cd Cloud-X-MVP
    ```

2.  **Start the Backend**

    ```bash
    # See Documentation/BACKEND_AGENTS.md for full setup
    npm run dev:backend
    ```

3.  **Start the Frontend**

    ```bash
    npm run dev
    ```

4.  **Run Both (Recommended)**
    ```bash
    npm run dev:all
    ```

## 🔮 Roadmap

Near-term work is organised into two phases (full detail in [`Documentation/SAAS_READINESS.md`](Documentation/SAAS_READINESS.md)):

- **Phase 1 — Harden & complete the core** (single-tenant, pilot-ready): server-side auth, security hardening, the Wazuh connector + dashboard, Postgres + a durable job queue, and a monthly posture-report PDF.
- **Phase 2 — Multi-tenant SaaS**: org/tenant model + RBAC, the Wazuh isolation strategy, billing (Stripe + M-Pesa/Paystack), and a DPA-aligned compliance layer.

Longer-term modules (NIDS/IDPS, DLP, EUBA, AI/SOAR) are tracked in [`Documentation/ROADMAP.md`](Documentation/ROADMAP.md).

## 📄 License

[MIT License](LICENSE)
