#!/bin/bash

# PPAP One-Click Deployment Script
# This script sets up the PPAP environment and starts all necessary services using Docker Compose.

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== PPAP Platform Deployment ===${NC}"

# 1. Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker is not installed.${NC}"
    exit 1
fi

if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif docker-compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}Error: docker-compose or 'docker compose' is not installed.${NC}"
    exit 1
fi

# 2. Setup Environment Variables
echo -e "${YELLOW}Setting up environment variables...${NC}"
cd deploy

if [ ! -f .env ]; then
    echo -e "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${GREEN}Generated .env file. Please remember to change default secrets for production.${NC}"
else
    echo -e "Found existing .env file."
fi

# 3. Start services
echo -e "${YELLOW}Building and starting services...${NC}"
$DOCKER_COMPOSE_CMD up -d --build

# 4. Wait for PostgreSQL
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
RETRIES=30
until $DOCKER_COMPOSE_CMD exec -T postgres pg_isready -U ppap > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    echo "Waiting for postgres server... ($((RETRIES--)) retries left)"
    sleep 2
done

if [ $RETRIES -eq 0 ]; then
    echo -e "${RED}PostgreSQL did not start in time. Check docker logs.${NC}"
    exit 1
fi

# 5. Initialize Database
echo -e "${YELLOW}Initializing database...${NC}"
cat init-db.sql | $DOCKER_COMPOSE_CMD exec -T postgres psql -U ppap -d ppap > /dev/null 2>&1 || true

# 6. Initialize MinIO bucket
echo -e "${YELLOW}Initializing MinIO bucket...${NC}"
# Wait for MinIO to be ready
RETRIES=15
until curl -sf http://localhost:9000/minio/health/live > /dev/null || [ $RETRIES -eq 0 ]; do
    echo "Waiting for MinIO server... ($((RETRIES--)) retries left)"
    sleep 2
done

if [ $RETRIES -gt 0 ]; then
    echo -e "Setting up 'ppap-files' bucket..."
    # Using Docker to run MinIO Client (mc)
    docker run --rm --network host --entrypoint /bin/sh minio/mc -c "\
        mc alias set ppapminio http://localhost:9000 minioadmin minioadmin && \
        mc mb ppapminio/ppap-files --ignore-existing && \
        mc anonymous set public ppapminio/ppap-files" || true
else
    echo -e "${RED}MinIO didn't start in time. You may need to create the bucket manually.${NC}"
fi

echo -e "${GREEN}=== Deployment Completed Successfully ===${NC}"
echo -e "Access the services at:"
echo -e "  - Frontend UI:   http://localhost"
echo -e "  - Backend API:   http://localhost:31234/docs"
echo -e "  - MinIO Console: http://localhost:9001 (minioadmin / minioadmin)"
echo -e ""
echo -e "Default Admin Account:"
echo -e "  Email:    admin@example.com"
echo -e "  Password: admin123"
