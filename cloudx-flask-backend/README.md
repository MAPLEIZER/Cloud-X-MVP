# Cloud-X Flask Backend

## Requirements
- Python 3.8+
- Virtual environment (recommended)
- Nmap, ZMap, and Masscan scanning tools

## Installation

1. Create a virtual environment:
   ```
   python3 -m venv venv
   # On macOS/Linux:
   source venv/bin/activate

   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install scanning tools:
   ```
   sudo apt update
   sudo apt install nmap zmap masscan
   ```

## Running the Application

**Important**: Due to the nature of network scanning tools, the application must be run with sudo privileges while preserving the virtual environment:

```bash
# On macOS/Linux:
sudo $(which python3) app.py

# On Windows (run PowerShell as Administrator):
python app.py
```

This is required because tools like ZMap and Masscan need root access to open raw sockets for network scanning. Using `sudo $(which python3)` ensures that the virtual environment is preserved while running with elevated privileges.

## API Endpoints

- `GET /api/scans` - List all scans
- `POST /api/scans` - Start a new scan (Body: `target`, `tool`, `scan_type`, `port`)
- `GET /api/scans/<job_id>` - Get scan status and results
- `DELETE /api/scans/<job_id>` - Stop a running scan
- `POST /api/scans/<job_id>/stop` - Stop a specific scan
- `GET /api/system-monitor?target=<ip>` - Monitor system resources (local or remote ping)
- `POST /api/deploy/agent` - Deploy Wazuh agent to a target (Body: `target`, `os_type`, `username`, `password`, etc.)
- `POST /api/deploy/node` - Deploy a backend node to a target
- `GET /api/sync-status` - Check heartbeat file status
- `GET /api/health` - Simple health check
- `GET /api/ping` - Connectivity check

## Database

The application uses a local SQLite database (`scans.db`) to store scan jobs and results.

## Configuration

The application runs on port 5001 and accepts connections from all interfaces (0.0.0.0).
