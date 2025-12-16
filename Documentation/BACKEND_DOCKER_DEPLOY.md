# Cloud-X Backend: Dockerized Install & Node Bootstrap

Borrowed Cloud-X ASCII art (from the agent installer) for the installer banner:

```text
                                                                                                    
                                                                                                    
                                               @@@@@                                                
                                            @@@      @@                                             
                                          @@             @@                                         
                                     @@@@@@         @@@@@@@@@@@                                     
                                    @@@           @@@         @@                                    
                                   @@           @@@  @@@@@@@@@ @@                                   
                                   @@ @       @@@  @@@       @ @@                                   
                                   @@ @@    @@@  @@@         @ @@                                   
                                    @@   @@    @@@            @@                                    
                                     @@@@@@@@@@@       @@@@@@@                                      
                                         @@@                                                        
                                                                                                    
                                    @@                     @@    @    @                             
                               @    @@   @@             @  @     @@  @                              
                             @@@@@@ @@ @@@@@@  @@  @@ @@@@@@       @@                               
                            @@      @@ @@   @@ @   @@ @    @      @ @@                              
                             @@@@@  @@ @@@@@@  @@@@@@ @@@@@@@    @   @@                             
                                                                                                    
                                                                                                    
                                                                                                    
```

## Backend shape (from repo scan)
- API server: `cloudx-flask-backend/app.py` (Flask + SQLAlchemy), listens on `0.0.0.0:5001`, uses SQLite `scans.db`, and exposes `/api/health`, `/api/ping`, `/api/scans`, `/api/system-monitor`, `/api/deploy/agent`, `/api/deploy/node`.
- Identity + persistence: `entrypoint.sh` creates `server_identity.json` (UUID) and exports `SERVER_ID`; volumes are expected for `scans.db` and `server_identity.json` so nodes keep identity across restarts.
- Agent deploy helper: `deployer.py` ships the scripts in `cloudx-flask-backend/scripts/{linux,windows,mac}` to remote hosts (Wazuh agent install/cleanup).
- Docker build: `cloudx-flask-backend/Dockerfile` uses `python:3.9-slim`, installs `nmap` + `iputils-ping` + `curl`, copies the app, and runs `entrypoint.sh`.
- Compose default: `cloudx-flask-backend/docker-compose.yml` maps `5001:5001`, mounts `./scans.db` and `./server_identity.json`, restarts unless stopped. Scanners need raw sockets (`NET_RAW`) when using masscan/zmap/nmap; add the capability when running in Docker.

## Build or publish the image (run from repo root)
```bash
# Build from cloudx-flask-backend
docker build -t cloudx-backend:latest cloudx-flask-backend

# Optional: save for offline install
docker save cloudx-backend:latest > cloudx-backend.tar
# Optional: push to a registry you control
# docker tag cloudx-backend:latest ghcr.io/<org>/cloudx-backend:latest
# docker push ghcr.io/<org>/cloudx-backend:latest
```

## Interactive install script (run on the backend server)
Use this on Ubuntu/Debian VPS hosts to lay down `.env` + `docker-compose.yml`, load/pull the image, and start the container with prompts for host-specific values (hostname, port, role, primary URL, image tag). The banner reuses the Cloud-X ASCII art above.

### How to run
Copy the included `install_backend.sh` from the repository to your server and execute it with root privileges:

```bash
cp install_backend.sh /tmp/install_backend.sh
sudo bash /tmp/install_backend.sh
```

### What the script does
- Prints the Cloud-X ASCII banner, confirms Docker + docker compose availability, and prompts for data dir, image tag, host port, node role, primary URL (for workers), node ID, and NET_RAW capability.
- Optionally loads a saved tarball (`docker load`) or attempts `docker pull` for the chosen image.
- Writes `.env` and `docker-compose.yml` into the chosen data directory, mounting `scans.db` and `server_identity.json` so the node keeps its ID.
- Runs `docker compose up -d` and leaves the app listening on the chosen host port mapped to container port 5001 (the app itself is fixed to 5001 in `app.py`).

## Multi-node notes
- Primary vs worker: the current codebase does not yet implement `/api/nodes/register` or `/api/nodes/heartbeat`; the `PRIMARY_NODE_URL`/`NODE_ROLE` values are persisted for future upgrades and documentation clarity.
- Identity: `entrypoint.sh` writes `server_identity.json` and exports `SERVER_ID` so each node keeps a stable ID across restarts or host reboots.
- Load balancing: place Nginx/HAProxy/Traefik in front of multiple backend containers and health-check `/api/health`. Persist the mounted volumes per node.

## Operate and verify
- Health check: `curl -fsSL http://<host>:<port>/api/health` and `/api/ping`.
- Logs: `docker compose -f <DATA_DIR>/docker-compose.yml logs -f backend`.
- Data: SQLite lives at `<DATA_DIR>/scans.db`; node identity at `<DATA_DIR>/server_identity.json`.
- Updates: rebuild/pull the image, then rerun the installer or simply `docker compose -f <DATA_DIR>/docker-compose.yml up -d` to pick up the new image tag.

## Optional: reverse proxy (Nginx) for frontend + backend + Cloudflare tunnel
- Files: `deploy/reverse-proxy/docker-compose.yml` and `deploy/reverse-proxy/nginx.conf.template`.
- Defaults: proxies `/api/` to `http://host.docker.internal:5001` (backend) and everything else to `http://host.docker.internal:3000` (frontend). Publishes port `80`.
- Linux host: `host.docker.internal` is mapped via `extra_hosts: host-gateway`.
- Run it (from repo root or copy the folder to the server):
  ```bash
  cd deploy/reverse-proxy
  docker compose up -d
  curl -fsSL http://localhost/_proxy/health   # proxy health
  ```
- To point Nginx at different upstreams (e.g., another host or container network), set envs before `docker compose up -d`:
  ```bash
  BACKEND_UPSTREAM=http://192.168.100.47:5001 FRONTEND_UPSTREAM=http://192.168.100.47:3000 docker compose up -d
  ```
- Cloudflare Tunnel: point the tunnel to the proxy’s published port (default 80). The proxy stays as the single entrypoint; backend/frontend stay inside.

## CI/CD: build and push backend image (GHCR)
- Workflow: `.github/workflows/backend-image.yml` builds `cloudx-flask-backend` and pushes to GHCR on pushes to `main`.
- Authentication uses the built-in `${{ secrets.GITHUB_TOKEN }}`; no extra secrets are required for publishing to GitHub Container Registry in this repository.
- Image tags published:
  - `ghcr.io/<owner>/cloudx-backend:latest`
  - `ghcr.io/<owner>/cloudx-backend:<git-sha>`

## CI/CD: build and push frontend image (GHCR)
- Workflow: `.github/workflows/frontend-image.yml` builds the Vite frontend via `Dockerfile.frontend` and pushes to GHCR on pushes to `main`.
- Build arg `FRONTEND_API_BASE_URL` controls the API URL baked at build time (default `http://localhost:5001`). Set repository variable `FRONTEND_API_BASE_URL` to point at your backend (e.g., `http://192.168.100.47:5001`).
- Authentication uses `${{ secrets.GITHUB_TOKEN }}` for GHCR login.
- Image tags published:
  - `ghcr.io/<owner>/cloudx-frontend:latest`
  - `ghcr.io/<owner>/cloudx-frontend:<git-sha>`

## Server-side pull/update helpers
- Backend: `deploy/pull-backend.sh`
  ```bash
  COMPOSE_FILE=/opt/cloudx-backend/docker-compose.yml bash pull-backend.sh
  ```
  Compose must reference `ghcr.io/<owner>/cloudx-backend:latest` (set during installer run).

- Frontend: `deploy/pull-frontend.sh`
  ```bash
  COMPOSE_FILE=/opt/cloudx-frontend/docker-compose.yml bash pull-frontend.sh
  ```
  Compose example lives at `deploy/frontend/docker-compose.yml` (replace `REPLACE_ME_OWNER` with your GHCR owner and ensure the backend URL baked at build time matches your environment).
