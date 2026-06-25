#!/bin/bash
# PPAP User Management Wrapper Script
# Run user CLI commands through Docker container

set -e

# Find docker-compose.yml
COMPOSE_FILE=""
if [ -f "deploy/docker-compose.yml" ]; then
  COMPOSE_FILE="deploy/docker-compose.yml"
elif [ -f "docker-compose.yml" ]; then
  COMPOSE_FILE="docker-compose.yml"
else
  echo "❌ Error: docker-compose.yml not found in current directory or deploy/"
  exit 1
fi

# Check if backend container is running
if ! docker compose -f "$COMPOSE_FILE" ps backend | grep -q "ppap-backend.*Up"; then
  echo "❌ Error: backend container is not running"
  echo "Please start the services first: docker compose -f $COMPOSE_FILE up -d"
  exit 1
fi

# Execute user CLI in backend container
docker compose -f "$COMPOSE_FILE" exec -T backend python scripts/user_cli.py "$@"
