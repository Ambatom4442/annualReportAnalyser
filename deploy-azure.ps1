# =============================================================================
# Azure Container Instance Deployment Script
# =============================================================================
# Prerequisites:
#   1. Azure CLI installed: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
#   2. Docker Desktop installed
#   3. Logged into Azure: az login
#   4. Logged into Azure Container Registry: az acr login --name <registry>
# =============================================================================

# Configuration - UPDATE THESE VALUES
$RESOURCE_GROUP = "rg-annual-report-analyser"
$LOCATION = "swedencentral"  # Azure region
$ACR_NAME = "aaborgenacr"  # Your Azure Container Registry name (must be globally unique)
$CONTAINER_NAME = "annual-report-analyser"
$IMAGE_NAME = "annual-report-analyser"
$IMAGE_TAG = "latest"

# Full image path
$FULL_IMAGE = "$ACR_NAME.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Azure Container Instance Deployment" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Step 1: Build Docker image
Write-Host "`n[1/5] Building Docker image..." -ForegroundColor Yellow
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
if ($LASTEXITCODE -ne 0) { Write-Host "Docker build failed!" -ForegroundColor Red; exit 1 }

# Step 2: Tag for Azure Container Registry
Write-Host "`n[2/5] Tagging image for ACR..." -ForegroundColor Yellow
docker tag ${IMAGE_NAME}:${IMAGE_TAG} $FULL_IMAGE

# Step 3: Login to ACR
Write-Host "`n[3/5] Logging into Azure Container Registry..." -ForegroundColor Yellow
az acr login --name $ACR_NAME
if ($LASTEXITCODE -ne 0) { Write-Host "ACR login failed!" -ForegroundColor Red; exit 1 }

# Step 4: Push to ACR
Write-Host "`n[4/5] Pushing image to ACR..." -ForegroundColor Yellow
docker push $FULL_IMAGE
if ($LASTEXITCODE -ne 0) { Write-Host "Docker push failed!" -ForegroundColor Red; exit 1 }

# Step 5: Deploy to Azure Container Instance
Write-Host "`n[5/5] Deploying to Azure Container Instance..." -ForegroundColor Yellow

# Get ACR credentials
$ACR_USERNAME = az acr credential show --name $ACR_NAME --query username -o tsv
$ACR_PASSWORD = az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv

# Prompt for API key if not set
if (-not $env:GEMINI_API_KEY) {
    $GEMINI_API_KEY = Read-Host "Enter your GEMINI_API_KEY"
} else {
    $GEMINI_API_KEY = $env:GEMINI_API_KEY
}

# Create/Update container instance
az container create `
    --resource-group $RESOURCE_GROUP `
    --name $CONTAINER_NAME `
    --image $FULL_IMAGE `
    --cpu 2 `
    --memory 4 `
    --ports 8501 `
    --dns-name-label $CONTAINER_NAME `
    --registry-login-server "$ACR_NAME.azurecr.io" `
    --registry-username $ACR_USERNAME `
    --registry-password $ACR_PASSWORD `
    --environment-variables `
        GEMINI_API_KEY=$GEMINI_API_KEY `
        STREAMLIT_SERVER_PORT=8501 `
        PYTHONPATH=/app/src `
    --restart-policy OnFailure `
    --location $LOCATION

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=============================================" -ForegroundColor Green
    Write-Host "Deployment Successful!" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Green
    
    # Get the FQDN
    $FQDN = az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query ipAddress.fqdn -o tsv
    Write-Host "`nYour app is available at: http://${FQDN}:8501" -ForegroundColor Cyan
} else {
    Write-Host "`nDeployment failed!" -ForegroundColor Red
}
