# =============================================================================
# Launch Annual Report Analyser
# Always runs from src directory for consistency
# =============================================================================

$ErrorActionPreference = "Stop"

# Get script location (project root)
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SrcDir = Join-Path $ProjectRoot "src"

# Change to src directory
Set-Location $SrcDir
Write-Host "Working directory: $SrcDir" -ForegroundColor Green

# Activate virtual environment
$VenvPath = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & $VenvPath
}

# Run Streamlit
Write-Host "Starting Streamlit app..." -ForegroundColor Cyan
streamlit run app.py
