#!/bin/bash

# ============================================================
# GrandFlow - LOCAL MODE - DRAFT
# Full stack in Docker for non-technical users
# Everything runs inside Docker (no local services needed)
# ============================================================

set -e

# Relative paths below (compose file, env file) must resolve against the
# repo root regardless of the caller's cwd — .devrc aliases this script by
# absolute path, so `cd`ing to wherever the shell happens to be otherwise
# breaks (e.g. running local-infra-down from inside a service directory).
cd "$(dirname "${BASH_SOURCE[0]:-$0}")"

MODE="$1"
COMPOSE_FILE="docker-compose.local.yml"
ENV_FILE=".env.local"
COMPOSE="docker compose -f $COMPOSE_FILE --env-file $ENV_FILE"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

case "$MODE" in
    up)
        print_header "Starting LOCAL MODE"
        print_info "Building and starting all services (this may take a few minutes)..."
        DOCKER_BUILDKIT=1 $COMPOSE up -d --build
        print_success "All services started!"
        echo ""
        echo -e "${GREEN}LOCAL MODE is ready!${NC}"
        echo ""
        echo -e "${YELLOW}Available endpoints:${NC}"
        echo "  Frontend:           http://localhost:4000"
        echo "  Nginx Proxy:        http://localhost:9082"
        echo "  Users Service:      http://localhost:9000"
        echo "  Budget Service:     http://localhost:9001"
        echo "  AI Service:         http://localhost:9002"
        echo "  RabbitMQ (AMQP):    localhost:5673"
        echo "  RabbitMQ (UI):      http://localhost:15673"
        echo "  MinIO (S3 API):     localhost:9010"
        echo "  MinIO Console:      http://localhost:9011 (minioadmin:minioadmin)"
        echo "  Celery Worker:      running in Docker (no exposed port)"
        echo "  Celery Beat:        running in Docker (no exposed port)"
        echo ""
        echo -e "${YELLOW}Database:${NC}"
        echo "  Host:     localhost:5433"
        echo "  User:     postgres"
        echo "  Password: postgres"
        echo "  Databases: grandflow_users, grandflow_budget, grandflow_ai"
        ;;

    down)
        print_header "Stopping LOCAL MODE"
        $COMPOSE down
        print_success "LOCAL MODE stopped"
        ;;

    logs)
        SERVICE="$2"
        if [ -z "$SERVICE" ]; then
            $COMPOSE logs -f
        else
            $COMPOSE logs -f "$SERVICE"
        fi
        ;;

    status)
        print_header "LOCAL MODE Status"
        $COMPOSE ps
        ;;

    rebuild)
        print_header "Rebuilding LOCAL MODE containers"
        DOCKER_BUILDKIT=1 $COMPOSE build --no-cache
        print_success "Containers rebuilt"
        ;;

    clean)
        print_header "Cleaning up LOCAL MODE"
        $COMPOSE down -v
        print_success "LOCAL MODE cleaned (volumes removed)"
        ;;

    shell)
        SERVICE="${2:-users}"
        print_info "Opening shell in $SERVICE container..."
        $COMPOSE exec "$SERVICE" /bin/bash
        ;;

    *)
        echo "Usage: ./local.sh {up|down|logs|status|rebuild|clean|shell}"
        echo ""
        echo "Commands:"
        echo "  up       - Start all services (full stack)"
        echo "  down     - Stop all services"
        echo "  logs [SERVICE] - View logs (optional: specify service)"
        echo "  status   - Show container status"
        echo "  rebuild  - Rebuild containers without cache"
        echo "  clean    - Stop and remove volumes"
        echo "  shell [SERVICE] - Open shell in a container (default: users)"
        exit 1
        ;;
esac
