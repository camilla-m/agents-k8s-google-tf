#!/bin/bash

# Deployment script for ADK Travel System on GKE

set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PROJECT_ID=${1:-"your-gcp-project-id"}
REGION=${2:-"us-central1"}
CLUSTER_NAME=${3:-"adk-travel-cluster"}

echo "🚀 Deploying ADK Travel System to GKE"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Cluster: $CLUSTER_NAME"
echo "Script dir: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"

# Set project
gcloud config set project $PROJECT_ID

# Navigate to project root
cd "$PROJECT_ROOT"

# Check if Dockerfile exists
if [ ! -f "Dockerfile" ]; then
    echo "❌ Dockerfile not found in $PROJECT_ROOT"
    exit 1
fi

echo "✅ Dockerfile found, building images..."

# Build and push Docker images
echo "📦 Building Docker images..."

# Build flight agent
echo "Building flight-agent..."
docker build -t gcr.io/$PROJECT_ID/flight-agent:latest \
  --build-arg AGENT_TYPE=flight \
  -f Dockerfile .
docker push gcr.io/$PROJECT_ID/flight-agent:latest

# Build hotel agent  
echo "Building hotel-agent..."
docker build -t gcr.io/$PROJECT_ID/hotel-agent:latest \
  --build-arg AGENT_TYPE=hotel \
  -f Dockerfile .
docker push gcr.io/$PROJECT_ID/hotel-agent:latest

# Build activity agent
echo "Building activity-agent..."
docker build -t gcr.io/$PROJECT_ID/activity-agent:latest \
  --build-arg AGENT_TYPE=activity \
  -f Dockerfile .
docker push gcr.io/$PROJECT_ID/activity-agent:latest

# Build travel coordinator
echo "Building travel-coordinator..."
docker build -t gcr.io/$PROJECT_ID/travel-coordinator:latest \
  --build-arg AGENT_TYPE=coordinator \
  -f Dockerfile .
docker push gcr.io/$PROJECT_ID/travel-coordinator:latest

# Update Kubernetes manifests with project ID
echo "📝 Updating Kubernetes manifests..."
if [ -d "k8s" ]; then
    # Create backup of original manifests
    cp -r k8s k8s.backup.$(date +%s) 2>/dev/null || true
    
    # Replace PROJECT_ID in all yaml files
    find k8s -name "*.yaml" -exec sed -i.bak "s/PROJECT_ID/$PROJECT_ID/g" {} \;
    
    # Remove backup files
    find k8s -name "*.bak" -delete
    
    echo "✅ Kubernetes manifests updated"
else
    echo "❌ k8s directory not found"
    exit 1
fi

# Get GKE credentials
echo "🔐 Getting GKE credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION

# Apply Kubernetes manifests
echo "⚙️ Applying Kubernetes manifests..."
kubectl apply -f k8s/

# Wait for deployments
echo "⏳ Waiting for deployments..."
kubectl wait --for=condition=available --timeout=300s deployment --all -n adk-travel

# Get service endpoints
echo "🌐 Service endpoints:"
kubectl get services -n adk-travel

echo "✅ Deployment complete!"
echo ""
echo "🎯 Next steps:"
echo "kubectl port-forward service/travel-coordinator 8080:80 -n adk-travel"
echo "python scripts/test_demo.py"