#!/usr/bin/env bash
#
# Docker helper script for USD/CLP Forecasting System
#
# Usage:
#   ./docker-run.sh build          # Build all images
#   ./docker-run.sh 7d             # Run 7-day forecaster
#   ./docker-run.sh 12m            # Run 12-month forecaster
#   ./docker-run.sh importer       # Run importer report
#   ./docker-run.sh logs 7d        # View logs for 7d forecaster
#   ./docker-run.sh clean          # Remove all containers

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo "Please create .env from .env.example and configure your API keys"
    exit 1
fi

case "$1" in
    build)
        echo -e "${GREEN}Building all Docker images...${NC}"
        docker-compose build
        echo -e "${GREEN}✓ Build complete${NC}"
        ;;

    7d)
        echo -e "${GREEN}Running 7-day forecaster...${NC}"
        docker-compose --profile manual run --rm forecaster-7d
        echo -e "${GREEN}✓ 7-day forecast complete${NC}"
        ;;

    12m)
        echo -e "${GREEN}Running 12-month forecaster...${NC}"
        docker-compose --profile manual run --rm forecaster-12m
        echo -e "${GREEN}✓ 12-month forecast complete${NC}"
        ;;

    importer)
        echo -e "${GREEN}Running importer report...${NC}"
        docker-compose --profile manual run --rm importer-report
        echo -e "${GREEN}✓ Importer report complete${NC}"
        ;;

    logs)
        if [ -z "$2" ]; then
            echo -e "${RED}ERROR: Please specify service (7d, 12m, importer)${NC}"
            exit 1
        fi

        case "$2" in
            7d)
                docker-compose logs -f forecaster-7d
                ;;
            12m)
                docker-compose logs -f forecaster-12m
                ;;
            importer)
                docker-compose logs -f importer-report
                ;;
            *)
                echo -e "${RED}ERROR: Unknown service: $2${NC}"
                exit 1
                ;;
        esac
        ;;

    clean)
        echo -e "${YELLOW}Removing all containers...${NC}"
        docker-compose down
        echo -e "${GREEN}✓ Containers removed${NC}"
        ;;

    test)
        echo -e "${GREEN}Running tests in Docker...${NC}"
        docker-compose run --rm forecaster-7d pytest tests/ -v
        ;;

    *)
        echo "USD/CLP Forecasting System - Docker Runner"
        echo ""
        echo "Usage:"
        echo "  ./docker-run.sh build           Build all images"
        echo "  ./docker-run.sh 7d              Run 7-day forecaster"
        echo "  ./docker-run.sh 12m             Run 12-month forecaster"
        echo "  ./docker-run.sh importer        Run importer report"
        echo "  ./docker-run.sh logs <service>  View logs (7d|12m|importer)"
        echo "  ./docker-run.sh clean           Remove all containers"
        echo "  ./docker-run.sh test            Run tests in Docker"
        echo ""
        exit 1
        ;;
esac
