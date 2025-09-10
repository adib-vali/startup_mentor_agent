#!/bin/bash

# Setup script for nginx configuration for Startup Mentor Agent
# This script configures nginx to serve the FastAPI app on port 8080

set -e  # Exit on any error

echo "🚀 Setting up nginx for Startup Mentor Agent..."

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "❌ nginx is not installed. Installing nginx..."
    sudo apt update
    sudo apt install -y nginx
fi

# Check if the FastAPI app is running on port 8001
if ! nc -z localhost 8001 2>/dev/null; then
    echo "⚠️  WARNING: FastAPI app is not running on port 8001"
    echo "   Please start your app with: uvicorn app.main:app --host 0.0.0.0 --port 8001"
    echo "   Continuing with nginx setup..."
fi

# Get server IP address
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "📍 Detected server IP: $SERVER_IP"

# Create the nginx site configuration
NGINX_CONFIG="/etc/nginx/sites-available/startup-mentor"
echo "📝 Creating nginx configuration at $NGINX_CONFIG..."

# Replace placeholder with actual server IP
sed "s/your_server_ip/$SERVER_IP/g" /root/startup_mentor_agent/startup-mentor-nginx | sudo tee $NGINX_CONFIG > /dev/null

# Enable the site
echo "🔗 Enabling nginx site..."
sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/startup-mentor

# Test nginx configuration
echo "🧪 Testing nginx configuration..."
sudo nginx -t

# Restart nginx
echo "🔄 Restarting nginx..."
sudo systemctl restart nginx

# Enable nginx to start on boot
sudo systemctl enable nginx

echo "✅ Nginx setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Start your FastAPI app: uvicorn app.main:app --host 0.0.0.0 --port 8001"
echo "2. Access your app at: http://localhost:8080 or http://$SERVER_IP:8080"
echo "3. Check nginx status: sudo systemctl status nginx"
echo ""
echo "🔧 Useful commands:"
echo "   - View nginx logs: sudo tail -f /var/log/nginx/access.log"
echo "   - View nginx error logs: sudo tail -f /var/log/nginx/error.log"
echo "   - Reload nginx config: sudo nginx -s reload"
echo "   - Stop nginx: sudo systemctl stop nginx" 