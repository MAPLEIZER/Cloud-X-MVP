# Cloud-X Security Roadmap

This document outlines the development roadmap for the Cloud-X Security Platform, moving from the current MVP to a comprehensive enterprise security solution for SMBs.

For a detailed execution timeline and implementation steps (including the AI-powered SOC vision), see `Documentation/IMPLEMENTATION_PLAN.md`.

## ✅ Completed (MVP Phase)

-   **Core Infrastructure**:
    -   Vite + React + ShadcnUI Frontend.
    -   Flask + Python Backend (`cloudx-flask-backend`).
    -   Agent Deployment Module (`deployer.py`).
-   **Dashboard**:
    -   Main Overview with widgets.
    -   Network Health & Scan Activity.
-   **Network Scanning App**:
    -   Nmap/Masscan integration (`/api/scans`).
    -   Real-time progress updates.
    -   Scan History with Filter/Search/Export.
-   **Settings**:
    -   Basic UI layout and navigation.
-   **Agent**:
    -   Custom Windows/Linux/Mac installers.
    -   Automatic Certificate Trust (Windows).
    -   Self-contained PowerShell/Bash scripts.

## 🚧 In Progress

-   **Documentation**:
    -   Backend API & Agent Docs (`Documentation/BACKEND_AGENTS.md`).
    -   Project Vision (`Documentation/project-description.md`).
-   **System Stability**:
    -   Global Linting & Type Checking.
    -   Backend Error Handling refinements.

## 📋 Planned Features (Short Term)

### 1. Downloads App
-   [ ] **Secure Storage**: Interface for storing security tools and reports.
-   [ ] **RBAC**: Role-based access control for file access.
-   [ ] **Report Generation**: Export scan results as PDF/CSV/JSON.

### 2. Wazuh Integration App
-   [ ] **Agent Dashboard**: View status of all deployed Wazuh agents.
-   [ ] **Alerts View**: Real-time stream of security events from Wazuh Manager.
-   [ ] **Policy Compliance**: Visualization of SCA (Security Configuration Assessment) results.
-   [ ] **File Integrity Monitoring**: View changes detected by Wazuh FIM.

### 3. Advanced Tools App
-   [ ] **Script Executor**: Web UI to run approved scripts on agents (via Active Response or custom agent actions).
-   [ ] **JSON Editor**: Web-based editor for `ossec.conf` and other config files.
-   [ ] **API Manager**: Configure integrations with external tools (VirusTotal, Shodan).

### 4. Billing System
-   [ ] **Stripe Integration**: Usage-based billing.
-   [ ] **Subscription Tiers**: Free, Basic, Pro management.

## 🔮 Future Vision (Enterprise Core)

The long-term goal is to build a unified **Security Operation Center (SOC)** platform for SMBs.

### Core Architecture
-   **Wazuh SIEM**: The central engine for log collection and correlation.
-   **Unified Dashboard**: Single pane of glass for all security data.

### Upcoming Modules
-   **NIDS/IDPS**: Network Intrusion Detection & Prevention System.
-   **DLP**: Data Loss Prevention module to detect sensitive data exfiltration.
-   **EUBA**: Entity and User Behavior Analytics for anomaly detection.
-   **AI & Analytics**:
    -   AI-assisted SOC triage and case management (analyst copilot).
    -   Automated incident response (SOAR).
    -   AI-driven threat hunting and prediction.
