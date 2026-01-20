#!/usr/bin/env bash
set -euo pipefail

# Azure Container Apps deployment for fna_docs
# Run from docs_mcp/deploys directory

RESOURCE_GROUP="${RESOURCE_GROUP:-fna-docs-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-fnadocsacr}"
APP_NAME="${APP_NAME:-fna-docs-mcp}"
ENVIRONMENT="${ENVIRONMENT:-fna-docs-env}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCS_MCP_DIR="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$HOME/fna_docs/docs"

# Generate one-time API key
MCP_API_KEY=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
echo ""
echo "=========================================="
echo "API KEY: $MCP_API_KEY"
echo "=========================================="
echo ""

echo "=== Azure Container Apps Deployment ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "ACR: $ACR_NAME"
echo "App: $APP_NAME"

# Check prerequisites
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI not installed"
    exit 1
fi

# Ensure logged in
az account show &> /dev/null || { echo "Error: Not logged in. Run 'az login'"; exit 1; }

# Create resource group if needed
echo "Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none 2>/dev/null || true

# Create ACR if needed
echo "Creating container registry..."
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic --output none 2>/dev/null || true

# Enable admin access for ACR
az acr update --name "$ACR_NAME" --admin-enabled true --output none

# Get ACR credentials
ACR_SERVER="$ACR_NAME.azurecr.io"
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

# Build image with docs from this repo
echo "Building Docker image..."
TEMP_BUILD=$(mktemp -d)
trap "rm -rf $TEMP_BUILD" EXIT

# Copy docs_mcp base
cp -r "$DOCS_MCP_DIR"/* "$TEMP_BUILD/"
rm -rf "$TEMP_BUILD/.venv" "$TEMP_BUILD/.ruff_cache" "$TEMP_BUILD/.git"

# Replace docs with our docs
rm -rf "$TEMP_BUILD/docs"
cp -r "$DOCS_DIR" "$TEMP_BUILD/docs"

# Build and push
az acr build \
    --registry "$ACR_NAME" \
    --image "$APP_NAME:$IMAGE_TAG" \
    "$TEMP_BUILD"

# Create Container Apps environment if needed
echo "Creating Container Apps environment..."
az containerapp env create \
    --name "$ENVIRONMENT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none 2>/dev/null || true

# Deploy/update container app
echo "Deploying container app..."
az containerapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENVIRONMENT" \
    --image "$ACR_SERVER/$APP_NAME:$IMAGE_TAG" \
    --registry-server "$ACR_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --target-port 8000 \
    --ingress external \
    --env-vars "DOCS_DIR=./docs" "MCP_NAME=fna-docs" "MCP_API_KEY=$MCP_API_KEY" \
    --min-replicas 0 \
    --max-replicas 1 \
    --cpu 0.25 \
    --memory 0.5Gi \
    --output none 2>/dev/null || \
az containerapp update \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$ACR_SERVER/$APP_NAME:$IMAGE_TAG" \
    --output none

# Get app URL
APP_URL=$(az containerapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo "=== Deployment Complete ==="
echo "App URL: https://$APP_URL"
echo "Health: https://$APP_URL/health"
echo "MCP endpoint: https://$APP_URL/mcp"
echo ""
echo "API KEY: $MCP_API_KEY"
echo "(Use with 'Authorization: Bearer $MCP_API_KEY' or 'x-api-key: $MCP_API_KEY')"
