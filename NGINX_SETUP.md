# Nginx Configuration for Startup Mentor Agent

This guide explains how to configure nginx as a reverse proxy for your FastAPI Startup Mentor Agent application.

## Overview

- **FastAPI App**: Runs on `localhost:8001`
- **Nginx**: Serves on port `8080` (since port 80 is occupied by another project)
- **Access URL**: `http://your-server-ip:8080`

## Quick Setup

### Option 1: Automated Setup (Recommended)

Run the provided setup script:

```bash
sudo ./setup_nginx.sh
```

This script will:
- Install nginx if not present
- Create and enable the nginx configuration
- Test the configuration
- Restart nginx
- Provide next steps

### Option 2: Manual Setup

1. **Install nginx** (if not already installed):
   ```bash
   sudo apt update
   sudo apt install nginx
   ```

2. **Copy the nginx configuration**:
   ```bash
   sudo cp startup-mentor-nginx /etc/nginx/sites-available/startup-mentor
   ```

3. **Update the server IP** in the configuration:
   ```bash
   sudo nano /etc/nginx/sites-available/startup-mentor
   # Replace 'your_server_ip' with your actual server IP
   ```

4. **Enable the site**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/startup-mentor /etc/nginx/sites-enabled/
   ```

5. **Test nginx configuration**:
   ```bash
   sudo nginx -t
   ```

6. **Restart nginx**:
   ```bash
   sudo systemctl restart nginx
   sudo systemctl enable nginx
   ```

## Starting Your Application

1. **Start the FastAPI application**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```

2. **Access your application**:
   - Local: `http://localhost:8080`
   - Remote: `http://your-server-ip:8080`

## Configuration Details

The nginx configuration includes:

- **Reverse Proxy**: Forwards requests from port 8080 to your FastAPI app on port 8001
- **WebSocket Support**: For real-time features (if needed)
- **Gzip Compression**: Reduces bandwidth usage
- **Security Headers**: Basic security improvements
- **Static File Serving**: Direct nginx serving for static assets
- **Health Check Endpoint**: Proxies health checks to your app

## Troubleshooting

### Check if FastAPI is running:
```bash
curl http://localhost:8001
```

### Check nginx status:
```bash
sudo systemctl status nginx
```

### View nginx logs:
```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

### Test nginx configuration:
```bash
sudo nginx -t
```

### Reload nginx after config changes:
```bash
sudo nginx -s reload
```

## Port Information

- **Port 8001**: FastAPI application (internal)
- **Port 8080**: Nginx proxy (public access)
- **Port 80**: Used by your other project (not touched)

## Files Created

- `nginx.conf`: Local development nginx config
- `startup-mentor-nginx`: System nginx site configuration
- `setup_nginx.sh`: Automated setup script
- `NGINX_SETUP.md`: This documentation

## Security Considerations

The configuration includes basic security headers. For production, consider:

- SSL/TLS certificates (Let's Encrypt)
- Rate limiting
- IP whitelisting (if needed)
- Firewall configuration
- Regular security updates 