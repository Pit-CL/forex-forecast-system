# Vultr Production Deployment Guide

**System:** USD/CLP Forex Forecasting System
**Server:** Vultr VPS
**Environment:** Production
**Last Updated:** 2025-11-12

---

## Server Information

### Access Details
```bash
# SSH Configuration
Host: reporting (configured in ~/.ssh/config)
User: deployer
Server IP: [Vultr VPS IP]
SSH Key: ~/.ssh/id_rsa

# Quick Access
ssh reporting
```

### Server Specifications
- **Provider:** Vultr
- **OS:** Ubuntu 22.04 LTS
- **Python:** 3.11+
- **vCPU:** 2 cores
- **RAM:** 4 GB
- **Storage:** 80 GB SSD
- **Network:** 1 Gbps

### Project Location
```
/home/deployer/forex-forecast-system/
```

---

## Initial Server Setup

### 1. Server Provisioning

```bash
# Create Vultr VPS
# - OS: Ubuntu 22.04 LTS
# - Plan: 2 vCPU, 4 GB RAM, 80 GB SSD
# - Region: Nearest to Chile (if available) or US West

# SSH to server
ssh root@<server-ip>

# Create deployer user
adduser deployer
usermod -aG sudo deployer

# Setup SSH key authentication
mkdir -p /home/deployer/.ssh
cp ~/.ssh/authorized_keys /home/deployer/.ssh/
chown -R deployer:deployer /home/deployer/.ssh
chmod 700 /home/deployer/.ssh
chmod 600 /home/deployer/.ssh/authorized_keys

# Switch to deployer user
su - deployer
```

### 2. System Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.11+
sudo apt-get install -y python3 python3-pip python3-venv

# Install WeasyPrint system dependencies
sudo apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info

# Install Git
sudo apt-get install -y git

# Install build dependencies
sudo apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

# Optional: Install Docker (if using Docker execution)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker deployer
```

### 3. Clone Repository

```bash
# Switch to deployer home
cd /home/deployer

# Clone repository
git clone https://github.com/Pit-CL/forex-forecast-system.git
cd forex-forecast-system

# Verify structure
ls -la
```

### 4. Python Environment Setup

```bash
cd /home/deployer/forex-forecast-system

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from forex_core.reporting import ReportBuilder; print('OK')"
python -c "import weasyprint; print('WeasyPrint OK')"
```

### 5. Environment Configuration

```bash
# Create .env file
cd /home/deployer/forex-forecast-system
nano .env
```

**Contents:**
```bash
# API Keys
FRED_API_KEY=your_fred_api_key_here
NEWS_API_KEY=your_news_api_key_here

# Email Configuration (Gmail App Password)
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your_app_password_here
EMAIL_RECIPIENTS=["email1@example.com","email2@example.com"]

# Environment
ENVIRONMENT=production
REPORT_TIMEZONE=America/Santiago
LOG_LEVEL=INFO

# Optional: Data warehouse
DATA_WAREHOUSE_PATH=/home/deployer/forex-forecast-system/data/warehouse
```

**Obtain API Keys:**
1. **FRED API:** https://fred.stlouisfed.org/docs/api/api_key.html
2. **News API:** https://newsapi.org/register
3. **Gmail App Password:** https://myaccount.google.com/apppasswords

### 6. Directory Setup

```bash
cd /home/deployer/forex-forecast-system

# Create necessary directories
mkdir -p data/warehouse
mkdir -p reports
mkdir -p logs
mkdir -p output

# Set permissions
chmod 755 data reports logs output
chmod 600 .env
```

---

## Deployment Process

### Standard Deployment (Code Updates)

```bash
# 1. SSH to server
ssh reporting

# 2. Navigate to project
cd /home/deployer/forex-forecast-system

# 3. Pull latest changes
git pull origin main

# 4. Activate virtual environment
source venv/bin/activate

# 5. Update dependencies
pip install -r requirements.txt --upgrade

# 6. Test execution
python -m services.forecaster_7d.cli validate

# 7. Run manual test
python -m services.forecaster_7d.cli run

# 8. Verify output
ls -lth reports/ | head -5
```

### Emergency Rollback

```bash
# 1. SSH to server
ssh reporting
cd /home/deployer/forex-forecast-system

# 2. Check git log
git log --oneline -10

# 3. Rollback to previous commit
git reset --hard <commit-hash>

# 4. Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt --force-reinstall

# 5. Verify
python -m services.forecaster_7d.cli validate
```

---

## Cron Configuration

### Automated Execution Script

**File:** `/home/deployer/forex-forecast-system/run_7d_forecast.sh`

```bash
#!/bin/bash
# USD/CLP 7-day Forecast Execution Script
# Runs via cron daily at 8 AM Chile time

set -e  # Exit on any error

# Configuration
PROJECT_DIR="/home/deployer/forex-forecast-system"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Navigate to project
cd "$PROJECT_DIR"

# Timestamp
echo "=== Starting USD/CLP 7-day forecast: $(date) ===" >> "$LOG_DIR/cron_7d.log"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Run forecast (output to timestamped log)
python -m services.forecaster_7d.cli run 2>&1 | tee -a "$LOG_DIR/forecast_7d_$TIMESTAMP.log"

# Check exit code
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "=== Completed successfully: $(date) ===" >> "$LOG_DIR/cron_7d.log"
else
    echo "=== FAILED with exit code $EXIT_CODE: $(date) ===" >> "$LOG_DIR/cron_7d.log"
    exit $EXIT_CODE
fi
```

**Setup:**
```bash
# Create script
nano /home/deployer/forex-forecast-system/run_7d_forecast.sh

# Make executable
chmod +x /home/deployer/forex-forecast-system/run_7d_forecast.sh

# Test manually
./run_7d_forecast.sh
```

### Crontab Configuration

```bash
# Edit crontab
crontab -e

# Add entries (paste the following)
```

**Crontab Entries:**
```cron
# USD/CLP 7-day forecast - Daily at 8 AM Chile time (America/Santiago)
# Note: Cron uses server timezone, ensure server is set to America/Santiago
0 8 * * * cd /home/deployer/forex-forecast-system && /home/deployer/forex-forecast-system/run_7d_forecast.sh >> /home/deployer/forex-forecast-system/logs/cron_7d.log 2>&1

# Cleanup old logs (>30 days) - Daily at midnight
0 0 * * * find /home/deployer/forex-forecast-system/logs/ -name "*.log" -mtime +30 -delete

# Cleanup old PDFs (>90 days) - Daily at midnight
0 0 * * * find /home/deployer/forex-forecast-system/reports/ -name "*.pdf" -mtime +90 -delete

# Optional: 12-month forecast - Monthly on 1st at 9 AM
# 0 9 1 * * cd /home/deployer/forex-forecast-system && /home/deployer/forex-forecast-system/run_12m_forecast.sh >> /home/deployer/forex-forecast-system/logs/cron_12m.log 2>&1

# Optional: Importer report - Monthly on 10th at 10 AM
# 0 10 10 * * cd /home/deployer/forex-forecast-system && /home/deployer/forex-forecast-system/run_importer.sh >> /home/deployer/forex-forecast-system/logs/cron_importer.log 2>&1
```

### Verify Cron Setup

```bash
# List cron jobs
crontab -l

# Check cron service status
sudo systemctl status cron

# View cron execution log
tail -f /var/log/syslog | grep CRON

# Test cron schedule (dry run)
# Use https://crontab.guru/ to verify schedule syntax
```

### Timezone Configuration

```bash
# Check current timezone
timedatectl

# Set timezone to Chile (if not already set)
sudo timedatectl set-timezone America/Santiago

# Verify
date
# Should show Chile time
```

---

## Monitoring and Maintenance

### Daily Health Checks

```bash
# 1. Check last execution time
ls -lt /home/deployer/forex-forecast-system/reports/ | head -5

# 2. Check for recent errors
tail -100 /home/deployer/forex-forecast-system/logs/cron_7d.log | grep -i error

# 3. Verify PDF was generated today
ls /home/deployer/forex-forecast-system/reports/usdclp_report_7d_$(date +%Y%m%d)*.pdf

# 4. Check log file sizes
du -sh /home/deployer/forex-forecast-system/logs/
du -sh /home/deployer/forex-forecast-system/reports/
```

### Log Monitoring

```bash
# Real-time log monitoring
tail -f /home/deployer/forex-forecast-system/logs/cron_7d.log

# View last execution details
ls -t /home/deployer/forex-forecast-system/logs/forecast_7d_*.log | head -1 | xargs cat

# Search for errors in recent logs
grep -i "error\|exception\|failed" /home/deployer/forex-forecast-system/logs/cron_7d.log

# Check execution times
grep "Starting\|Completed" /home/deployer/forex-forecast-system/logs/cron_7d.log | tail -20
```

### System Resource Monitoring

```bash
# Disk space
df -h /home/deployer/forex-forecast-system

# Data warehouse size
du -sh /home/deployer/forex-forecast-system/data/

# Reports directory size
du -sh /home/deployer/forex-forecast-system/reports/

# Memory usage
free -h

# CPU load
top
htop  # if installed

# Process monitoring (while running)
ps aux | grep python
```

### Downloading PDFs

```bash
# From local machine

# Download latest PDF (today)
scp reporting:/home/deployer/forex-forecast-system/reports/usdclp_report_7d_$(date +%Y%m%d)*.pdf ~/Downloads/

# Download specific date
scp reporting:/home/deployer/forex-forecast-system/reports/usdclp_report_7d_20251112*.pdf ~/Downloads/

# Download all PDFs from last 7 days
scp reporting:/home/deployer/forex-forecast-system/reports/usdclp_report_7d_*.pdf ~/Downloads/

# View available PDFs
ssh reporting 'ls -lth /home/deployer/forex-forecast-system/reports/ | head -10'
```

---

## Troubleshooting Guide

### Issue: PDF Not Generated

**Symptoms:** No PDF file for today's date

**Diagnosis:**
```bash
# 1. Check if cron executed
grep "$(date +%Y-%m-%d)" /home/deployer/forex-forecast-system/logs/cron_7d.log

# 2. Check detailed log
ls -t /home/deployer/forex-forecast-system/logs/forecast_7d_*.log | head -1 | xargs cat

# 3. Verify cron is running
systemctl status cron
```

**Solutions:**

1. **Cron not executing:**
   ```bash
   # Restart cron service
   sudo systemctl restart cron

   # Verify crontab
   crontab -l
   ```

2. **Script execution error:**
   ```bash
   # Run manually to see errors
   cd /home/deployer/forex-forecast-system
   ./run_7d_forecast.sh
   ```

3. **Python errors:**
   ```bash
   # Check virtual environment
   source venv/bin/activate
   python -m services.forecaster_7d.cli validate
   ```

---

### Issue: API Key Errors

**Symptoms:** Errors like "Invalid API key" or "API request failed"

**Diagnosis:**
```bash
# Verify .env file
cat /home/deployer/forex-forecast-system/.env

# Test API keys manually
python3 << EOF
from forex_core.config import get_settings
settings = get_settings()
print(f"FRED API Key: {settings.fred_api_key[:8]}...")
print(f"News API Key: {settings.news_api_key[:8]}...")
EOF
```

**Solutions:**

1. **Update .env file:**
   ```bash
   nano /home/deployer/forex-forecast-system/.env
   # Update expired/invalid keys
   ```

2. **Test API connectivity:**
   ```bash
   # Test FRED API
   curl "https://api.stlouisfed.org/fred/series/observations?series_id=DEXCHUS&api_key=YOUR_KEY&file_type=json"

   # Test News API
   curl "https://newsapi.org/v2/everything?q=chile&apiKey=YOUR_KEY"
   ```

---

### Issue: WeasyPrint Errors

**Symptoms:** "WeasyPrint not found" or PDF generation fails

**Diagnosis:**
```bash
# Test WeasyPrint
python3 -c "import weasyprint; print(weasyprint.VERSION)"

# Check system dependencies
dpkg -l | grep -E 'libcairo|libpango|libgdk'
```

**Solutions:**

1. **Reinstall system dependencies:**
   ```bash
   sudo apt-get install --reinstall \
       libcairo2 \
       libpango-1.0-0 \
       libpangocairo-1.0-0 \
       libgdk-pixbuf-2.0-0
   ```

2. **Reinstall WeasyPrint:**
   ```bash
   source /home/deployer/forex-forecast-system/venv/bin/activate
   pip uninstall weasyprint
   pip install weasyprint==66.0
   ```

---

### Issue: Out of Memory

**Symptoms:** Process killed, "Memory Error" in logs

**Diagnosis:**
```bash
# Check memory usage
free -h

# Check swap
swapon --show

# View kernel logs
dmesg | grep -i "out of memory"
```

**Solutions:**

1. **Add swap space:**
   ```bash
   # Create 2GB swap
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile

   # Make permanent
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

2. **Optimize data loading:**
   - Reduce historical data window
   - Clear old data cache
   ```bash
   rm -rf /home/deployer/forex-forecast-system/data/warehouse/*
   ```

---

### Issue: Disk Space Full

**Symptoms:** "No space left on device"

**Diagnosis:**
```bash
# Check disk usage
df -h

# Find large directories
du -sh /home/deployer/forex-forecast-system/* | sort -h
```

**Solutions:**

1. **Clean old PDFs:**
   ```bash
   # Remove PDFs older than 90 days
   find /home/deployer/forex-forecast-system/reports/ -name "*.pdf" -mtime +90 -delete
   ```

2. **Clean old logs:**
   ```bash
   # Remove logs older than 30 days
   find /home/deployer/forex-forecast-system/logs/ -name "*.log" -mtime +30 -delete
   ```

3. **Clear data cache:**
   ```bash
   # Clear old cached data
   rm -rf /home/deployer/forex-forecast-system/data/warehouse/*
   # Data will re-download on next execution
   ```

---

### Issue: Git Pull Conflicts

**Symptoms:** "error: Your local changes would be overwritten"

**Solutions:**

1. **Stash local changes:**
   ```bash
   git stash
   git pull origin main
   git stash pop
   ```

2. **Force reset (DESTRUCTIVE):**
   ```bash
   git fetch origin
   git reset --hard origin/main
   ```

---

## Security Best Practices

### 1. File Permissions

```bash
# Ensure proper ownership
sudo chown -R deployer:deployer /home/deployer/forex-forecast-system

# Secure .env file
chmod 600 /home/deployer/forex-forecast-system/.env

# Secure SSH keys (if any)
chmod 600 ~/.ssh/*
chmod 700 ~/.ssh
```

### 2. Firewall Configuration

```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (if web dashboard added later)
# sudo ufw allow 80/tcp
# sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

### 3. Automatic Security Updates

```bash
# Enable unattended upgrades
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 4. Log Rotation

```bash
# Create logrotate config
sudo nano /etc/logrotate.d/forex-forecast

# Add:
/home/deployer/forex-forecast-system/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 deployer deployer
}
```

---

## Backup and Disaster Recovery

### Backup Strategy

```bash
# Create backup script
nano /home/deployer/backup_forex.sh
```

**Backup Script:**
```bash
#!/bin/bash
BACKUP_DIR="/home/deployer/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/home/deployer/forex-forecast-system"

mkdir -p "$BACKUP_DIR"

# Backup configuration and code
tar -czf "$BACKUP_DIR/forex_backup_$TIMESTAMP.tar.gz" \
    --exclude='venv' \
    --exclude='data/warehouse' \
    --exclude='*.pyc' \
    "$PROJECT_DIR"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/forex_backup_*.tar.gz | tail -n +8 | xargs -r rm

echo "Backup completed: $BACKUP_DIR/forex_backup_$TIMESTAMP.tar.gz"
```

**Setup Automated Backups:**
```bash
chmod +x /home/deployer/backup_forex.sh

# Add to crontab (weekly backups)
crontab -e
# Add line:
# 0 2 * * 0 /home/deployer/backup_forex.sh >> /home/deployer/backup.log 2>&1
```

### Disaster Recovery

**Complete System Restore:**

1. **Provision new server** (same specs)
2. **Run initial setup** (system dependencies, Python, etc.)
3. **Restore from backup:**
   ```bash
   # Copy backup to new server
   scp backup_file.tar.gz deployer@new-server:~/

   # SSH to new server
   ssh deployer@new-server

   # Extract
   tar -xzf backup_file.tar.gz -C /home/deployer/

   # Recreate virtual environment
   cd /home/deployer/forex-forecast-system
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Restore .env (from secure storage)
   nano .env  # Paste credentials

   # Setup cron
   crontab -e  # Add cron entries
   ```

---

## Performance Optimization

### 1. Data Caching

The system automatically caches data in `/home/deployer/forex-forecast-system/data/warehouse/`

**Manual Cache Management:**
```bash
# View cache size
du -sh /home/deployer/forex-forecast-system/data/warehouse/

# Clear specific data source
rm /home/deployer/forex-forecast-system/data/warehouse/fred_*.json

# Clear all cache (forces re-download)
rm -rf /home/deployer/forex-forecast-system/data/warehouse/*
```

### 2. Log Management

```bash
# Compress old logs
find /home/deployer/forex-forecast-system/logs/ -name "*.log" -mtime +7 -exec gzip {} \;

# Archive old PDFs
tar -czf reports_archive_$(date +%Y%m).tar.gz reports/*.pdf
mv reports_archive_*.tar.gz ~/archives/
```

### 3. Python Optimization

```bash
# Compile Python bytecode
cd /home/deployer/forex-forecast-system
source venv/bin/activate
python -m compileall src/
```

---

## Monitoring and Alerts (Advanced)

### Email Alerts on Failure

Create wrapper script for email notification:

```bash
nano /home/deployer/forex-forecast-system/run_7d_with_alerts.sh
```

**Script:**
```bash
#!/bin/bash
PROJECT_DIR="/home/deployer/forex-forecast-system"
LOG_FILE="$PROJECT_DIR/logs/cron_7d.log"

# Run forecast
"$PROJECT_DIR/run_7d_forecast.sh"
EXIT_CODE=$?

# Send email if failed
if [ $EXIT_CODE -ne 0 ]; then
    # Using sendmail or mailx
    echo "USD/CLP Forecast failed on $(date). Check logs at $LOG_FILE" | \
    mail -s "ALERT: Forecast Generation Failed" admin@example.com
fi

exit $EXIT_CODE
```

### Uptime Monitoring

Use external services like:
- **UptimeRobot** (free tier available)
- **Pingdom**
- **StatusCake**

Configure to check if PDF was generated daily:
```bash
# Create health check endpoint (simple HTTP server)
# Or use file timestamp check via UptimeRobot's keyword monitoring
```

---

## Useful Commands Reference

### Quick Reference Card

```bash
# === Access ===
ssh reporting

# === Navigation ===
cd /home/deployer/forex-forecast-system

# === Execution ===
./run_7d_forecast.sh                    # Manual run
python -m services.forecaster_7d.cli run  # Direct Python run

# === Monitoring ===
tail -f logs/cron_7d.log               # Watch logs
ls -lth reports/ | head -5             # Recent PDFs
du -sh data/ reports/ logs/            # Disk usage

# === Maintenance ===
git pull origin main                   # Update code
source venv/bin/activate              # Activate venv
pip install -r requirements.txt -U    # Update deps

# === Troubleshooting ===
crontab -l                            # View cron jobs
systemctl status cron                 # Cron service status
grep -i error logs/cron_7d.log       # Search errors
```

---

## Contact and Support

**GitHub Repository:** https://github.com/Pit-CL/forex-forecast-system

**Documentation:**
- System Architecture: `/docs/ARCHITECTURE.md`
- Docker Guide: `/docs/DOCKER.md`
- Migration Guide: `/MIGRATION_COMPLETE.md`

**Key Personnel:**
- Developer: [Your Name]
- Server Admin: deployer@vultr
- Email: rafael@cavara.cl, valentina@cavara.cl

---

**Last Updated:** 2025-11-12
**Document Version:** 1.0
**Deployment Status:** PRODUCTION ACTIVE
