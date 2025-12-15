Tech stack for the shadcn/ui +vite template we are using:
UI: ShadcnUI (TailwindCSS + RadixUI)

Build Tool: Vite

Routing: TanStack Router

Type Checking: TypeScript

Linting/Formatting: Eslint & Prettier

Icons: Lucide Icons, Tabler Icons (Brand icons only)

Auth (partial): Clerk


🔐 Cybersecurity Dashboard MVP – Layout & Structure
1. Main Page (Summarized Dashboard)

Key Widgets:

Security posture score (aggregated from Wazuh alerts + network scan results).

Active alerts summary (top critical alerts).

Network health (up/down agents, suspicious open ports).

Threat feed ticker (e.g., pulled from Wazuh or custom feed).

Goal: At-a-glance view of company’s overall cybersecurity health.

2. Apps Section

Each app is modular and should open like a mini-dashboard.

2.1 Network App

Features:

Agent network status (online/offline, latency, bandwidth).

Open ports view (from Nmap/Masscan results).

Detected vulnerabilities (basic scan results).

Live traffic monitor (if you log packet data or Netflow).

Backend: Your Flask + Celery workers run Nmap/Zmap scans, push results to DB, dashboard queries via API.

2.2 Downloads App

Repository of tools, reports, and exported scan results.

Role-based access (admin vs user).

Downloadable CSV, JSON, PDF reports.

2.3 Wazuh App

Features:

Per-agent alerts view (using Wazuh REST API).

Policy violations & compliance reports.

File integrity monitoring results.

Endpoint security status (antivirus, EDR alerts if integrated).

Important: Since Wazuh API supports RBAC, you can expose only tenant-specific data instead of your global dashboard.

2.4 Advanced App

Scripts: Run approved automation (patching, user lockdown, etc.).

API Integrations: Connect with external services (VirusTotal, Shodan, Slack alerts).

Alerts Management: Unified alerting system (from Wazuh + network scans).

JSON Editor: For editing configs (scan configs, Wazuh rules, etc.).

3. Settings

User account management (linked to Clerk for auth).

Team / organization settings.

Agent registration keys.

Custom alert rules (thresholds, notifications).

4. Documentation

Internal docs (how to onboard, how to use features).

Links to Wazuh, Nmap/Zmap docs.

Possibly a knowledge base.

5. Billing

Usage-based billing (e.g., per-agent, per-scan, per-alert).

Integration with Stripe (Clerk works well with it).

Subscription tiers (MVP: Free, Basic, Pro).

Invoice history.

🔧 Tech Notes

Frontend: Vite (React + Clerk for auth).

Backend: Flask + Celery + Redis + SQLAlchemy (SQLite → Postgres later).This is something we should work on now instead of using sql lite
         The backend was moved to an ubuntu server running on local network:192.168.100.37 inside a python virtual Environment

APIs:

Wazuh REST API → fetch agent/alert data.

Flask custom API → network scans, downloads, scripts.


123: Modularity: Each "app" in the dashboard should be its own module in the codebase (so later you can add/remove apps without breaking the core).
124: 
125: 6. Future Roadmap & Vision
126: 
127: The long-term vision for Cloud-X is to evolve into a fully security-based enterprise platform that remains affordable for Small and Medium-sized Businesses (SMBs).
128: 
129: Core Philosophy:
130: -   **Wazuh SIEM as the Core**: The central nervous system of the platform, collecting logs, events, and alerts from all endpoints.
131: -   **Unified Platform**: Combining custom-built modules with best-in-breed open-source tools.
132: 
133: Upcoming Modules:
134: -   **Network Intrusion Detection & Prevention (NIDS/IDPS)**: Advanced network monitoring to detect and block malicious traffic patterns.
135: -   **Data Loss Prevention (DLP)**: Mechanisms to prevent sensitive data exfiltration.
136: -   **Entity and User Behavior Analytics (EUBA)**: Baseline user activity to detect anomalies and insider threats.
137: -   **AI & Analytics Modules**: Leveraging AI to correlate events, predict threats, and automate response actions (SOAR).
138: 
139: Target Audience:
140: -   SMBs needing enterprise-grade security without the enterprise price tag.
