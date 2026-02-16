#!/bin/bash
# 大模型驱动的股票分析系统 - Docker 启动脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== LLM Stock Analyzer Docker Setup ===${NC}"

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# 创建 .env 文件（如果不存在）
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env file with your configuration${NC}"
fi

# 解析命令行参数
case "${1:-start}" in
    start)
        echo -e "${GREEN}Starting production environment...${NC}"
        docker compose up -d
        echo -e "${GREEN}Services started:${NC}"
        echo "  - Frontend: http://localhost"
        echo "  - Backend:  http://localhost:8000"
        echo "  - API Docs: http://localhost:8000/docs"
        ;;
    dev)
        echo -e "${GREEN}Starting development environment...${NC}"
        docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
        echo -e "${GREEN}Development services started:${NC}"
        echo "  - Frontend Dev: http://localhost:5173"
        echo "  - Backend:      http://localhost:8000"
        ;;
    stop)
        echo -e "${YELLOW}Stopping services...${NC}"
        docker compose down
        ;;
    restart)
        echo -e "${YELLOW}Restarting services...${NC}"
        docker compose restart
        ;;
    logs)
        docker compose logs -f "${2:-}"
        ;;
    rebuild)
        echo -e "${YELLOW}Rebuilding containers...${NC}"
        docker compose build --no-cache
        docker compose up -d
        ;;
    clean)
        echo -e "${YELLOW}Stopping and removing containers, volumes...${NC}"
        docker compose down -v
        ;;
    ps)
        docker compose ps
        ;;
    health)
        echo -e "${GREEN}Checking services health...${NC}"
        docker compose ps
        echo ""
        echo -e "${GREEN}Backend health:${NC}"
        curl -s http://localhost:8000/health || echo "Backend not healthy"
        ;;
    *)
        echo "Usage: $0 {start|dev|stop|restart|logs|rebuild|clean|ps|health}"
        echo ""
        echo "Commands:"
        echo "  start    - Start production environment"
        echo "  dev      - Start development environment"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - View logs (optional: service name)"
        echo "  rebuild  - Rebuild and start containers"
        echo "  clean    - Remove all containers and volumes"
        echo "  ps       - Show running containers"
        echo "  health   - Check services health"
        exit 1
        ;;
esac
