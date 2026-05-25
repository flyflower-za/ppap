#!/bin/bash

# Ubuntu UFW Firewall Script for PPAP Platform
# This script enables UFW and opens the necessary ports for external access.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Configuring Ubuntu UFW Firewall for PPAP...${NC}"

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run this script as root or using sudo.${NC}"
    exit 1
fi

# Make sure ufw is installed
if ! command -v ufw &> /dev/null; then
    echo -e "${YELLOW}UFW is not installed. Installing ufw...${NC}"
    apt-get update && apt-get install -y ufw
fi

# Always allow SSH to prevent locking ourselves out
echo -e "Allowing SSH (Port 22)..."
ufw allow 22/tcp

# Frontend (HTTP/HTTPS)
echo -e "Allowing HTTP/HTTPS (Port 80, 443)..."
ufw allow 80/tcp
ufw allow 443/tcp

# Backend API
echo -e "Allowing Backend API (Port 31234)..."
ufw allow 31234/tcp

# MinIO Object Storage
echo -e "Allowing MinIO API and Console (Port 9000, 9001)..."
ufw allow 9000/tcp
ufw allow 9001/tcp

# Enable firewall (force yes to avoid prompt)
echo -e "${YELLOW}Enabling UFW...${NC}"
ufw --force enable

echo -e "${GREEN}Firewall configuration completed!${NC}"
ufw status numbered
