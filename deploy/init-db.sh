#!/bin/sh
# PPAP Database Initialization Script
# This script ensures proper database initialization on first run

set -e

echo "=== PPAP Database Initialization ==="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
RETRIES=30
until PGPASSWORD=ppap123 psql -h postgres -U ppap -d ppap -c 'SELECT 1' > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
  echo "Waiting for postgres... ($((RETRIES--)) retries left)"
  sleep 2
done

if [ $RETRIES -eq 0 ]; then
  echo "Error: PostgreSQL did not start in time"
  exit 1
fi

# Check if database is already initialized
echo "Checking database initialization status..."
if PGPASSWORD=ppap123 psql -h postgres -U ppap -d ppap -c 'SELECT 1 FROM users' > /dev/null 2>&1; then
  echo "Database already initialized, skipping..."
  exit 0
fi

# Run initialization script
echo "Running database initialization..."
PGPASSWORD=ppap123 psql -h postgres -U ppap -d ppap < /docker-entrypoint-initdb.d/init-db.sql

echo "=== Database Initialization Completed ==="
