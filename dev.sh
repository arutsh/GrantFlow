#!/bin/bash

# ============================================================
# GrandFlow - DEV MODE
# Infrastructure only: PostgreSQL, Redis, API Gateway, Nginx
# Frontend and Backend services run on local machine
# ============================================================

set -e

MODE="$1"
COMPOSE_FILE="docker-compose.dev.yml"
ENV_FILE=".env.dev"
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
        print_header "Starting DEV MODE"
        print_info "Starting infrastructure (DB, Redis, Nginx)..."
        systemctl stop postgresql redis 2>/dev/null || true
        DOCKER_BUILDKIT=1 $COMPOSE up -d --build
        print_success "Infrastructure started!"
        echo ""
        echo -e "${GREEN}DEV MODE is ready!${NC}"
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "1. Start Users Service locally (port 8000):"
        echo "   cd services/users && alembic upgrade head && python -m uvicorn main:app --reload --port 8000"
        echo ""
        echo "2. Start Budget Service locally (port 8001) - in another terminal:"
        echo "   cd services/budget && alembic upgrade head && python -m uvicorn main:app --reload --port 8001"
        echo ""
        echo "3. Start AI Service locally (port 8002) - in another terminal:"
        echo "   cd services/ai && alembic upgrade head && python -m uvicorn main:app --reload --port 8002"
        echo ""
        echo "4. Start Chat Service locally (port 8003) - in another terminal:"
        echo "   cd services/chat && alembic upgrade head && python -m uvicorn main:app --reload --port 8003"
        echo ""
        echo "5. Start Frontend locally - in another terminal:"
        echo "   cd frontend-typescript && npm run dev"
        echo ""
        echo "Or run: ./dev.sh services (for detailed commands)"
        echo ""
        echo -e "${YELLOW}Available endpoints:${NC}"
        echo "  Database:           localhost:5432"
        echo "  Redis:              localhost:6379"
        echo "  RabbitMQ:           localhost:5672 (AMQP), localhost:15672 (UI)"
        echo "  Flower (Celery UI): http://localhost:5555"
        echo "  Nginx Proxy:        localhost:8082"
        echo "  Users Service:      localhost:8000 (run locally) - http://localhost:8000/docs"
        echo "  Budget Service:     localhost:8001 (run locally) - http://localhost:8001/docs"
        echo "  AI Service:         localhost:8002 (run locally) - http://localhost:8002/docs"
        echo "  Chat Service:       localhost:8003 (run locally) - http://localhost:8003/docs"
        echo "  Frontend:           localhost:3000 (run locally)"
        echo "  Celery Worker:      run locally (see ./dev.sh services)"
        echo "  Celery Beat:        run locally (see ./dev.sh services)"
        echo ""
        echo -e "${YELLOW}Monitoring & Observability:${NC}"
        echo "  Jaeger Tracing:     http://localhost:16686"
        echo "  Prometheus Metrics: http://localhost:9090"
        echo "  Grafana Dashboards: http://localhost:3002 (admin:admin)"
        echo "  Users Metrics:      http://localhost:8000/metrics"
        echo "  Budget Metrics:     http://localhost:8001/metrics"
        echo "  AI Metrics:         http://localhost:8002/metrics"
        echo "  Chat Metrics:       http://localhost:8003/metrics"
        ;;

    down)
        print_header "Stopping DEV MODE"
        $COMPOSE down
        print_success "DEV MODE stopped"
        ;;

    logs)
        $COMPOSE logs -f
        ;;

    status)
        print_header "DEV MODE Status"
        $COMPOSE ps
        ;;

    rebuild)
        print_header "Rebuilding DEV MODE containers"
        DOCKER_BUILDKIT=1 $COMPOSE build --no-cache
        print_success "Containers rebuilt"
        ;;

    services)
        print_header "Running Services Locally - Commands"
        echo ""
        echo -e "${YELLOW}Open new terminals and run these commands:${NC}"
        echo ""
        echo -e "${BLUE}=== Terminal 1: Users Service (port 8000) ===${NC}"
        echo "cd services/users"
        echo "alembic upgrade head"
        echo "python -m uvicorn main:app --reload --port 8000"
        echo ""
        echo -e "${BLUE}=== Terminal 2: Budget Service (port 8001) ===${NC}"
        echo "cd services/budget"
        echo "alembic upgrade head"
        echo "python -m uvicorn main:app --reload --port 8001"
        echo ""
        echo -e "${BLUE}=== Terminal 3: AI Service (port 8002) ===${NC}"
        echo "cd services/ai"
        echo "alembic upgrade head"
        echo "python -m uvicorn main:app --reload --port 8002"
        echo ""
        echo -e "${BLUE}=== Terminal 4: Chat Service (port 8003) ===${NC}"
        echo "cd services/chat"
        echo "alembic upgrade head"
        echo "python -m uvicorn main:app --reload --port 8003"
        echo ""
        echo -e "${BLUE}=== Terminal 5: Frontend ===${NC}"
        echo "cd frontend-typescript"
        echo "npm install  # first time only"
        echo "npm run dev"
        echo ""
        echo -e "${BLUE}=== Terminal 6: Celery Worker ===${NC}"
        echo "cd services/worker"
        echo "celery -A celery_app worker --loglevel=info -Q ai,budget,users"
        echo ""
        echo -e "${BLUE}=== Terminal 7: Celery Beat ===${NC}"
        echo "cd services/worker"
        echo "celery -A celery_app beat --loglevel=info"
        echo ""
        echo -e "${YELLOW}Endpoints:${NC}"
        echo "  Frontend:       http://localhost:3000"
        echo "  Users API:      http://localhost:8000/docs"
        echo "  Budget API:     http://localhost:8001/docs"
        echo "  AI API:         http://localhost:8002/docs"
        echo "  Chat API:       http://localhost:8003/docs"
        echo "  Nginx Proxy:    http://localhost:8082"
        echo ""
        echo -e "${YELLOW}Monitoring (already running in Docker):${NC}"
        echo "  Jaeger:         http://localhost:16686 (traces)"
        echo "  Prometheus:     http://localhost:9090 (metrics)"
        echo "  Grafana:        http://localhost:3001 (dashboards, admin:admin)"
        echo "  Flower:         http://localhost:5555 (Celery task monitor)"
        echo ""
        echo -e "${YELLOW}Note: .env.*.dev files already have localhost configured${NC}"
        ;;

    clean)
        print_header "Cleaning up DEV MODE"
        $COMPOSE down -v
        print_success "DEV MODE cleaned (volumes removed)"
        ;;

    *)
        echo "Usage: ./dev.sh {up|down|logs|status|rebuild|services|clean}"
        echo ""
        echo "Commands:"
        echo "  up       - Start infrastructure for dev mode"
        echo "  down     - Stop infrastructure"
        echo "  logs     - View logs"
        echo "  status   - Show container status"
        echo "  rebuild  - Rebuild containers without cache"
        echo "  services - Show commands to run services locally"
        echo "  clean    - Stop and remove volumes"
        exit 1
        ;;
esac
