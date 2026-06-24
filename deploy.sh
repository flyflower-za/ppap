#!/bin/bash

# PPAP One-Click Deployment Script (Updated)
# This script sets up the PPAP environment and starts all necessary services using Docker Compose.
# Supports the new automated database initialization via db-init service

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configurable host and ports (for remote/SSH forwarding scenarios)
API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-31234}"
MINIO_PORT="${MINIO_PORT:-9000}"
MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-9001}"

echo -e "${GREEN}=== PPAP Platform Deployment ===${NC}"
echo -e "${BLUE}Updated version with automated database initialization${NC}"
echo ""

# 1. Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker is not installed.${NC}"
    echo "Please install Docker Desktop first."
    exit 1
fi

echo -e "${GREEN}[+] Docker is installed${NC}"

# Check Docker Compose availability
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
    echo -e "${GREEN}[+] Using 'docker compose' command${NC}"
elif docker-compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
    echo -e "${GREEN}[+] Using 'docker-compose' command${NC}"
else
    echo -e "${RED}Error: Neither 'docker compose' nor 'docker-compose' is installed.${NC}"
    exit 1
fi

# Check if Docker daemon is running
if ! docker ps &> /dev/null; then
    echo -e "${RED}Error: Docker daemon is not running.${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo -e "${GREEN}[+] Docker daemon is running${NC}"
echo ""

# 2. Setup Environment Variables
echo -e "${YELLOW}Setting up environment variables...${NC}"
cd deploy

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}[+] Created .env from .env.example${NC}"
    else
        echo -e "${YELLOW}Creating basic .env file...${NC}"
        cat > .env << EOF
# PPAP Environment Configuration
SECRET_KEY=change-this-in-production
POSTGRES_PASSWORD=ppap123
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
REDIS_PASSWORD=redis-secret-pass
EOF
        echo -e "${GREEN}[+] Created basic .env file${NC}"
    fi

    # Auto-generate strong secrets for first-time deployment
    if command -v openssl &> /dev/null; then
        GENERATED_SECRET=$(openssl rand -hex 32)
        GENERATED_DB_PASS=$(openssl rand -base64 16 | tr -d '/+==' | head -c 20)
        GENERATED_MINIO_PASS=$(openssl rand -base64 16 | tr -d '/+==' | head -c 20)
        GENERATED_REDIS_PASS=$(openssl rand -base64 12 | tr -d '/+==' | head -c 16)
        GENERATED_ADMIN_PASS=$(openssl rand -base64 10 | tr -d '/+==' | head -c 12)

        # macOS sed requires empty string after -i, Linux does not
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i'' -e "s/^SECRET_KEY=.*/SECRET_KEY=${GENERATED_SECRET}/" .env
            sed -i'' -e "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${GENERATED_DB_PASS}/" .env
            sed -i'' -e "s/^MINIO_ROOT_PASSWORD=.*/MINIO_ROOT_PASSWORD=${GENERATED_MINIO_PASS}/" .env
            sed -i'' -e "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=${GENERATED_REDIS_PASS}/" .env
        else
            sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${GENERATED_SECRET}/" .env
            sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${GENERATED_DB_PASS}/" .env
            sed -i "s/^MINIO_ROOT_PASSWORD=.*/MINIO_ROOT_PASSWORD=${GENERATED_MINIO_PASS}/" .env
            sed -i "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=${GENERATED_REDIS_PASS}/" .env
        fi

        echo -e "${GREEN}[+] Auto-generated strong secrets (saved to .env)${NC}"
        echo -e "${YELLOW}  ⚠ Save these credentials securely!${NC}"

        # P2-5: Generate bcrypt hash for admin password and replace in init-db.sql
        ADMIN_HASH=$(python3 -c "
import bcrypt
print(bcrypt.hashpw(b'${GENERATED_ADMIN_PASS}', bcrypt.gensalt()).decode())
" 2>/dev/null || python -c "
import bcrypt
print(bcrypt.hashpw(b'${GENERATED_ADMIN_PASS}', bcrypt.gensalt()).decode())
" 2>/dev/null || echo "")

        if [ -n "$ADMIN_HASH" ]; then
            # Escape $ in hash for sed (bcrypt hashes contain $)
            ESCAPED_HASH=$(echo "$ADMIN_HASH" | sed 's/\$/\\$/g')
            sed -i'' -e "s/\\\$2b\\\$.*'/'${ESCAPED_HASH}'/" init-db.sql 2>/dev/null || \
            sed -i "s/\$2b\$.*'/'${ESCAPED_HASH}'/" init-db.sql 2>/dev/null || \
            echo -e "${YELLOW}  ⚠ Could not update admin password in init-db.sql${NC}"
            # Write hash to .env for db-init container (existing databases)
            echo "ADMIN_PASSWORD_HASH=${ADMIN_HASH}" >> .env
            export ADMIN_PASSWORD_HASH="${ADMIN_HASH}"
            echo -e "${GREEN}[+] Admin password set to: ${GENERATED_ADMIN_PASS}${NC}"
        else
            echo -e "${YELLOW}  ⚠ Python/bcrypt not available, using default admin password (admin123)${NC}"
        fi
    fi
else
    echo -e "${GREEN}[+] Found existing .env file (reusing saved secrets)${NC}"
    # Ensure ADMIN_PASSWORD_HASH exists in .env for existing deployments
    if ! grep -q "ADMIN_PASSWORD_HASH" .env; then
        ADMIN_HASH=$(python3 -c "
import bcrypt
print(bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode())
" 2>/dev/null || python -c "
import bcrypt
print(bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode())
" 2>/dev/null || echo "")
        if [ -n "$ADMIN_HASH" ]; then
            echo "ADMIN_PASSWORD_HASH=${ADMIN_HASH}" >> .env
            echo -e "${YELLOW}[+] Generated ADMIN_PASSWORD_HASH for existing deployment${NC}"
        fi
    fi
fi
# Export ADMIN_PASSWORD_HASH for docker-compose
export $(grep -E '^ADMIN_PASSWORD_HASH=' .env | xargs) 2>/dev/null
echo ""

# Parse arguments
FORCE_REBUILD=0
for arg in "$@"; do
    if [ "$arg" == "--clean" ] || [ "$arg" == "--force" ]; then
        FORCE_REBUILD=1
    fi
done

# 3. Start services with automated database initialization
echo -e "${YELLOW}Starting services with automated database initialization...${NC}"
echo -e "${BLUE}The db-init service will automatically run init-db.sql${NC}"

if [ $FORCE_REBUILD -eq 1 ]; then
    echo -e "${YELLOW}Force rebuilding all containers without cache...${NC}"
    $DOCKER_COMPOSE_CMD build --no-cache
fi

$DOCKER_COMPOSE_CMD up -d --build --remove-orphans

echo ""
echo -e "${YELLOW}Waiting for database initialization to complete...${NC}"
RETRIES=30

# Wait for db-init service to complete
while [ $RETRIES -gt 0 ]; do
    STATUS=$(docker inspect ppap-db-init --format='{{.State.Status}}' 2>/dev/null || echo "")
    EXITCODE=$(docker inspect ppap-db-init --format='{{.State.ExitCode}}' 2>/dev/null || echo "")
    
    if [ "$STATUS" = "exited" ] && [ "$EXITCODE" = "0" ]; then
        echo -e "${GREEN}[+] Database initialization completed${NC}"
        break
    elif [ "$STATUS" = "exited" ]; then
        echo -e "${RED}Error: Database initialization failed${NC}"
        $DOCKER_COMPOSE_CMD logs db-init
        exit 1
    else
        echo "Waiting for database initialization... ($((RETRIES--)) retries left)"
        sleep 2
    fi
done

if [ $RETRIES -eq 0 ]; then
    echo -e "${YELLOW}Database initialization may still be in progress. Check logs:${NC}"
    echo "  $DOCKER_COMPOSE_CMD logs db-init"
fi

# 4. Wait for services to be healthy
echo ""
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
RETRIES=30
until $DOCKER_COMPOSE_CMD exec -T postgres pg_isready -U ppap > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    echo "PostgreSQL: ($((RETRIES--)) retries left"
    sleep 2
done

if [ $RETRIES -gt 0 ]; then
    echo -e "${GREEN}[+] PostgreSQL is ready${NC}"
else
    echo -e "${RED}PostgreSQL did not start in time${NC}"
    exit 1
fi

# Wait for Redis
echo "Waiting for Redis..."
RETRIES=30
until $DOCKER_COMPOSE_CMD exec -T redis redis-cli ping > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    echo "Redis: ($((RETRIES--)) retries left"
    sleep 2
done

if [ $RETRIES -gt 0 ]; then
    echo -e "${GREEN}[+] Redis is ready${NC}"
else
    echo -e "${YELLOW}Redis may still be starting${NC}"
fi

# Wait for MinIO
echo "Waiting for MinIO..."
RETRIES=15
until curl -sf http://${API_HOST}:${MINIO_PORT}/minio/health/live > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    echo "MinIO: ($((RETRIES--)) retries left)"
    sleep 2
done

if [ $RETRIES -gt 0 ]; then
    echo -e "${GREEN}[+] MinIO is ready${NC}"
else
    echo -e "${YELLOW}MinIO may still be starting${NC}"
fi

# Wait for Backend API
echo "Waiting for Backend API..."
RETRIES=30
until curl -sf http://${API_HOST}:${API_PORT}/docs > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    echo "Backend API: ($((RETRIES--)) retries left)"
    sleep 2
done

if [ $RETRIES -gt 0 ]; then
    echo -e "${GREEN}[+] Backend API is ready${NC}"
else
    echo -e "${YELLOW}Backend API may still be starting${NC}"
fi

# 5. Wait for MinIO bucket initialization
echo ""
echo -e "${YELLOW}Waiting for MinIO bucket initialization...${NC}"

MINIO_RETRIES=30
while [ $MINIO_RETRIES -gt 0 ]; do
    STATUS=$(docker inspect ppap-minio-init --format='{{.State.Status}}' 2>/dev/null || echo "")
    EXITCODE=$(docker inspect ppap-minio-init --format='{{.State.ExitCode}}' 2>/dev/null || echo "")

    if [ "$STATUS" = "exited" ] && [ "$EXITCODE" = "0" ]; then
        echo -e "${GREEN}[+] MinIO bucket 'ppap-files' initialized${NC}"
        break
    elif [ "$STATUS" = "exited" ]; then
        echo -e "${RED}Error: MinIO bucket initialization failed${NC}"
        $DOCKER_COMPOSE_CMD logs minio-init
        echo -e "${YELLOW}⚠ Continuing anyway, may need manual bucket setup${NC}"
        break
    else
        echo "Waiting for MinIO bucket initialization... ($((MINIO_RETRIES--)) retries left)"
        sleep 2
    fi
done

if [ $MINIO_RETRIES -eq 0 ]; then
    echo -e "${YELLOW}MinIO bucket initialization may still be in progress. Check logs:${NC}"
    echo "  $DOCKER_COMPOSE_CMD logs minio-init"
fi

# 6. Final status check
echo ""
echo -e "${YELLOW}Checking service status...${NC}"
$DOCKER_COMPOSE_CMD ps

echo ""
echo -e "${GREEN}=== Deployment Completed Successfully ===${NC}"
echo -e "${BLUE}Access the services at:${NC}"
echo -e "  🌐 Frontend UI:   ${GREEN}http://${API_HOST}${NC}"
echo -e "  🔧 Backend API:   ${GREEN}http://${API_HOST}:${API_PORT}/docs${NC}"
echo -e "  📁 MinIO Console: ${GREEN}http://${API_HOST}:${MINIO_CONSOLE_PORT}${NC} ${YELLOW}(minioadmin / ${MINIO_ROOT_USER:-minioadmin})${NC}"
echo ""
echo -e "${BLUE}Default Admin Account:${NC}"
echo -e "  📧 Email:    ${GREEN}admin@example.com${NC}"
echo -e "  🔑 Password: ${GREEN}${GENERATED_ADMIN_PASS:-admin123}${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Access the frontend UI at http://localhost"
echo "   2. Login with admin@example.com / admin123"
echo -e "  3. Configure LDAP/SSO in Settings if needed"
echo "  4. Upload PDF files to test verification functionality"
echo ""
