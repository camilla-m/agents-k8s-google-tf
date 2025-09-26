#!/bin/bash

# ADK Travel Agents - Deploy Script (Current Structure)
# Adapted for: Dockerfile in root, src/ folder, k8s/ manifests
# Usage: ./scripts/deploy-current-structure.sh PROJECT_ID [REGION] [CLUSTER_NAME]

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
IMAGE_NAME="adk-travel-app"

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
    echo "Current project structure expected:"
    echo "  ├── Dockerfile          # Main Dockerfile in root"
    echo "  ├── src/               # Application source code"
    echo "  ├── k8s/               # Kubernetes manifests"
    echo "  └── scripts/           # This script"
    echo ""
    exit 1
fi

PROJECT_ID="$1"
REGION="${2:-$DEFAULT_REGION}"
CLUSTER_NAME="${3:-$DEFAULT_CLUSTER_NAME}"

print_status "🚀 Deploying ADK Travel (Current Structure)"
print_status "Project: $PROJECT_ID"
print_status "Region: $REGION"
print_status "Cluster: $CLUSTER_NAME"

# Check project structure
print_status "🔍 Checking project structure..."
MISSING_ITEMS=()

if [ ! -f "Dockerfile" ]; then
    MISSING_ITEMS+=("Dockerfile (in root)")
fi

if [ ! -d "src" ]; then
    MISSING_ITEMS+=("src/ directory")
fi

if [ ! -d "k8s" ]; then
    MISSING_ITEMS+=("k8s/ directory")
fi

if [ ${#MISSING_ITEMS[@]} -gt 0 ]; then
    print_error "Missing required items: ${MISSING_ITEMS[*]}"
fi

print_success "✅ Project structure validated"

# Check prerequisites
print_status "🔧 Checking prerequisites..."
for cmd in gcloud kubectl docker; do
    if ! command -v $cmd &> /dev/null; then
        print_error "$cmd is required but not installed"
    fi
done

# Set project
gcloud config set project "$PROJECT_ID" --quiet

# Enable required APIs
print_status "📡 Enabling required APIs..."
REQUIRED_APIS=(
    "artifactregistry.googleapis.com"
    "container.googleapis.com" 
    "compute.googleapis.com"
    "aiplatform.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "^$api$"; then
        print_status "Enabling $api..."
        gcloud services enable "$api" --quiet
    fi
done
print_success "Required APIs enabled"

# Wait for API propagation
print_status "Waiting for API propagation (30 seconds)..."
sleep 30

# Create/Check Artifact Registry
REGISTRY_URL="$REGION-docker.pkg.dev/$PROJECT_ID/adk-travel"
print_status "🐳 Checking/Creating Artifact Registry..."
if ! gcloud artifacts repositories describe adk-travel --location="$REGION" &>/dev/null; then
    print_status "Creating Artifact Registry repository 'adk-travel'..."
    
    if gcloud artifacts repositories create adk-travel \
        --repository-format=docker \
        --location="$REGION" \
        --description="ADK Travel agents Docker images" \
        --quiet; then
        print_success "✅ Artifact Registry repository created"
    else
        print_error "❌ Failed to create Artifact Registry repository"
    fi
else
    print_success "✅ Artifact Registry repository already exists"
fi

# Configure Docker authentication
print_status "🔐 Configuring Docker authentication..."
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

# Connect to cluster
print_status "☸️  Connecting to cluster..."
if ! gcloud container clusters describe "$CLUSTER_NAME" --region="$REGION" &>/dev/null; then
    print_error "Cluster '$CLUSTER_NAME' not found in region '$REGION'"
fi

gcloud container clusters get-credentials "$CLUSTER_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID"
print_success "Connected to cluster $CLUSTER_NAME"

# Create/Check namespace
print_status "📂 Checking namespace..."
if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
    print_status "Creating namespace '$NAMESPACE'..."
    kubectl create namespace "$NAMESPACE"
    print_success "Namespace created"
else
    print_success "Namespace already exists"
fi

# Build Docker image
print_status "🏗️  Building Docker image..."
IMAGE_TAG="$REGISTRY_URL/$IMAGE_NAME:$(date +%Y%m%d-%H%M%S)"
IMAGE_LATEST="$REGISTRY_URL/$IMAGE_NAME:latest"

print_status "Building image: $IMAGE_TAG"

# Build from root directory using the Dockerfile
if docker build -t "$IMAGE_TAG" -t "$IMAGE_LATEST" .; then
    print_success "✅ Docker image built successfully"
else
    print_error "❌ Docker build failed"
fi

# Push Docker image
print_status "📤 Pushing Docker image..."
docker push "$IMAGE_TAG"
docker push "$IMAGE_LATEST"
print_success "✅ Image pushed to registry"

# Apply Kubernetes manifests
print_status "☸️  Applying Kubernetes manifests..."

# Check if k8s directory has files
K8S_FILES=$(find k8s -name "*.yaml" -o -name "*.yml" 2>/dev/null | wc -l)
if [ "$K8S_FILES" -eq 0 ]; then
    print_error "No YAML files found in k8s/ directory"
fi

print_status "Found $K8S_FILES Kubernetes manifest files"

# Apply each manifest file, replacing placeholders
for file in k8s/*.yaml k8s/*.yml; do
    if [ -f "$file" ]; then
        print_status "Applying $(basename "$file")..."
        
        # Replace placeholders and apply
        sed -e "s|PROJECT_ID|$PROJECT_ID|g" \
            -e "s|REGION|$REGION|g" \
            -e "s|IMAGE_URL|$IMAGE_LATEST|g" \
            -e "s|REGISTRY_URL|$REGISTRY_URL|g" \
            -e "s|NAMESPACE|$NAMESPACE|g" \
            "$file" | kubectl apply -f -
    fi
done

# Check for subdirectories in k8s/
if [ -d "k8s/deployments" ] || [ -d "k8s/services" ] || [ -d "k8s/ingress" ]; then
    print_status "Applying manifests from subdirectories..."
    
    # Apply from subdirectories
    for subdir in k8s/*/; do
        if [ -d "$subdir" ]; then
            print_status "Processing directory: $(basename "$subdir")"
            
            for file in "$subdir"*.yaml "$subdir"*.yml; do
                if [ -f "$file" ]; then
                    print_status "Applying $(basename "$file")..."
                    
                    sed -e "s|PROJECT_ID|$PROJECT_ID|g" \
                        -e "s|REGION|$REGION|g" \
                        -e "s|IMAGE_URL|$IMAGE_LATEST|g" \
                        -e "s|REGISTRY_URL|$REGISTRY_URL|g" \
                        -e "s|NAMESPACE|$NAMESPACE|g" \
                        "$file" | kubectl apply -f -
                fi
            done
        fi
    done
fi

print_success "✅ Kubernetes manifests applied"

# Wait for deployments to be ready
print_status "⏳ Waiting for deployments to be ready..."
if kubectl get deployments -n "$NAMESPACE" &>/dev/null; then
    kubectl wait --for=condition=available --timeout=300s deployment --all -n "$NAMESPACE" || {
        print_warning "Some deployments may still be starting"
    }
else
    print_warning "No deployments found, checking pods instead..."
    sleep 30
fi

# Show deployment status
print_status "📊 Deployment Status:"
echo ""
echo "=== Pods ==="
kubectl get pods -n "$NAMESPACE" -o wide

echo ""
echo "=== Services ==="
kubectl get services -n "$NAMESPACE" -o wide

echo ""
echo "=== Deployments ==="
kubectl get deployments -n "$NAMESPACE" 2>/dev/null || echo "No deployments found"

# Check for external IPs
print_status "🌐 Checking for external access..."
EXTERNAL_IP=""
LOAD_BALANCER_SERVICE=""

# Look for LoadBalancer services
LB_SERVICES=$(kubectl get services -n "$NAMESPACE" -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].metadata.name}' 2>/dev/null || echo "")
if [ ! -z "$LB_SERVICES" ]; then
    for service in $LB_SERVICES; do
        IP=$(kubectl get service "$service" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        if [ ! -z "$IP" ]; then
            EXTERNAL_IP="$IP"
            LOAD_BALANCER_SERVICE="$service"
            break
        fi
    done
fi

# Show access information
echo ""
if [ ! -z "$EXTERNAL_IP" ]; then
    print_success "🎉 External IP available: $EXTERNAL_IP"
    echo ""
    echo "🧪 Test Commands:"
    echo "curl http://$EXTERNAL_IP/health"
    echo "curl http://$EXTERNAL_IP/"
else
    print_status "🔄 No external IP available yet. Use port-forward:"
    echo ""
    
    # Try to find the main service for port-forward
    MAIN_SERVICE=$(kubectl get services -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ ! -z "$MAIN_SERVICE" ]; then
        echo "🧪 Port-forward command:"
        echo "kubectl port-forward service/$MAIN_SERVICE 8080:80 -n $NAMESPACE"
        echo ""
        echo "🧪 Test Commands:"
        echo "curl http://localhost:8080/health"
        echo "curl http://localhost:8080/"
    fi
fi

# Check for any failed pods
FAILED_PODS=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
if [ "$FAILED_PODS" -gt 0 ]; then
    print_warning "⚠️  Some pods are not running:"
    kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running
    echo ""
    print_status "Recent events:"
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -10
fi

# Save deployment information
cat > current-deployment-info.txt << EOF
ADK Travel - Current Structure Deployment
========================================
Timestamp: $(date)
Project: $PROJECT_ID
Region: $REGION  
Cluster: $CLUSTER_NAME
Namespace: $NAMESPACE

Docker Image: $IMAGE_TAG
Registry URL: $REGISTRY_URL
$(if [ ! -z "$EXTERNAL_IP" ]; then
echo "External IP: $EXTERNAL_IP (service: $LOAD_BALANCER_SERVICE)"
echo ""
echo "Test Commands:"
echo "curl http://$EXTERNAL_IP/health"
echo "curl http://$EXTERNAL_IP/"
else
echo "Port-forward Command:"
echo "kubectl port-forward service/$MAIN_SERVICE 8080:80 -n $NAMESPACE"
echo ""
echo "Test Commands:"
echo "curl http://localhost:8080/health"  
echo "curl http://localhost:8080/"
fi)

Management Commands:
kubectl get all -n $NAMESPACE
kubectl logs -f deployment/$(kubectl get deployments -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo 'DEPLOYMENT_NAME') -n $NAMESPACE
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'

Structure Used:
✅ Dockerfile in root
✅ Source code in src/
✅ Kubernetes manifests in k8s/
EOF

print_success "✅ Deployment completed!"
print_status "📄 Deployment info saved to: current-deployment-info.txt"

# Final status
RUNNING_PODS=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
TOTAL_PODS=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)

echo ""
if [ "$TOTAL_PODS" -gt 0 ]; then
    print_status "Final Status: $RUNNING_PODS/$TOTAL_PODS pods running"
    
    if [ "$RUNNING_PODS" -eq "$TOTAL_PODS" ]; then
        print_success "🎉 All applications deployed successfully!"
    else
        print_warning "⚠️  Some applications may still be starting"
    fi
else
    print_warning "⚠️  No pods found - check Kubernetes manifests"
fi

echo ""
print_success "🚀 ADK Travel deployment complete!"
echo ""
print_status "🔍 To troubleshoot, check:"
echo "kubectl get all -n $NAMESPACE"
echo "kubectl describe pods -n $NAMESPACE"
echo "kubectl logs -l app=adk-travel -n $NAMESPACE"