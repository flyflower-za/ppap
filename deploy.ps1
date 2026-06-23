# PPAP Platform Deployment Script for Windows
# This script sets up the PPAP environment and starts all necessary services using Docker Compose.
# Supports the new automated database initialization via db-init service

param(
    [switch]$ForceRebuild = $false
)

# Colors for output
$GREEN = "`e[0;32m"
$YELLOW = "`e[1;33m"
$RED = "`e[0;31m"
$BLUE = "`e[0;34m"
$NC = "`e[0m"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    switch ($Color) {
        "Green" { Write-Host $GREEN -NoNewline }
        "Yellow" { Write-Host $YELLOW -NoNewline }
        "Red" { Write-Host $RED -NoNewline }
        "Blue" { Write-Host $BLUE -NoNewline }
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

function Invoke-DockerCompose {
    $flatArgs = @()
    foreach ($arg in $args) {
        if ($arg -is [array]) {
            $flatArgs += $arg
        } else {
            $flatArgs += $arg
        }
    }

    if (Test-DockerCompose) {
        $fullArgs = @("compose") + $flatArgs
        & docker $fullArgs
    } else {
        & docker-compose $flatArgs
    }
}

Write-Host "$($GREEN)=== PPAP Platform Deployment ===$($NC)"
Write-Host "$($BLUE)Updated version with automated database initialization$($NC)"
Write-Host ""

# 1. Check prerequisites
Write-ColorOutput "Checking prerequisites..." "Yellow"

# Check if Docker is running
if (-not (Test-Docker)) {
    Write-ColorOutput "Error: Docker daemon is not running." "Red"
    Write-Host "Please start Docker Desktop and try again."
    exit 1
}
Write-ColorOutput "[+] Docker is installed" "Green"

# Determine which Docker Compose command to use
if (Test-DockerCompose) {
    $DOCKER_COMPOSE_CMD = "docker compose"
    Write-ColorOutput "[+] Using 'docker compose' command" "Green"
} elseif (Test-DockerComposeLegacy) {
    $DOCKER_COMPOSE_CMD = "docker-compose"
    Write-ColorOutput "[+] Using 'docker-compose' command" "Green"
} else {
    Write-ColorOutput "Error: Neither 'docker compose' nor 'docker-compose' is installed." "Red"
    exit 1
}

# Check if Docker daemon is running
if (-not (Test-Docker)) {
    Write-ColorOutput "Error: Docker daemon is not running." "Red"
    Write-Host "Please start Docker Desktop and try again."
    exit 1
}

Write-ColorOutput "[+] Docker daemon is running" "Green"
Write-Host ""

# 2. Setup Environment Variables
Write-ColorOutput "Setting up environment variables..." "Yellow"
cd deploy

$envFile = ".env"
$envExample = ".env.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-ColorOutput "[+] Created .env from .env.example" "Green"
        Write-ColorOutput "  Please remember to change default secrets for production!" "Yellow"
    } else {
        Write-ColorOutput "Creating basic .env file..." "Yellow"
@"
# PPAP Environment Configuration
SECRET_KEY=change-this-in-production
"@ | Out-File -FilePath $envFile -Encoding UTF8
        Write-ColorOutput "[+] Created basic .env file" "Green"
    }
} else {
    Write-ColorOutput "[+] Found existing .env file" "Green"
}
Write-Host ""

# 3. Start services with automated database initialization
Write-ColorOutput "Starting services with automated database initialization..." "Yellow"
Write-Host "$($BLUE)The db-init service will automatically run init-db.sql$($NC)"

if ($ForceRebuild) {
    Write-ColorOutput "Force rebuilding all containers without cache..." "Yellow"
    Invoke-DockerCompose "build", "--no-cache"
}

Invoke-DockerCompose "up", "-d", "--build", "--remove-orphans"

Write-Host ""
Write-ColorOutput "Waiting for database initialization to complete..." "Yellow"
$retries = 30

# Wait for db-init service to complete
$dbInitReady = $false

while ($retries -gt 0 -and -not $dbInitReady) {
    $status = (docker inspect ppap-db-init --format='{{.State.Status}}' 2>$null)
    $exitCode = (docker inspect ppap-db-init --format='{{.State.ExitCode}}' 2>$null)

    if ($status -eq "exited" -and $exitCode -eq "0") {
        $dbInitReady = $true
        Write-ColorOutput "[+] Database initialization completed" "Green"
        break
    } elseif ($status -eq "exited") {
        Write-ColorOutput "Error: Database initialization failed" "Red"
        Invoke-DockerCompose "logs", "db-init"
        exit 1
    } else {
        Write-Host "Waiting for database initialization... ($retries retries left)"
        Start-Sleep -Seconds 2
        $retries--
    }
}

if (-not $dbInitReady) {
    Write-ColorOutput "Database initialization may still be in progress. Check logs:" "Yellow"
    Write-Host "  docker compose logs db-init"
}

# 4. Wait for services to be healthy
Write-Host ""
Write-ColorOutput "Waiting for services to be healthy..." "Yellow"

# Wait for PostgreSQL
Write-Host "Waiting for PostgreSQL..."
$retries = 30
$postgresReady = $false

while (-not $postgresReady -and $retries -gt 0) {
    $null = Invoke-DockerCompose "exec", "-T", "postgres", "pg_isready", "-U", "ppap" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $postgresReady = $true
    } else {
        Write-Host "PostgreSQL: ($retries retries left)"
        Start-Sleep -Seconds 2
        $retries--
    }
}

if ($postgresReady) {
    Write-ColorOutput "[+] PostgreSQL is ready" "Green"
} else {
    Write-ColorOutput "PostgreSQL did not start in time" "Red"
    exit 1
}

# Wait for Redis
Write-Host "Waiting for Redis..."
$retries = 30
$redisReady = $false

while (-not $redisReady -and $retries -gt 0) {
    $null = Invoke-DockerCompose "exec", "-T", "redis", "redis-cli", "ping" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $redisReady = $true
    } else {
        Write-Host "Redis: ($retries retries left)"
        Start-Sleep -Seconds 2
        $retries--
    }
}

if ($redisReady) {
    Write-ColorOutput "[+] Redis is ready" "Green"
} else {
    Write-ColorOutput "Redis may still be starting" "Yellow"
}

# Wait for MinIO
Write-Host "Waiting for MinIO..."
$retries = 15
$minioReady = $false

while (-not $minioReady -and $retries -gt 0) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $minioReady = $true
        } else {
            Write-Host "MinIO: ($retries retries left)"
            Start-Sleep -Seconds 2
            $retries--
        }
    } catch {
        Write-Host "MinIO: ($retries retries left)"
        Start-Sleep -Seconds 2
        $retries--
    }
}

if ($minioReady) {
    Write-ColorOutput "[+] MinIO is ready" "Green"
} else {
    Write-ColorOutput "MinIO may still be starting" "Yellow"
}

# Wait for Backend API
Write-Host "Waiting for Backend API..."
$retries = 30
$backendReady = $false

while (-not $backendReady -and $retries -gt 0) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:31234/docs" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
        } else {
            Write-Host "Backend API: ($retries retries left)"
            Start-Sleep -Seconds 2
            $retries--
        }
    } catch {
        Write-Host "Backend API: ($retries retries left)"
        Start-Sleep -Seconds 2
        $retries--
    }
}

if ($backendReady) {
    Write-ColorOutput "[+] Backend API is ready" "Green"
} else {
    Write-ColorOutput "Backend API may still be starting" "Yellow"
}

# 5. Initialize MinIO bucket
Write-Host ""
Write-ColorOutput "Initializing MinIO bucket..." "Yellow"
Start-Sleep -Seconds 3  # Give MinIO a moment to stabilize

$retries = 5
$bucketCreated = $false

while (-not $bucketCreated -and $retries -gt 0) {
    $null = docker run --rm --network container:ppap-minio --entrypoint /bin/sh minio/mc -c "mc alias set ppapminio http://localhost:9000 minioadmin minioadmin && mc mb ppapminio/ppap-files --ignore-existing && mc anonymous set public ppapminio/ppap-files" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $bucketCreated = $true
    } else {
        Write-Host "Attempting to create MinIO bucket... ($retries retries left)"
        Start-Sleep -Seconds 3
        $retries--
    }
}

if ($bucketCreated) {
    Write-ColorOutput "[+] MinIO bucket 'ppap-files' created" "Green"
} else {
    Write-ColorOutput "⚠ MinIO bucket creation failed, may need manual setup" "Yellow"
    Write-Host "Run: docker run --rm --network container:ppap-minio minio/mc ..."
}

# 6. Final status check
Write-Host ""
Write-ColorOutput "Checking service status..." "Yellow"
Invoke-DockerCompose "ps"

Write-Host ""
Write-Host "$($GREEN)=== Deployment Completed Successfully ===$($NC)"
Write-Host "$($BLUE)Access the services at:$($NC)"
Write-Host "  🌐 Frontend UI:   $(${GREEN})http://localhost$($NC)"
Write-Host "  🔧 Backend API:   $(${GREEN})http://localhost:31234/docs$($NC)"
Write-Host "  📁 MinIO Console: $(${GREEN})http://localhost:9001$($NC) $(${YELLOW})(minioadmin / minioadmin)$($NC)"
Write-Host ""
Write-Host "$($BLUE)Default Admin Account:$($NC)"
Write-Host "  📧 Email:    $(${GREEN})admin@example.com$($NC)"
Write-Host "  🔑 Password: $(${GREEN})admin123$($NC)"
Write-Host ""
Write-Host "$($YELLOW)Next steps:$($NC)"
Write-Host "  1. Access the frontend UI at http://localhost"
Write-Host "  2. Login with admin@example.com / admin123"
Write-Host "  3. Configure LDAP/SSO in Settings if needed"
Write-Host "  4. Upload PDF files to test verification functionality"
Write-Host ""
