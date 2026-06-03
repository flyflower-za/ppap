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
        echo -e "${YELLOW}  Please remember to change default secrets for production!${NC}"
    else
        echo -e "${YELLOW}Creating basic .env file...${NC}"
        cat > .env << EOF
# PPAP Environment Configuration
SECRET_KEY=change-this-in-production
EOF
        echo -e "${GREEN}[+] Created basic .env file${NC}"
    fi
else
    echo -e "${GREEN}[+] Found existing .env file${NC}"
fi
echo ""

# 3. Start services with automated database initialization
echo -e "${YELLOW}Starting services with automated database initialization...${NC}"
echo -e "${BLUE}The db-init service will automatically run init-db.sql${NC}"

$DOCKER_COMPOSE_CMD up -d --build

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
until curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    echo "MinIO: ($((RETRIES--)) retries left)"
    sleep 2
done

if [ $RETRIES -gt 0 ]; then
    echo -e "${GREEN}[+] MinIO is ready${NC}"
else
    echo -e "${YELLOW}MinIO may still be starting${NC}"
fi

# 5. Initialize MinIO bucket
echo ""
echo -e "${YELLOW}Initializing MinIO bucket...${NC}"
sleep 3  # Give MinIO a moment to stabilize

RETRIES=5
until docker run --rm --network container:ppap-minio --entrypoint /bin/sh minio/mc -c "mc alias set ppapminio http://localhost:9000 minioadmin minioadmin && mc mb ppapminio/ppap-files --ignore-existing && mc anonymous set public ppapminio/ppap-files" > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    echo "Attempting to create MinIO bucket... ($((RETRIES--)) retries left)"
    sleep 3
done

if [ $? -eq 0 ] || [ $RETRIES -gt 0 ]; then
    echo -e "${GREEN}[+] MinIO bucket 'ppap-files' created${NC}"
else
    echo -e "${YELLOW}⚠ MinIO bucket creation failed, may need manual setup${NC}"
    echo "Run: docker run --rm --network container:ppap-minio minio/mc ..."
fi

# 6. Final status check
echo ""
echo -e "${YELLOW}Checking service status...${NC}"
$DOCKER_COMPOSE_CMD ps

echo ""
echo -e "${GREEN}=== Deployment Completed Successfully ===${NC}"
echo -e "${BLUE}Access the services at:${NC}"
echo -e "  🌐 Frontend UI:   ${GREEN}http://localhost${NC}"
echo -e "  🔧 Backend API:   ${GREEN}http://localhost:31234/docs${NC}"
echo -e "  📁 MinIO Console: ${GREEN}http://localhost:9001${NC} ${YELLOW}(minioadmin / minioadmin)${NC}"
echo ""
echo -e "${BLUE}Default Admin Account:${NC}"
echo -e "  📧 Email:    ${GREEN}admin@example.com${NC}"
echo -e "  🔑 Password: ${GREEN}admin123${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Access the frontend UI at http://localhost"
echo "   2. Login with admin@example.com / admin123"
echo -e "  3. Configure LDAP/SSO in Settings if needed"
echo "  4. Upload PDF files to test verification functionality"
echo ""
