#!/usr/bin/env bash

# Celery Worker Startup Script for macOS / Local Development
# This script automatically injects the OBJC_DISABLE_INITIALIZE_FORK_SAFETY
# environment variable to prevent Celery's multiprocessing fork() from
# crashing on macOS due to Objective-C library initialization restrictions.

export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

echo "Starting Celery worker for PPAP File Verification Platform..."
echo "macOS fork safety bypass activated."

celery -A app.tasks.celery_app worker --loglevel=info
