#!/bin/bash

# Deployment script for ADK Travel System on GKE

set -e

PROJECT_ID=${1:-"your-gcp-project-id"}
REGION=${2:-"us-central1"}
CLUSTER_NAME=${3:-"adk-travel-cluster"}

echo "🚀 Deploying ADK Travel System to GKE"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Cluster: $CLUSTER_NAME"

# Set project
gcloud config set project $PROJECT_ID

# Build and push Docker images
echo "📦 Building Docker images..."

# Build flight agent
docker build -t gcr.io/$PROJECT_ID/flight-agent:latest -f Dockerfile .
docker push gcr.io/$PROJECT_ID/flight-agent:latest

# Build hotel agent  
docker build -t gcr.io/$PROJECT_ID/hotel-agent:latest -f Dockerfile .
docker push gcr.io/$PROJECT_ID/hotel-agent:latest

# Build activity agent
docker build -t gcr.io/$PROJECT_ID/activity-agent:latest -f Dockerfile .
docker push gcr.io/$PROJECT_ID/activity-agent:latest

# Build travel coordinator
docker build -t gcr.io/$PROJECT_ID/travel-coordinator:latest -f Dockerfile .
docker push gcr.io/$PROJECT_ID/travel-coordinator:latest

# Update Kubernetes manifests with project ID
echo "📝 Updating Kubernetes manifests..."
sed -i "s/PROJECT_ID/$PROJECT_ID/g" k8s/*.yaml

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
echo "Access the travel coordinator at the LoadBalancer IP"

# Test deployment
echo "🧪 Testing deployment..."
COORDINATOR_IP=$(kubectl get service travel-coordinator -n adk-travel -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ ! -z "$COORDINATOR_IP" ]; then
    echo "Testing health endpoint..."
    curl -f http://$COORDINATOR_IP/health || echo "Health check failed"
fi