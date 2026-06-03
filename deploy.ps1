# PPAP Platform Deployment Script for Windows
# This script sets up the PPAP environment and starts all necessary services using Docker Compose.

param(
    [switch]$SkipEnvCheck = $false,
    [switch]$SkipMinIO = $false,
    [switch]$ForceRebuild = $false
)

# Colors for output
$GREEN = "`e[32m"
$YELLOW = "`e[33m"
$RED = "`e[31m"
$NC = "`e[0m"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    switch ($Color) {
        "Green" { Write-Host $GREEN -NoNewline }
        "Yellow" { Write-Host $YELLOW -NoNewline }
        "Red" { Write-Host $RED -NoNewline }
        "White" { Write-Host $NC -NoNewline }
        default { Write-Host $NC -NoNewline }
    }
    Write-Host $Message
    Write-Host $NC
}

function Test-DockerCompose {
    # Test if docker compose command works
    $null = docker compose version 2>$null
    return $?
}

function Test-DockerComposeLegacy {
    # Test if docker-compose command works
    $null = docker-compose version 2>$null
    return $?
}

function Test-Docker {
    # Test if docker command works
    $null = docker ps 2>$null
    return $?
}

Write-ColorOutput "=== PPAP Platform Deployment ===" "Green"
Write-Host ""

# 1. Check prerequisites
Write-ColorOutput "Checking prerequisites..." "Yellow"

# Check if Docker is running
if (-not (Test-Docker)) {
    Write-ColorOutput "Error: Docker Desktop is not running." "Red"
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}
Write-ColorOutput "✓ Docker Desktop is running" "Green"

# Determine which Docker Compose command to use
if (Test-DockerCompose) {
    $DOCKER_COMPOSE_CMD = "docker compose"
    Write-ColorOutput "✓ Using 'docker compose' command" "Green"
} elseif (Test-DockerComposeLegacy) {
    $DOCKER_COMPOSE_CMD = "docker-compose"
    Write-ColorOutput "✓ Using 'docker-compose' command" "Green"
} else {
    Write-ColorOutput "Error: Neither 'docker compose' nor 'docker-compose' is available." "Red"
    exit 1
}

# Check if in correct directory
$originalDir = Get-Location
if (-not (Test-Path "docker-compose.yml")) {
    Write-ColorOutput "Changing to deploy directory..." "Yellow"
    cd deploy
}

# 2. Setup Environment Variables
Write-Host ""
Write-ColorOutput "Setting up environment variables..." "Yellow"

$envFile = ".env"
$envExample = ".env.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-ColorOutput "✓ Created .env from .env.example" "Green"
        Write-ColorOutput "  Please remember to change default secrets for production!" "Yellow"
    } else {
        Write-ColorOutput "⚠ Neither .env nor .env.example found. Creating basic .env..." "Yellow"
        @"
# PPAP Environment Configuration
SECRET_KEY=change-this-in-production
"@ | Out-File -FilePath $envFile
        Write-ColorOutput "✓ Created basic .env file" "Green"
        Write-ColorOutput "  Please update SECRET_KEY for production!" "Yellow"
    }
} else {
    Write-ColorOutput "✓ Found existing .env file" "Green"
}

# 3. Build and start services
Write-Host ""
Write-ColorOutput "Building and starting services..." "Yellow"

$buildArgs = @("up", "-d")
if ($ForceRebuild) {
    $buildArgs += @("--build")
    Write-ColorOutput "Force rebuild enabled..." "Yellow"
}

try {
    & $DOCKER_COMPOSE_CMD $buildArgs
    Write-ColorOutput "✓ Services started successfully" "Green"
} catch {
    Write-ColorOutput "Error: Failed to start services. Check docker logs for details." "Red"
    Write-Host "Run 'docker compose logs' to see error details." -ForegroundColor Red
    exit 1
}

# 4. Wait for services to be healthy
Write-Host ""
Write-ColorOutput "Waiting for services to be healthy..." "Yellow"

# Wait for PostgreSQL
$retries = 30
$postgresReady = $false

while ($retries -gt 0 -and -not $postgresReady) {
    try {
        $null = docker compose exec -T postgres pg_isready -U ppap 2>$null
        $postgresReady = $true
        Write-ColorOutput "✓ PostgreSQL is ready" "Green"
    } catch {
        Write-Host "Waiting for PostgreSQL... ($retries retries left)" -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        $retries--
    }
}

if (-not $postgresReady) {
    Write-ColorOutput "Error: PostgreSQL did not start in time" "Red"
    Write-Host "Run 'docker compose logs postgres' to see error details." -ForegroundColor Red
    exit 1
}

# Wait for MinIO (unless skipped)
if (-not $SkipMinIO) {
    Write-Host "Waiting for MinIO to be ready..."
    $retries = 15
    $minioReady = $false

    while ($retries -gt 0 -and -not $minioReady) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                $minioReady = $true
                Write-ColorOutput "✓ MinIO is ready" "Green"
            }
        } catch {
            Write-Host "Waiting for MinIO... ($retries retries left)" -ForegroundColor Yellow
            Start-Sleep -Seconds 2
            $retries--
        }
    }

    if ($minioReady) {
        Write-ColorOutput "Setting up 'ppap-files' bucket..." "Yellow"
        try {
            docker run --rm --network host --entrypoint /bin/sh minio/mc -c `
                "mc alias set ppapminio http://localhost:9000 minioadmin minioadmin && `
                mc mb ppapminio/ppap-files --ignore-existing && `
                mc anonymous set public ppapminio/ppap-files"
            Write-ColorOutput "✓ MinIO bucket created" "Green"
        } catch {
            Write-ColorOutput "⚠ Failed to create MinIO bucket, may need manual setup" "Yellow"
        }
    } else {
        Write-ColorOutput "⚠ MinIO didn't start in time. You may need to create the bucket manually." "Yellow"
    }
}

Write-Host ""
Write-ColorOutput "=== Deployment Completed Successfully ===" "Green"
Write-Host "Access the services at:"
Write-Host "  - Frontend UI:   http://localhost" -ForegroundColor Cyan
Write-Host "  - Backend API:   http://localhost:31234/docs" -ForegroundColor Cyan
Write-Host "  - MinIO Console: http://localhost:9001 (minioadmin / minioadmin)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Default Admin Account:"
Write-Host "  Email:    admin@example.com" -ForegroundColor Green
Write-Host "  Password: admin123" -ForegroundColor Green

# Return to original directory
cd $originalDir
