# PPAP Platform Deployment Script for Windows
# This script sets up the PPAP environment and starts all necessary services using Docker Compose.
# Supports the new automated database initialization via db-init service

param(
    [switch]$ForceRebuild = $false
)

# Colors for output - Use native PowerShell colors for compatibility
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput $Message "Green"
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput $Message "Cyan"
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput $Message "Yellow"
}

function Write-Error-Color {
    param([string]$Message)
    Write-ColorOutput $Message "Red"
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

Write-Host "=== PPAP Platform Deployment ===" -ForegroundColor Green
Write-Host "Updated version with automated database initialization" -ForegroundColor Cyan
Write-Host ""

# 1. Check prerequisites
Write-Warning "Checking prerequisites..."

# Check if Docker is running
if (-not (Test-Docker)) {
    Write-Error-Color "Error: Docker daemon is not running."
    Write-Host "Please start Docker Desktop and try again."
    exit 1
}
Write-Success "[+] Docker is installed"

# Determine which Docker Compose command to use
if (Test-DockerCompose) {
    $DOCKER_COMPOSE_CMD = "docker compose"
    Write-Success "[+] Using 'docker compose' command"
} elseif (Test-DockerComposeLegacy) {
    $DOCKER_COMPOSE_CMD = "docker-compose"
    Write-Success "[+] Using 'docker-compose' command"
} else {
    Write-Error-Color "Error: Neither 'docker compose' nor 'docker-compose' is installed."
    exit 1
}

# Check if Docker daemon is running
if (-not (Test-Docker)) {
    Write-Error-Color "Error: Docker daemon is not running."
    Write-Host "Please start Docker Desktop and try again."
    exit 1
}

Write-Success "[+] Docker daemon is running"
Write-Host ""

# Check if there are code changes that might require rebuild
$hasChanges = $false
$gitRoot = git rev-parse --show-toplevel 2>$null
if ($gitRoot) {
    # Check for uncommitted changes in backend or frontend
    $changedFiles = git status --porcelain backend frontend 2>$null
    if ($changedFiles) {
        $hasChanges = $true
        Write-Warning "Detected uncommitted changes in backend/frontend code."
        Write-Host "  Use '.\deploy.ps1 -ForceRebuild' to force rebuild containers."
    }
}

if (-not $hasChanges -and -not $ForceRebuild) {
    # Check if containers are already running
    $runningContainers = docker ps --filter "name=ppap-" --format "{{.Names}}" 2>$null
    if ($runningContainers) {
        Write-Info "Containers are already running. Use '-ForceRebuild' to rebuild."
        $rebuild = Read-Host "Force rebuild now? (y/N)"
        if ($rebuild -eq 'y' -or $rebuild -eq 'Y') {
            $ForceRebuild = $true
        }
    }
}

# 2. Setup Environment Variables
Write-Warning "Setting up environment variables..."
cd deploy

$envFile = ".env"
$envExample = ".env.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Success "[+] Created .env from .env.example"
        Write-Warning "  Please remember to change default secrets for production!"
    } else {
        Write-Warning "Creating basic .env file..."
@"
# PPAP Environment Configuration
SECRET_KEY=change-this-in-production
"@ | Out-File -FilePath $envFile -Encoding UTF8
        Write-Success "[+] Created basic .env file"
    }
} else {
    Write-Success "[+] Found existing .env file"
}
Write-Host ""

# 3. Start services with automated database initialization
Write-Warning "Starting services with automated database initialization..."
Write-Info "The db-init service will automatically run init-db.sql"

if ($ForceRebuild) {
    Write-Warning "Force rebuilding all containers without cache..."
    Invoke-DockerCompose "build", "--no-cache"
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Color "Error: Docker build failed!"
        exit 1
    }
}

Write-Host "Building and starting containers..."
Invoke-DockerCompose "up", "-d", "--build", "--remove-orphans" | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Error-Color "Error: Failed to start containers! Check 'docker compose logs' for details."
    exit 1
}
Write-Success "[+] Containers started successfully"

Write-Host ""
Write-Warning "Waiting for database initialization to complete..."
$retries = 30

# Wait for db-init service to complete
$dbInitReady = $false

while ($retries -gt 0 -and -not $dbInitReady) {
    $status = (docker inspect ppap-db-init --format='{{.State.Status}}' 2>$null)
    $exitCode = (docker inspect ppap-db-init --format='{{.State.ExitCode}}' 2>$null)

    if ($status -eq "exited" -and $exitCode -eq "0") {
        $dbInitReady = $true
        Write-Success "[+] Database initialization completed"
        break
    } elseif ($status -eq "exited") {
        Write-Error-Color "Error: Database initialization failed"
        Invoke-DockerCompose "logs", "db-init"
        exit 1
    } else {
        Write-Host "Waiting for database initialization... ($retries retries left)"
        Start-Sleep -Seconds 2
        $retries--
    }
}

if (-not $dbInitReady) {
    Write-Warning "Database initialization may still be in progress. Check logs:"
    Write-Host "  docker compose logs db-init"
}

# 4. Wait for services to be healthy
Write-Host ""
Write-Warning "Waiting for services to be healthy..."

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
    Write-Success "[+] PostgreSQL is ready"
} else {
    Write-Error-Color "PostgreSQL did not start in time"
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
    Write-Success "[+] Redis is ready"
} else {
    Write-Warning "Redis may still be starting"
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
    Write-Success "[+] MinIO is ready"
} else {
    Write-Warning "MinIO may still be starting"
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
    Write-Success "[+] Backend API is ready"
} else {
    Write-Warning "Backend API may still be starting"
}

# 5. Initialize MinIO bucket
Write-Host ""
Write-Warning "Initializing MinIO bucket..."
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
    Write-Success "[+] MinIO bucket 'ppap-files' created"
} else {
    Write-Warning "⚠ MinIO bucket creation failed, may need manual setup"
    Write-Host "Run: docker run --rm --network container:ppap-minio minio/mc ..."
}

# 6. Final status check
Write-Host ""
Write-Warning "Checking service status..."
Invoke-DockerCompose "ps"

Write-Host ""
Write-Host "=== Deployment Completed Successfully ===" -ForegroundColor Green
Write-Host "Access the services at:" -ForegroundColor Cyan
Write-Host "  🌐 Frontend UI:   " -NoNewline; Write-Host "http://localhost" -ForegroundColor Green
Write-Host "  🔧 Backend API:   " -NoNewline; Write-Host "http://localhost:31234/docs" -ForegroundColor Green
Write-Host "  📁 MinIO Console: " -NoNewline; Write-Host "http://localhost:9001" -ForegroundColor Green; Write-Host " (minioadmin / minioadmin)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Default Admin Account:" -ForegroundColor Cyan
Write-Host "  📧 Email:    " -NoNewline; Write-Host "admin@example.com" -ForegroundColor Green
Write-Host "  🔑 Password: " -NoNewline; Write-Host "admin123" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Access the frontend UI at http://localhost"
Write-Host "  2. Login with admin@example.com / admin123"
Write-Host "  3. Configure LDAP/SSO in Settings if needed"
Write-Host "  4. Upload PDF files to test verification functionality"
Write-Host ""
