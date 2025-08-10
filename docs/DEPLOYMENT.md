# Deployment Guide

This document provides comprehensive instructions for deploying the Court Data Fetcher application in various environments.

## Prerequisites

- Python 3.8 or higher
- Chrome browser (for Selenium)

- Git

## Local Development Deployment

### 1. Clone the Repository

```bash
git clone <repository-url>
cd court_data_fetcher
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```



### 4. Initialize Database

```bash
python -c "from db import init_db; init_db()"
```

### 5. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`



## Production Deployment

### 1. Using Gunicorn

Install Gunicorn:

```bash
pip install gunicorn
```

Create `gunicorn.conf.py`:

```python
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

Run with Gunicorn:

```bash
gunicorn -c gunicorn.conf.py app:app
```

### 2. Using Nginx as Reverse Proxy

Install Nginx:

```bash
# Ubuntu/Debian
sudo apt-get install nginx

# CentOS/RHEL
sudo yum install nginx
```

Create Nginx configuration `/etc/nginx/sites-available/court-data-fetcher`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/court_data_fetcher/static;
        expires 30d;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/court-data-fetcher /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3. Using Systemd Service

Create `/etc/systemd/system/court-data-fetcher.service`:

```ini
[Unit]
Description=Court Data Fetcher
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/court_data_fetcher
Environment=PATH=/path/to/court_data_fetcher/venv/bin
ExecStart=/path/to/court_data_fetcher/venv/bin/gunicorn -c gunicorn.conf.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable court-data-fetcher
sudo systemctl start court-data-fetcher
```

## Cloud Deployment

### 1. AWS EC2 Deployment

#### Launch EC2 Instance

```bash
# Connect to your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y python3 python3-pip python3-venv nginx git

# Install Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt-get update
sudo apt-get install -y google-chrome-stable
```

#### Deploy Application

```bash
# Clone repository
git clone <repository-url>
cd court_data_fetcher

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn



# Initialize database
python -c "from db import init_db; init_db()"

# Set up systemd service (as shown above)
# Set up Nginx (as shown above)
```

### 2. Google Cloud Platform (GCP)

#### Using App Engine

Create `app.yaml`:

```yaml
runtime: python39
entrypoint: gunicorn -b :$PORT app:app

instance_class: F1

automatic_scaling:
  target_cpu_utilization: 0.6
  min_instances: 1
  max_instances: 10


```

Deploy:

```bash
gcloud app deploy
```

#### Using Compute Engine

Follow the AWS EC2 deployment steps, but use GCP Compute Engine instead.

### 3. Heroku Deployment

Create `Procfile`:

```
web: gunicorn app:app
```

Create `runtime.txt`:

```
python-3.9.18
```

Deploy:

```bash
heroku create your-app-name
git push heroku main
heroku open
```



## Monitoring and Logging

### 1. Application Logs

Configure logging in `app.py`:

```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/court_data_fetcher.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Court Data Fetcher startup')
```

### 2. Health Checks

Add health check endpoint:

```python
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
```

### 3. Monitoring with Prometheus

Install Prometheus client:

```bash
pip install prometheus_client
```

Add metrics:

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

@app.route('/metrics')
def metrics():
    return generate_latest()
```

## Security Considerations

### 1. HTTPS Configuration

For production, always use HTTPS:

```bash
# Install Certbot for Let's Encrypt
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### 2. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### 3. Database Security

For production, consider using PostgreSQL instead of SQLite:

```env
DATABASE_URL=postgresql://user:password@localhost/court_data_fetcher
```

## Backup and Recovery

### 1. Database Backup

```bash
# Create backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
sqlite3 case_data.db ".backup $BACKUP_DIR/case_data_$DATE.db"
```

### 2. Application Backup

```bash
# Backup application files
tar -czf backup_$(date +%Y%m%d).tar.gz court_data_fetcher/
```

## Troubleshooting

### Common Issues

1. **Chrome/Selenium Issues**
   ```bash
   # Check Chrome installation
   google-chrome --version
   
   # Check ChromeDriver
   chromedriver --version
   ```

2. **Permission Issues**
   ```bash
   # Fix file permissions
   sudo chown -R www-data:www-data /path/to/court_data_fetcher
   sudo chmod -R 755 /path/to/court_data_fetcher
   ```

3. **Port Conflicts**
   ```bash
   # Check if port 5000 is in use
   sudo netstat -tlnp | grep :5000
   
   # Kill process if needed
   sudo kill -9 <PID>
   ```

### Log Analysis

```bash
# View application logs
tail -f logs/court_data_fetcher.log

# View system logs
sudo journalctl -u court-data-fetcher -f

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Performance Optimization

### 1. Caching

Implement Redis caching:

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_data(key):
    return redis_client.get(key)

def set_cached_data(key, value, expire=3600):
    redis_client.setex(key, expire, value)
```

### 2. Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX idx_case_queries_timestamp ON case_queries(query_timestamp);
CREATE INDEX idx_case_queries_case_info ON case_queries(case_type, case_number, case_year);
```

### 3. Load Balancing

For high traffic, use multiple instances behind a load balancer:

```nginx
upstream court_data_fetcher {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
}

server {
    location / {
        proxy_pass http://court_data_fetcher;
    }
}
```
