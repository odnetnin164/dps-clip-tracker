# DPS Clip Tracker - Windows Run Script
# This script sets up and runs the DPS Clip Tracker application on Windows

param(
    [switch]$Clean,
    [switch]$Build,
    [switch]$Help
)

# Show help
if ($Help) {
    Write-Host "DPS Clip Tracker - Windows Run Script" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\run.ps1          - Run the application"
    Write-Host "  .\run.ps1 -Clean   - Clean and reinstall dependencies"
    Write-Host "  .\run.ps1 -Build   - Build executable"
    Write-Host "  .\run.ps1 -Help    - Show this help"
    Write-Host ""
    Write-Host "Note: This application requires administrator privileges for global hotkey functionality."
    exit 0
}

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Warning "This application requires administrator privileges for global hotkey functionality."
    Write-Host "Please run this script as Administrator or the hotkeys may not work properly." -ForegroundColor Yellow
    Write-Host ""
}

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.11+ and try again."
    exit 1
}

# Clean installation if requested
if ($Clean) {
    Write-Host "Cleaning previous installation..." -ForegroundColor Yellow
    if (Test-Path "venv") {
        Remove-Item -Recurse -Force "venv"
    }
    if (Test-Path "build") {
        Remove-Item -Recurse -Force "build"
    }
    if (Test-Path "dist") {
        Remove-Item -Recurse -Force "dist"
    }
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
}

# Activate virtual environment and install dependencies
Write-Host "Setting up dependencies..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies"
    exit 1
}

# Build executable if requested
if ($Build) {
    Write-Host "Building executable..." -ForegroundColor Yellow
    python build_spec.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build executable"
        exit 1
    }
    Write-Host "Executable built successfully in dist\ directory" -ForegroundColor Green
    exit 0
}

# Run the application
Write-Host "Starting DPS Clip Tracker..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the application" -ForegroundColor Cyan
Write-Host ""

python -m src.main