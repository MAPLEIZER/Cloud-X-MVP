# Cloud-X Security Scanner: Backend Configuration

This document outlines the setup and configuration required for the Flask-based backend application that powers the Cloud-X Security Dashboard.

## Core Technologies

| Technology | Purpose |
|------------|---------|
| **Flask** | Web framework for REST API |
| **Flask-SQLAlchemy** | Database ORM |
| **Flask-CORS** | Cross-origin request handling |
| **SQLite** | Database (file: `scans.db`) |
| **Threading** | Background task processing for scans |
| **Paramiko** | SSH connections for Linux/Mac agent deployment |
| **pywinrm** | WinRM connections for Windows agent deployment |
| **psutil** | Local system monitoring |
| **ping3** | Network latency checking |

> **Note**: The current implementation uses Python threading for background tasks instead of Celery. This simplifies deployment but limits scalability. For high-volume deployments, consider migrating to Celery with Redis.

---

## Environment Variables

The backend uses minimal environment configuration. For production, create a `.env` file:

```env
# Optional: Override database location
DATABASE_URL=sqlite:///scans.db

# Optional: Flask debug mode (default: True in development)
FLASK_DEBUG=1
```

---

## Setup and Running

### Prerequisites

- Python 3.8+
- Network scanning tools: `nmap`, `zmap`, `masscan` (for scan functionality)
- Virtual environment (recommended)

### Installation

1. **Create and activate virtual environment:**
   ```bash
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install scanning tools (Linux/macOS):**
   ```bash
   sudo apt update
   sudo apt install nmap zmap masscan
   ```

### Running the Backend

```bash
# Linux/macOS (requires sudo for raw socket access)
sudo $(which python3) app.py

# Windows (run PowerShell as Administrator)
python app.py
```

The backend API will be available at `http://0.0.0.0:5001`.

---

## Database

The application uses SQLite with automatic table creation on startup.

- **Database file**: `scans.db` (created automatically)
- **Main table**: `Scan` - stores scan jobs, status, and results

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `job_id` | String(36) | UUID for the scan |
| `tool` | String(50) | Scanner tool (nmap, zmap, masscan) |
| `target` | String(128) | Scan target IP/network |
| `scan_type` | String(50) | Scan type configuration |
| `status` | String(20) | Current status |
| `progress` | Integer | Progress percentage (0-100) |
| `results` | Text | JSON-encoded scan results |
| `created_at` | DateTime | Creation timestamp |

---

## API Endpoints

See [cloudx-flask-backend/README.md](../cloudx-flask-backend/README.md) for complete API documentation.

---

## Deployment Notes

### Agent Scripts Location

The backend serves agent installation scripts from:
```
cloudx-flask-backend/scripts/
├── windows/
│   ├── cloudx-agent-installer.psm1
│   ├── cloudx-agent-uninstaller.psm1
│   └── cloudx-code-signing.cer
├── linux/
│   ├── cloudx-agent-install.sh
│   ├── cloudx-agent-setup.sh
│   ├── remove-threat.py
│   └── requirements.txt
└── mac/
    ├── cloudx-agent-install.sh
    └── cloudx-agent-setup.sh
```

### File Synchronization

The backend uses a heartbeat file (`sync_heartbeat.json`) for monitoring file synchronization status. The `/api/sync-status` endpoint checks this file's timestamp.
