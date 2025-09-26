#!/bin/bash

# ADK Travel Agents - Deploy Only Script
# Assumes cluster and infrastructure already exist
# Usage: ./scripts/deploy-only.sh PROJECT_ID [REGION] [CLUSTER_NAME]

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default values
DEFAULT_REGION="us-central1"
DEFAULT_CLUSTER_NAME="adk-travel-cluster"
NAMESPACE="adk-travel"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Validation
if [ $# -lt 1 ] || [ $# -gt 3 ]; then
    echo "Usage: $0 PROJECT_ID [REGION] [CLUSTER_NAME]"
    echo ""
    echo "This script assumes:"
    echo "  - GKE cluster already exists"
    echo "  - Artifact Registry repository exists" 
    echo "  - Service accounts are configured"
    echo "  - APIs are enabled"
    echo ""
    exit 1
fi

PROJECT_ID="$1"
REGION="${2:-$DEFAULT_REGION}"
CLUSTER_NAME="${3:-$DEFAULT_CLUSTER_NAME}"

print_status "🚀 Deploying ADK Travel Agents (Apps Only)"
print_status "Project: $PROJECT_ID"
print_status "Region: $REGION"
print_status "Cluster: $CLUSTER_NAME"

# Check prerequisites
print_status "Checking prerequisites..."
for cmd in gcloud kubectl docker; do
    if ! command -v $cmd &> /dev/null; then
        print_error "$cmd is required but not installed"
    fi
done

# Set project
gcloud config set project "$PROJECT_ID" --quiet

# Verify cluster exists and get credentials
print_status "Connecting to existing cluster..."
if ! gcloud container clusters describe "$CLUSTER_NAME" --region="$REGION" &>/dev/null; then
    print_error "Cluster '$CLUSTER_NAME' not found in region '$REGION'"
fi

gcloud container clusters get-credentials "$CLUSTER_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID"

print_success "Connected to cluster $CLUSTER_NAME"

# Verify namespace exists
print_status "Checking namespace..."
if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
    print_warning "Namespace '$NAMESPACE' not found, creating it..."
    kubectl create namespace "$NAMESPACE"
fi

# Create Artifact Registry repository if it doesn't exist
REGISTRY_URL="$REGION-docker.pkg.dev/$PROJECT_ID/adk-travel"
print_status "Checking/Creating Artifact Registry..."
if ! gcloud artifacts repositories describe adk-travel --location="$REGION" &>/dev/null; then
    print_status "Creating Artifact Registry repository..."
    gcloud artifacts repositories create adk-travel \
        --repository-format=docker \
        --location="$REGION" \
        --description="ADK Travel agents Docker images" \
        --quiet
    print_success "Artifact Registry repository 'adk-travel' created"
else
    print_success "Artifact Registry repository 'adk-travel' already exists"
fi

# Configure Docker authentication
print_status "Configuring Docker authentication..."
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

# Build and push Docker images
print_status "🐳 Building and pushing Docker images..."

# Build flight agent
if [ -d "docker/flight-agent" ]; then
    print_status "Building flight-agent..."
    cd docker/flight-agent
    docker build -t "$REGISTRY_URL/flight-agent:latest" .
    docker push "$REGISTRY_URL/flight-agent:latest"
    cd ../..
    print_success "flight-agent image pushed"
else
    print_warning "docker/flight-agent directory not found"
fi

# Build coordinator
if [ -d "docker/coordinator" ]; then
    print_status "Building coordinator..."
    cd docker/coordinator
    docker build -t "$REGISTRY_URL/coordinator:latest" .
    docker push "$REGISTRY_URL/coordinator:latest"
    cd ../..
    print_success "coordinator image pushed"
else
    print_warning "docker/coordinator directory not found"
fi

# Apply ConfigMap (update project ID)
print_status "📝 Applying ConfigMap..."
if [ -f "k8s/configmap.yaml" ]; then
    sed "s/PROJECT_ID/$PROJECT_ID/g" k8s/configmap.yaml | kubectl apply -f -
    print_success "ConfigMap applied"
fi

# Apply RBAC (update project ID)
print_status "🔐 Applying RBAC..."
if [ -f "k8s/rbac.yaml" ]; then
    sed "s/PROJECT_ID/$PROJECT_ID/g" k8s/rbac.yaml | kubectl apply -f -
    print_success "RBAC applied"
fi

# Deploy applications
print_status "☸️  Deploying applications..."

# Apply all deployments
if [ -d "k8s/deployments" ]; then
    for file in k8s/deployments/*.yaml; do
        if [ -f "$file" ]; then
            print_status "Applying $(basename "$file")..."
            sed -e "s/REGION/$REGION/g" -e "s/PROJECT_ID/$PROJECT_ID/g" "$file" | kubectl apply -f -
        fi
    done
    print_success "All deployments applied"
else
    print_warning "k8s/deployments directory not found"
fi

# Wait for deployments to be ready
print_status "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment --all -n "$NAMESPACE" || {
    print_warning "Some deployments may not be ready yet"
    kubectl get pods -n "$NAMESPACE"
}

# Get deployment status
print_status "📊 Deployment Status:"
echo ""
kubectl get all -n "$NAMESPACE"

# Get service endpoints
print_status "🌐 Service Information:"
kubectl get services -n "$NAMESPACE" -o wide

# Check for LoadBalancer IP
EXTERNAL_IP=$(kubectl get service travel-coordinator -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

if [ ! -z "$EXTERNAL_IP" ]; then
    echo ""
    print_success "🎉 External IP available: $EXTERNAL_IP"
    echo ""
    echo "Test commands:"
    echo "curl http://$EXTERNAL_IP/health"
    echo "curl -X POST http://$EXTERNAL_IP/chat -H 'Content-Type: application/json' -d '{\"message\": \"Plan a trip to Tokyo\"}'"
else
    echo ""
    print_status "🔄 LoadBalancer IP not ready yet. Use port-forward for testing:"
    echo ""
    echo "kubectl port-forward service/travel-coordinator 8080:80 -n $NAMESPACE"
    echo "curl http://localhost:8080/health"
    echo "curl -X POST http://localhost:8080/chat -H 'Content-Type: application/json' -d '{\"message\": \"Plan a trip to Tokyo\"}'"
fi

# Show pod logs if there are issues
FAILED_PODS=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
if [ "$FAILED_PODS" -gt 0 ]; then
    print_warning "Some pods are not running:"
    kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running
    echo ""
    print_status "Recent events:"
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -5
fi

# Save deployment info
cat > deployment-status.txt << EOF
ADK Travel Agents - Deploy Only Status
=====================================
Timestamp: $(date)
Project: $PROJECT_ID
Region: $REGION
Cluster: $CLUSTER_NAME
Namespace: $NAMESPACE

Images Built and Pushed:
✅ $REGISTRY_URL/flight-agent:latest
✅ $REGISTRY_URL/coordinator:latest

Quick Test Commands:
$(if [ ! -z "$EXTERNAL_IP" ]; then
echo "curl http://$EXTERNAL_IP/health"
echo "curl -X POST http://$EXTERNAL_IP/chat -H 'Content-Type: application/json' -d '{\"message\": \"Find flights to Tokyo\"}'"
else
echo "kubectl port-forward service/travel-coordinator 8080:80 -n $NAMESPACE"
echo "curl http://localhost:8080/health"
echo "curl -X POST http://localhost:8080/chat -H 'Content-Type: application/json' -d '{\"message\": \"Find flights to Tokyo\"}'"
fi)

Management Commands:
kubectl get pods -n $NAMESPACE
kubectl logs -f deployment/travel-coordinator -n $NAMESPACE
kubectl get services -n $NAMESPACE
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'
EOF

print_success "✅ Application deployment completed!"
print_status "📄 Status saved to: deployment-status.txt"

# Final verification
RUNNING_PODS=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Running --no-headers | wc -l)
TOTAL_PODS=$(kubectl get pods -n "$NAMESPACE" --no-headers | wc -l)

echo ""
print_status "Final Status: $RUNNING_PODS/$TOTAL_PODS pods running"

if [ "$RUNNING_PODS" -eq "$TOTAL_PODS" ] && [ "$TOTAL_PODS" -gt 0 ]; then
    print_success "🎉 All applications deployed successfully!"
else
    print_warning "⚠️  Some applications may still be starting up"
    print_status "Check status with: kubectl get pods -n $NAMESPACE"
fi

echo ""
print_success "🚀 ADK Travel Agents deployment complete!"