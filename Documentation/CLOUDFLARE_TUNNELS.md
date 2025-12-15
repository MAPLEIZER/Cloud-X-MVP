# Cloudflare Tunnels Deployment Guide

This guide explains how to expose your Cloud-X Security Dashboard from your home server securely using Cloudflare Tunnels.

## Overview

Cloudflare Tunnels allows you to expose local services to the internet without opening ports on your firewall. This provides a secure, encrypted connection between your home server and Cloudflare's edge network.

## Current Project Status

### Frontend
- **Technology**: React, TypeScript, Vite
- **UI Framework**: Shadcn UI with TailwindCSS
- **Features**: Modern responsive interface, light/dark mode, Clerk authentication
- **Development Port**: 3000 (via `npm run dev`)

### Backend
- **Technology**: Flask REST API
- **Port**: 5001
- **Database**: SQLite (scans.db)
- **Features**: Network scanning, system monitoring, background task processing

## Prerequisites

### Required
- A domain managed by Cloudflare
- Cloudflare account with DNS access
- Docker installed on your home server
- Linux-based home server (recommended: Ubuntu 20.04+)

### Optional but Recommended
- Static IP address (for stability)
- UPS backup system
- Firewall configured for Docker

## Step 1: Prepare Your Server

### Install Docker
```bash
# Update package index
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Create Cloudflare Directory
```bash
mkdir -p ~/cloudflared && cd ~/cloudflared
```

## Step 2: Create Cloudflare Tunnel

### 2.1 Generate Tunnel Credentials
```bash
# Set your variables
export TUNNEL_NAME="cloudx-tunnel"
export DOMAIN="yourdomain.com"  # Replace with your actual domain

# Create tunnel via Cloudflare API (requires cloudflared CLI)
docker run --rm -v $PWD:/home/nonroot/.cloudflared cloudflare/cloudflared:latest tunnel login

# Create the tunnel
docker run --rm -v $PWD:/home/nonroot/.cloudflared cloudflare/cloudflared:latest tunnel create $TUNNEL_NAME

# Note the tunnel ID from the output
export TUNNEL_ID="your-tunnel-id-here"  # Replace with actual ID
```

### 2.2 Create Configuration File
Create `config.yml` in `~/cloudflared/`:

```yaml
tunnel: $TUNNEL_ID
credentials-file: /home/nonroot/.cloudflared/$TUNNEL_ID.json

ingress:
  # Main application
  - hostname: cloudx.$DOMAIN
    service: http://localhost:5001
    # Optional: Add health check
    originRequest:
      noTLSVerify: false
      connectTimeout: 30s
      tlsTimeout: 10s
  
  # Frontend (if serving separately)
  - hostname: app.$DOMAIN
    service: http://localhost:3000
  
  # Default route for unmatched traffic
  - service: http_status:404
```

### 2.3 Download Credentials
```bash
# Download the credentials file
docker run --rm -v $PWD:/home/nonroot/.cloudflared cloudflare/cloudflared:latest tunnel route dns $TUNNEL_ID cloudx.$DOMAIN
```

## Step 3: Set Up Systemd Service

Create a systemd service to run the tunnel automatically:

```bash
sudo tee /etc/systemd/system/cloudflared.service > /dev/null << 'EOL'
[Unit]
Description=Cloudflare Tunnel for Cloud-X Dashboard
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/cloudflared
ExecStart=/usr/bin/docker run --rm --name cloudflared \
  --network=host \
  -v /root/cloudflared:/etc/cloudflared \
  -v /root/cloudflared:/home/nonroot/.cloudflared \
  cloudflare/cloudflared:latest tunnel --config /etc/cloudflared/config.yml run
Restart=always
RestartSec=10
TimeoutStartSec=30

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd and enable the service
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared
```

## Step 4: Configure DNS

1. Log in to your Cloudflare dashboard
2. Navigate to your domain's DNS settings
3. Create a new CNAME record:
   - **Type**: CNAME
   - **Name**: cloudx
   - **Target**: `$TUNNEL_ID.cfargotunnel.com`
   - **Proxy status**: Proxied (orange cloud icon)
   - **TTL**: Auto

## Step 5: Update Application Configuration

### 5.1 Flask Backend CORS Update
Update `cloudx-flask-backend/app.py`:

```python
# Replace the existing CORS configuration
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://cloudx.yourdomain.com",  # Your production domain
            "http://localhost:3000",         # Keep for local development
            "http://localhost:5001"          # Direct backend access
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
    }
})
```

### 5.2 Frontend Environment Variables
Create `.env.production` in the project root:

```env
# Production environment variables
VITE_API_BASE_URL=https://cloudx.yourdomain.com/api
VITE_APP_URL=https://cloudx.yourdomain.com
VITE_ENVIRONMENT=production
```

### 5.3 Update Production Build
Update `vite.config.ts` for production:

```typescript
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['@tanstack/react-router'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu']
        }
      }
    }
  },
  server: {
    host: true,
    port: 3000
  }
})
```

## Step 6: Security Configuration

### 6.1 Cloudflare WAF Rules
Set up these WAF rules in your Cloudflare dashboard:

1. **Rate Limiting**:
   - Path: `*`
   - Rate limit: 100 requests per minute
   - Action: Challenge

2. **Country Blocking** (optional):
   - Block countries from which you don't expect traffic

3. **Bot Fight Mode**:
   - Enable to challenge suspicious bots

### 6.2 Cloudflare Access (Recommended)
For additional security, set up Cloudflare Access:

1. Go to "Access" > "Applications" in Cloudflare
2. Add new application:
   - Application domain: `cloudx.yourdomain.com`
   - Session duration: 8 hours
   - Add authentication methods (Email, Google, etc.)
3. Create policies for who can access

### 6.3 SSL/TLS Configuration
In Cloudflare SSL/TLS settings:
- **Encryption Mode**: Full (strict)
- **Minimum TLS Version**: 1.2
- **HSTS**: Enable

## Step 7: Production Deployment

### 7.1 Build Frontend
```bash
cd /path/to/Cloud-X-MVP
npm run build
```

### 7.2 Serve Frontend with Nginx
Create Nginx configuration:

```nginx
# /etc/nginx/sites-available/cloudx
server {
    listen 80;
    server_name localhost;
    
    # Serve frontend
    location / {
        root /path/to/Cloud-X-MVP/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # Proxy API requests to Flask
    location /api {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/cloudx /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7.3 Update Cloudflare Config
Update your `config.yml` to point to Nginx:

```yaml
ingress:
  - hostname: cloudx.$DOMAIN
    service: http://localhost:80  # Nginx port
  - service: http_status:404
```

## Step 8: Monitoring and Maintenance

### 8.1 Service Monitoring
```bash
# Check tunnel status
sudo systemctl status cloudflared

# View logs
journalctl -u cloudflared -f

# Check if tunnel is accessible
curl -I https://cloudx.yourdomain.com/api/health
```

### 8.2 Health Check Script
Create `/usr/local/bin/health-check.sh`:

```bash
#!/bin/bash
# Health check for Cloud-X services

TUNNEL_STATUS=$(systemctl is-active cloudflared)
NGINX_STATUS=$(systemctl is-active nginx)
FLASK_STATUS=$(pgrep -f "python app.py" > /dev/null && echo "running" || echo "stopped")

echo "=== Cloud-X Health Check ==="
echo "Tunnel: $TUNNEL_STATUS"
echo "Nginx: $NGINX_STATUS"
echo "Flask: $FLASK_STATUS"

if [[ "$TUNNEL_STATUS" != "active" ]]; then
    echo "Restarting Cloudflare Tunnel..."
    sudo systemctl restart cloudflared
fi

if [[ "$NGINX_STATUS" != "active" ]]; then
    echo "Restarting Nginx..."
    sudo systemctl restart nginx
fi
```

Make it executable and add to cron:
```bash
chmod +x /usr/local/bin/health-check.sh
echo "*/5 * * * * /usr/local/bin/health-check.sh" | sudo crontab -
```

### 8.3 Backup Strategy
Create backup script `/usr/local/bin/backup-cloudx.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/cloudx"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp /path/to/cloudx-flask-backend/scans.db $BACKUP_DIR/scans_$DATE.db

# Backup configuration files
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    /root/cloudflared/config.yml \
    /root/cloudflared/*.json \
    /etc/nginx/sites-available/cloudx

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

## Step 9: Troubleshooting

### Common Issues

1. **Tunnel Not Starting**
   ```bash
   # Check Docker is running
   sudo systemctl status docker
   
   # Check tunnel logs
   journalctl -u cloudflared -n 50
   ```

2. **502 Bad Gateway**
   - Verify Flask backend is running on port 5001
   - Check Nginx configuration: `sudo nginx -t`
   - Review Nginx error logs: `sudo tail -f /var/log/nginx/error.log`

3. **CORS Errors**
   - Verify CORS configuration in Flask app
   - Check that your domain is listed in allowed origins
   - Clear browser cache and cookies

4. **DNS Propagation**
   - Use `dig cloudx.yourdomain.com` to verify DNS
   - May take up to 24 hours for full propagation

### Performance Optimization

1. **Enable Cloudflare Caching**
   - Cache static assets for 1 year
   - Cache API responses for 5 minutes (if appropriate)

2. **Database Optimization**
   - Consider migrating to PostgreSQL for better performance
   - Implement connection pooling

3. **Monitoring Setup**
   - Set up Uptime monitoring from external service
   - Configure Cloudflare Analytics

## Step 10: Advanced Configuration

### Multiple Services
If you need to expose multiple services:

```yaml
ingress:
  - hostname: cloudx.$DOMAIN
    service: http://localhost:5001
  - hostname: monitor.$DOMAIN
    service: http://localhost:3000
  - hostname: api.$DOMAIN
    service: http://localhost:8080
  - service: http_status:404
```

### Load Balancing
For high availability, consider:
- Multiple backend servers
- Cloudflare Load Balancing
- Database replication

### CI/CD Integration
Set up automated deployment:
1. GitHub Actions to build and test
2. Automated deployment to production
3. Rollback capabilities

## Security Checklist

- [ ] Cloudflare Access configured
- [ ] WAF rules enabled
- [ ] Rate limiting active
- [ ] SSL/TLS set to Full (strict)
- [ ] HSTS enabled
- [ ] Regular backups configured
- [ ] Monitoring alerts set up
- [ ] Firewall rules configured
- [ ] Database credentials secured
- [ ] API endpoints authenticated

## Support

For issues with:
- **Cloudflare Tunnels**: Check [Cloudflare documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- **Flask Application**: Review application logs
- **Nginx Configuration**: Check Nginx error logs
- **DNS Issues**: Use Cloudflare DNS tools

Remember to test thoroughly in a staging environment before deploying to production.
