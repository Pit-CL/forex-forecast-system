#!/bin/bash
# Forex Forecast System Monitoring Script

echo "============================================"
echo "Forex Forecast System Status Check"
echo "Time: $(date)"
echo "============================================"

# Check Docker containers
echo -e "\n[Docker Containers]"
docker compose -f /opt/forex-forecast-system/docker-compose-simple.yml ps

# Check API health
echo -e "\n[API Health Check]"
curl -s http://localhost:8000/api/health || echo "API not responding"

# Check Frontend
echo -e "\n[Frontend Check]"
curl -s -o /dev/null -w "Frontend HTTP Status: %{http_code}\n" http://localhost:3000 || echo "Frontend not responding"

# Check disk usage
echo -e "\n[Disk Usage]"
df -h /opt/forex-forecast-system

# Check memory usage
echo -e "\n[Memory Usage]"
free -h

echo "============================================"
