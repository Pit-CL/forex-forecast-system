# Docker Deployment Guide

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Build Images

```bash
./docker-run.sh build
```

### 3. Run Services

```bash
# Run 7-day forecaster
./docker-run.sh 7d

# Run 12-month forecaster
./docker-run.sh 12m

# Run importer report
./docker-run.sh importer
```

## Architecture

The system uses 3 independent Docker containers:

1. **forecaster-7d**: Short-term (7-day) USD/CLP forecast
   - Runs daily at 08:00 Chile time
   - Generates PDF report with charts
   - Sends email notifications

2. **forecaster-12m**: Long-term (12-month) USD/CLP forecast
   - Runs monthly on 1st day at 09:00
   - Strategic outlook for importers
   - Detailed methodology and drivers

3. **importer-report**: Macro environment analysis
   - Runs monthly on 10th day at 10:00
   - Broader economic context
   - Combines technical and fundamental analysis

## Docker Compose Structure

```yaml
services:
  forecaster-7d:
    build: Dockerfile.7d
    volumes:
      - ./data:/app/data          # Data persistence
      - ./output:/app/output      # PDF reports
      - ./logs:/app/logs          # Logging
    environment:
      - FRED_API_KEY
      - NEWS_API_KEY
      - GMAIL credentials
```

## Volume Mounts

| Volume | Purpose | Notes |
|--------|---------|-------|
| `./data` | Cached historical data | Reduces API calls |
| `./output` | Generated PDF reports | Organized by date |
| `./logs` | Application logs | Rotation recommended |
| `./.env` | Configuration | Read-only mount |

## Environment Variables

Required in `.env`:

```bash
# API Keys
FRED_API_KEY=your_fred_key
NEWS_API_KEY=your_news_key

# Email (Gmail App Password)
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=app_specific_password
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com

# Configuration
ENVIRONMENT=production
REPORT_TIMEZONE=America/Santiago
```

## Running Services

### Manual Execution

```bash
# Run once and exit
./docker-run.sh 7d
./docker-run.sh 12m
./docker-run.sh importer
```

### View Logs

```bash
./docker-run.sh logs 7d
./docker-run.sh logs 12m
./docker-run.sh logs importer
```

### Clean Up

```bash
# Remove containers
./docker-run.sh clean

# Remove images
docker-compose down --rmi all
```

## Automated Scheduling

### Using Cron (Recommended)

Add to crontab:

```bash
# 7-day forecast: Daily at 08:00 Chile time
0 8 * * * cd /path/to/forex-forecast-system && ./docker-run.sh 7d >> logs/cron-7d.log 2>&1

# 12-month forecast: Monthly on 1st at 09:00
0 9 1 * * cd /path/to/forex-forecast-system && ./docker-run.sh 12m >> logs/cron-12m.log 2>&1

# Importer report: Monthly on 10th at 10:00
0 10 10 * * cd /path/to/forex-forecast-system && ./docker-run.sh importer >> logs/cron-importer.log 2>&1
```

### Using systemd Timers

Create `/etc/systemd/system/forex-7d.service`:

```ini
[Unit]
Description=USD/CLP 7-Day Forecaster
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/path/to/forex-forecast-system
ExecStart=/path/to/forex-forecast-system/docker-run.sh 7d
User=your-user

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/forex-7d.timer`:

```ini
[Unit]
Description=Run USD/CLP 7-Day Forecaster Daily
Requires=forex-7d.service

[Timer]
OnCalendar=daily
OnCalendar=08:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:

```bash
sudo systemctl enable forex-7d.timer
sudo systemctl start forex-7d.timer
```

## Troubleshooting

### PDF Generation Fails

Ensure WeasyPrint dependencies are installed:

```bash
docker-compose exec forecaster-7d apt-get update
docker-compose exec forecaster-7d apt-get install -y libcairo2 libpango-1.0-0
```

### API Rate Limits

Check data caching:

```bash
ls -lh data/warehouse/
```

Cached data reduces API calls. Default TTL: 30 minutes.

### Email Fails

Test Gmail App Password:

```bash
docker-compose run --rm forecaster-7d python -c "
from forex_core.notifications import EmailSender
from forex_core.config import get_settings
sender = EmailSender(get_settings())
print('✓ Email configured correctly')
"
```

### View Container Logs

```bash
# Real-time logs
docker-compose logs -f forecaster-7d

# Last 100 lines
docker-compose logs --tail=100 forecaster-7d
```

## Development

### Run Tests in Docker

```bash
./docker-run.sh test
```

### Access Container Shell

```bash
docker-compose run --rm forecaster-7d /bin/bash
```

### Mount Local Code (Development)

Edit `docker-compose.yml`:

```yaml
volumes:
  - ./src:/app/src  # Mount source for live development
```

## Production Deployment

### Security Checklist

- [ ] `.env` file has restricted permissions (600)
- [ ] API keys are valid and not rate-limited
- [ ] Gmail App Password is configured (not account password)
- [ ] Email recipients are verified
- [ ] Data volumes have sufficient disk space
- [ ] Log rotation is configured
- [ ] Cron/systemd timers are tested
- [ ] Backup strategy for historical data

### Monitoring

Check service health:

```bash
# Docker health check
docker-compose ps

# Recent logs
./docker-run.sh logs 7d | tail -50

# Output files
ls -lh output/
```

### Backup

```bash
# Backup historical data
tar -czf forex-data-backup-$(date +%Y%m%d).tar.gz data/

# Backup reports
tar -czf forex-reports-$(date +%Y%m%d).tar.gz output/
```

## Performance

### Image Sizes

| Image | Size | Build Time |
|-------|------|------------|
| forecaster-7d | ~800MB | ~3min |
| forecaster-12m | ~800MB | ~3min |
| importer-report | ~800MB | ~3min |

### Runtime

| Service | Avg Duration | Memory |
|---------|--------------|--------|
| 7-day forecast | 30-60s | ~300MB |
| 12-month forecast | 60-120s | ~400MB |
| Importer report | 45-90s | ~350MB |

## Support

For issues:

1. Check logs: `./docker-run.sh logs <service>`
2. Verify .env configuration
3. Test API keys
4. Review GitHub issues: https://github.com/yourusername/forex-forecast-system/issues
