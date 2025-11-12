#!/bin/bash
# Deploy USD/CLP Professional Refinements to Vultr
# This script pulls the latest changes, rebuilds the container, and generates a test PDF

set -e  # Exit on any error

echo "=========================================="
echo "USD/CLP Professional Refinements Deployment"
echo "=========================================="
echo ""

# Check if we're on Vultr (optional, can be run locally with ssh)
if [ -z "$VULTR_HOST" ]; then
    VULTR_HOST="reporting"  # Default ssh alias
fi

echo "Target: $VULTR_HOST"
echo "Branch: develop"
echo ""

# SSH into Vultr and execute deployment commands
ssh "$VULTR_HOST" << 'ENDSSH'
set -e

echo "[1/6] Navigating to project directory..."
cd /home/deployer/forex-forecast-system

echo "[2/6] Pulling latest changes from develop..."
git fetch origin
git checkout develop
git pull origin develop

echo "[3/6] Checking out changes..."
git log -1 --oneline

echo "[4/6] Rebuilding forecaster-7d container..."
docker compose build forecaster-7d

echo "[5/6] Generating test PDF (without email)..."
docker compose run --rm forecaster-7d python -m services.forecaster_7d.cli run --skip-email

echo "[6/6] Verifying PDF generation..."
latest_pdf=$(ls -t reports/usdclp_report_7d_*.pdf 2>/dev/null | head -1)

if [ -z "$latest_pdf" ]; then
    echo "ERROR: No PDF found in reports/"
    exit 1
fi

pdf_size=$(du -h "$latest_pdf" | cut -f1)
echo ""
echo "=========================================="
echo "DEPLOYMENT SUCCESSFUL"
echo "=========================================="
echo "PDF: $latest_pdf"
echo "Size: $pdf_size"
echo ""
echo "Next steps:"
echo "1. Download PDF: scp $VULTR_HOST:/home/deployer/forex-forecast-system/$latest_pdf ."
echo "2. Verify dates are legible in multi-panel charts"
echo "3. Check methodology section is expanded"
echo "4. Confirm chart explanations are present"
echo "5. Verify source captions on all charts"
echo ""
ENDSSH

echo ""
echo "Deployment script completed on Vultr!"
echo ""
echo "To download the PDF locally, run:"
echo "scp $VULTR_HOST:/home/deployer/forex-forecast-system/reports/usdclp_report_7d_*.pdf ."
