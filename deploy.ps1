# PPAP Platform Deployment Script for Windows
# This script sets up the PPAP environment and starts all necessary services using Docker Compose.
# Supports the new automated database initialization via db-init service

param(
    [switch]$ForceRebuild = $false
)

# Configurable host and ports (for remote/SSH forwarding scenarios)
$apiHost = $env:API_HOST ?? "localhost"
$apiPort = $env:API_PORT ?? "31234"
$minioPort = $env:MINIO_PORT ?? "9000"
$minioConsolePort = $env:MINIO_CONSOLE_PORT ?? "9001"

# Colors for output - Use native PowerShell colors for compatibility
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Write UTF-8 without BOM (compatible with PS 5.x and 7+)
function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
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
    if (Test-DockerCompose) {
        $fullArgs = @("compose") + $args
        & docker @fullArgs
    } else {
        $dcArgs = @($args)
        & docker-compose @dcArgs
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

Write-Host ""

# Check if there are code changes that might require rebuild
$hasChanges = $false
$projectRoot = $PSScriptRoot
if (-not $projectRoot) { $projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition }

# Only check git if .git directory exists and git is available
if ((Test-Path "$projectRoot\.git") -and (Get-Command git -ErrorAction SilentlyContinue)) {
    $changedFiles = git -C $projectRoot status --porcelain backend frontend 2>$null
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

# Sync new keys from .env.example to existing .env
if ((Test-Path $envFile) -and (Test-Path $envExample)) {
    $exampleLines = Get-Content $envExample
    $envContent = Get-Content $envFile -Raw
    foreach ($line in $exampleLines) {
        if ($line -match '^\s*#' -or $line -match '^\s*$') { continue }
        if ($line -match '^([^=]+)=') {
            $key = $Matches[1].Trim()
            if (-not ($envContent -match "^${key}=")) {
                Add-Content -Path $envFile -Value $line
                Write-Host "Added new config: $key"
            }
        }
    }
}

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Success "[+] Created .env from .env.example"
    } else {
        Write-Warning "Creating basic .env file..."
        $basicEnv = @"
# PPAP Environment Configuration
SECRET_KEY=change-this-in-production
POSTGRES_PASSWORD=ppap123
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
REDIS_PASSWORD=redis-secret-pass
"@
        Write-Utf8NoBom -Path $envFile -Content $basicEnv
        Write-Success "[+] Created basic .env file"
    }

    # Auto-generate strong secrets for first-time deployment
    $secretKey = -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })
    $charSet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    $dbPass = -join ((1..20) | ForEach-Object { $charSet[(Get-Random -Maximum 62)] })
    $minioPass = -join ((1..20) | ForEach-Object { $charSet[(Get-Random -Maximum 62)] })
    $redisPass = -join ((1..16) | ForEach-Object { $charSet[(Get-Random -Maximum 62)] })
    $adminPass = -join ((1..12) | ForEach-Object { $charSet[(Get-Random -Maximum 62)] })

    $envContent = Get-Content $envFile -Raw
    $envContent = $envContent -replace '^SECRET_KEY=.*', "SECRET_KEY=$secretKey"
    $envContent = $envContent -replace '^POSTGRES_PASSWORD=.*', "POSTGRES_PASSWORD=$dbPass"
    $envContent = $envContent -replace '^MINIO_ROOT_PASSWORD=.*', "MINIO_ROOT_PASSWORD=$minioPass"
    $envContent = $envContent -replace '^REDIS_PASSWORD=.*', "REDIS_PASSWORD=$redisPass"
    Write-Utf8NoBom -Path $envFile -Content $envContent

    Write-Success "[+] Auto-generated strong secrets (saved to .env)"
    Write-Warning "  ⚠ Save these credentials securely! DB password: $dbPass"

    # P2-5: Generate bcrypt hash for admin password and replace in init-db.sql
    try {
        $pyScript = @"
import bcrypt, sys
sys.stdout.write(bcrypt.hashpw(b'$adminPass', bcrypt.gensalt()).decode())
"@
        $adminHash = python -c $pyScript 2>$null
        if ($adminHash) {
            $initDbPath = Join-Path $PSScriptRoot "deploy/init-db.sql"
            if (-not (Test-Path $initDbPath)) {
                $initDbPath = "init-db.sql"
            }
            if (Test-Path $initDbPath) {
                # Replace the bcrypt hash pattern in init-db.sql
                $content = Get-Content $initDbPath -Raw
                $updated = $content -replace '\$2b\$\d+\$[A-Za-z0-9./]+', $adminHash
                Write-Utf8NoBom -Path $initDbPath -Content $updated
                Write-Success "[+] Admin password set to: $adminPass"
            }
            # Write hash to .env for db-init container (existing databases)
            Add-Content -Path $envFile -Value "ADMIN_PASSWORD_HASH=$adminHash"
            $env:ADMIN_PASSWORD_HASH = $adminHash
        } else {
            Write-Warning "  ⚠ Python/bcrypt not available, using default admin password (admin123)"
        }
    } catch {
        Write-Warning "  ⚠ Could not generate admin password hash, using default (admin123)"
    }
} else {
    Write-Success "[+] Found existing .env file (reusing saved secrets)"
    # Ensure ADMIN_PASSWORD_HASH exists in .env for existing deployments
    $envContent = Get-Content $envFile -Raw
    if (-not ($envContent -match 'ADMIN_PASSWORD_HASH')) {
        try {
            $pyScript = @"
import bcrypt, sys
sys.stdout.write(bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode())
"@
            $adminHash = python -c $pyScript 2>$null
            if ($adminHash) {
                Add-Content -Path $envFile -Value "ADMIN_PASSWORD_HASH=$adminHash"
                Write-Warning "[+] Generated ADMIN_PASSWORD_HASH for existing deployment"
            }
        } catch {}
    }
}
# Load ADMIN_PASSWORD_HASH into environment for docker-compose
$envContent = Get-Content $envFile -Raw
if ($envContent -match 'ADMIN_PASSWORD_HASH=(.+)') {
    $env:ADMIN_PASSWORD_HASH = $Matches[1].Trim()
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
        $response = Invoke-WebRequest -Uri "http://${apiHost}:${minioPort}/minio/health/live" -UseBasicParsing -TimeoutSec 2
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
        $response = Invoke-WebRequest -Uri "http://${apiHost}:${apiPort}/docs" -UseBasicParsing -TimeoutSec 2
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

# 5. Wait for MinIO bucket initialization
Write-Host ""
Write-Warning "Waiting for MinIO bucket initialization..."

$retries = 30
$minioInitReady = $false

while ($retries -gt 0 -and -not $minioInitReady) {
    $status = (docker inspect ppap-minio-init --format='{{.State.Status}}' 2>$null)
    $exitCode = (docker inspect ppap-minio-init --format='{{.State.ExitCode}}' 2>$null)

    if ($status -eq "exited" -and $exitCode -eq "0") {
        $minioInitReady = $true
        Write-Success "[+] MinIO bucket 'ppap-files' initialized"
        break
    } elseif ($status -eq "exited") {
        Write-Error-Color "Error: MinIO bucket initialization failed"
        Invoke-DockerCompose "logs", "minio-init"
        Write-Warning "⚠ Continuing anyway, may need manual bucket setup"
        break
    } else {
        Write-Host "Waiting for MinIO bucket initialization... ($retries retries left)"
        Start-Sleep -Seconds 2
        $retries--
    }
}

if (-not $minioInitReady -and $retries -eq 0) {
    Write-Warning "MinIO bucket initialization may still be in progress. Check logs:"
    Write-Host "  docker compose logs minio-init"
}

# 6. Final status check
Write-Host ""
Write-Warning "Checking service status..."
Invoke-DockerCompose "ps"

Write-Host ""
Write-Host "=== Deployment Completed Successfully ===" -ForegroundColor Green
Write-Host "Access the services at:" -ForegroundColor Cyan
Write-Host "  🌐 Frontend UI:   " -NoNewline; Write-Host "http://${apiHost}" -ForegroundColor Green
Write-Host "  🔧 Backend API:   " -NoNewline; Write-Host "http://${apiHost}:${apiPort}/docs" -ForegroundColor Green
Write-Host "  📁 MinIO Console: " -NoNewline; Write-Host "http://${apiHost}:${minioConsolePort}" -ForegroundColor Green; Write-Host " (minioadmin)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Default Admin Account:" -ForegroundColor Cyan
Write-Host "  📧 Email:    " -NoNewline; Write-Host "admin@example.com" -ForegroundColor Green
Write-Host "  🔑 Password: " -NoNewline; Write-Host $(if ($adminPass) { $adminPass } else { "admin123" }) -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Access the frontend UI at http://localhost"
Write-Host "  2. Login with admin@example.com / admin123"
Write-Host "  3. Configure LDAP/SSO in Settings if needed"
Write-Host "  4. Upload PDF files to test verification functionality"
Write-Host ""
