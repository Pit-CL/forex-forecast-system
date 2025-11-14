#!/bin/bash
###############################################################################
# Host System Cron Audit Script
#
# This script audits the host system for any forex-related crons that should
# be running inside Docker containers instead. It helps maintain the
# Docker-first architecture principle.
#
# Usage: sudo ./audit_host_crons.sh [--clean]
#        --clean: Actually remove forex-related crons (dry-run by default)
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Mode: dry-run by default
CLEAN_MODE=false
if [[ "$1" == "--clean" ]]; then
    CLEAN_MODE=true
fi

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}       Host System Cron Audit Tool${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

if $CLEAN_MODE; then
    echo -e "${YELLOW}⚠️  Running in CLEAN MODE - Will remove forex crons${NC}"
else
    echo -e "${GREEN}✓ Running in DRY-RUN MODE - No changes will be made${NC}"
    echo -e "   To actually clean, run: sudo $0 --clean"
fi
echo ""

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}This script must be run as root (use sudo)${NC}"
        exit 1
    fi
}

# Function to log findings
log_finding() {
    local level=$1
    local message=$2
    case $level in
        ERROR)
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        WARNING)
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        OK)
            echo -e "${GREEN}[OK]${NC} $message"
            ;;
        INFO)
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
    esac
}

# Patterns that indicate forex-related crons
FOREX_PATTERNS=(
    "forex"
    "forecast_with_ensemble"
    "auto_retrain"
    "send_.*_email"
    "daily_dashboard"
    "USD.*CLP"
    "copper_report"
    "unified_email"
)

# Check if string matches any forex pattern
is_forex_related() {
    local line=$1
    for pattern in "${FOREX_PATTERNS[@]}"; do
        if echo "$line" | grep -qi "$pattern"; then
            return 0
        fi
    done
    return 1
}

# Audit user crontabs
audit_user_crons() {
    echo -e "${BLUE}=== Checking User Crontabs ===${NC}"

    local found_issues=false

    # Check all user crontabs
    for user_cron in /var/spool/cron/crontabs/*; do
        if [[ -f "$user_cron" ]]; then
            local username=$(basename "$user_cron")
            local temp_file="/tmp/cron_audit_${username}_$$"
            local forex_lines=""

            while IFS= read -r line; do
                # Skip comments and empty lines for checking
                if [[ ! "$line" =~ ^# ]] && [[ ! -z "$line" ]]; then
                    if is_forex_related "$line"; then
                        forex_lines+="    $line\n"
                        found_issues=true
                    fi
                fi
            done < "$user_cron"

            if [[ ! -z "$forex_lines" ]]; then
                log_finding WARNING "User '$username' has forex-related crons:"
                echo -e "$forex_lines"

                if $CLEAN_MODE; then
                    # Create cleaned version
                    > "$temp_file"
                    while IFS= read -r line; do
                        if [[ "$line" =~ ^# ]] || [[ -z "$line" ]] || ! is_forex_related "$line"; then
                            echo "$line" >> "$temp_file"
                        else
                            echo "# REMOVED BY AUDIT: $line" >> "$temp_file"
                        fi
                    done < "$user_cron"

                    # Install cleaned crontab
                    crontab -u "$username" "$temp_file"
                    rm -f "$temp_file"
                    log_finding OK "Cleaned crontab for user '$username'"
                fi
            else
                log_finding OK "User '$username' crontab is clean"
            fi
        fi
    done

    if ! $found_issues; then
        log_finding OK "No forex-related crons found in user crontabs"
    fi
    echo ""
}

# Audit system-wide cron directories
audit_system_crons() {
    echo -e "${BLUE}=== Checking System Cron Directories ===${NC}"

    local dirs=(
        "/etc/cron.d"
        "/etc/cron.hourly"
        "/etc/cron.daily"
        "/etc/cron.weekly"
        "/etc/cron.monthly"
    )

    local found_issues=false

    for dir in "${dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            log_finding INFO "Checking $dir..."

            for file in "$dir"/*; do
                if [[ -f "$file" ]] && [[ ! "$file" == *.bak ]]; then
                    local filename=$(basename "$file")

                    # Check filename
                    if is_forex_related "$filename"; then
                        log_finding WARNING "Found forex-related file: $file"
                        found_issues=true

                        if $CLEAN_MODE; then
                            mv "$file" "${file}.removed_$(date +%Y%m%d_%H%M%S)"
                            log_finding OK "Renamed to ${file}.removed_*"
                        fi
                    else
                        # Check file contents
                        if grep -q -E "(forex|forecast_with_ensemble|auto_retrain)" "$file" 2>/dev/null; then
                            log_finding WARNING "File $file contains forex-related entries"
                            grep -n -E "(forex|forecast_with_ensemble|auto_retrain)" "$file" | sed 's/^/        Line /'
                            found_issues=true
                        fi
                    fi
                fi
            done
        fi
    done

    if ! $found_issues; then
        log_finding OK "No forex-related crons found in system directories"
    fi
    echo ""
}

# List Docker container crons (for reference)
show_docker_crons() {
    echo -e "${BLUE}=== Docker Container Crons (For Reference) ===${NC}"
    echo -e "${GREEN}These SHOULD be running inside containers:${NC}"

    local containers=("forex-7d" "forex-15d" "forex-30d" "forex-90d")

    for container in "${containers[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            echo -e "\n${BLUE}Container: $container${NC}"
            docker exec "$container" crontab -l 2>/dev/null | head -5 || echo "    Unable to read crontab"
        else
            echo -e "\n${YELLOW}Container '$container' is not running${NC}"
        fi
    done
    echo ""
}

# Show recommended infrastructure crons
show_recommended_crons() {
    echo -e "${BLUE}=== Recommended Host System Crons ===${NC}"
    echo -e "${GREEN}These types of crons SHOULD run on the host:${NC}"
    echo ""
    cat << 'EOF'
# Docker maintenance
0 3 * * 0 docker system prune -af --volumes

# Backup Docker volumes
0 2 * * * /usr/local/bin/backup-docker-volumes.sh

# Monitor Docker health
*/5 * * * * /usr/local/bin/check-docker-health.sh

# System updates (Ubuntu/Debian)
0 4 * * 0 apt-get update && apt-get upgrade -y

# Log rotation
0 0 * * * logrotate /etc/logrotate.conf

# SSL certificate renewal (if using Certbot)
0 0,12 * * * certbot renew --quiet

# Disk usage alert
0 8 * * * df -h | awk '$5 > 80 {print $0}' | mail -s "Disk Usage Alert" admin@example.com
EOF
    echo ""
}

# Generate summary report
generate_summary() {
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}                   SUMMARY${NC}"
    echo -e "${BLUE}=================================================${NC}"
    echo ""

    if $CLEAN_MODE; then
        echo -e "${GREEN}✓ Audit completed in CLEAN MODE${NC}"
        echo -e "  Forex-related crons have been removed/disabled"
    else
        echo -e "${YELLOW}✓ Audit completed in DRY-RUN MODE${NC}"
        echo -e "  No changes were made"
    fi

    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Ensure Docker containers have the correct crontabs"
    echo "2. Restart Docker containers to apply new schedules"
    echo "3. Monitor logs to verify crons are running correctly"
    echo "4. Set up infrastructure monitoring crons on host"
    echo ""

    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  docker exec forex-7d crontab -l     # View container crons"
    echo "  docker restart forex-7d              # Restart container"
    echo "  docker logs forex-7d --tail 50 -f   # Monitor container logs"
    echo "  journalctl -u docker -f             # Monitor Docker service"
}

# Main execution
main() {
    check_root

    echo -e "${BLUE}Starting audit at $(date)${NC}"
    echo ""

    audit_user_crons
    audit_system_crons
    show_docker_crons
    show_recommended_crons
    generate_summary

    echo -e "${GREEN}Audit completed at $(date)${NC}"
}

# Run main function
main