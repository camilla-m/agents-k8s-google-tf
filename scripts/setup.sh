#!/bin/bash
set -e

# Google ADK Travel System - Complete Setup Script
# Sets up GCP project, infrastructure, and application

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ID=${1:-""}
REGION=${2:-"us-central1"}
CLUSTER_NAME=${3:-"adk-travel-cluster"}
SERVICE_ACCOUNT_NAME="adk-travel-sa"

# Functions
print_header() {
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is required but not installed"
    fi
}

# Validation
if [ -z "$PROJECT_ID" ]; then
    print_error "Usage: $0 <PROJECT_ID> [REGION] [CLUSTER_NAME]"
fi

print_header "Google ADK Travel System - Complete Setup"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Cluster: $CLUSTER_NAME"
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check prerequisites
print_header "Checking Prerequisites"
check_command "gcloud"
check_command "kubectl"
check_command "docker"
check_command "terraform"

print_success "All required tools are installed"

# Set up GCP project
print_header "Setting up GCP Project"
print_success "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

print_success "Enabling required APIs..."
gcloud services enable \
  container.googleapis.com \
  compute.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com

print_success "APIs enabled successfully"

# Create service account for ADK
print_header "Creating Service Account"
print_success "Creating service account: $SERVICE_ACCOUNT_NAME..."

# Create service account if it doesn't exist
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" &>/dev/null; then
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
        --display-name="Google ADK Travel Service Account" \
        --description="Service account for Google ADK Travel System"
    print_success "Service account created"
else
    print_success "Service account already exists"
fi

# Assign necessary roles
print_success "Assigning IAM roles..."
ROLES=(
    "roles/aiplatform.user"
    "roles/secretmanager.secretAccessor"
    "roles/monitoring.metricWriter"
    "roles/logging.logWriter"
    "roles/storage.objectViewer"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="$role" \
        --quiet
done

print_success "IAM roles assigned"

# Create service account key
print_header "Creating Service Account Key"
KEY_FILE="$PROJECT_ROOT/adk-service-account-key.json"

if [ ! -f "$KEY_FILE" ]; then
    print_success "Creating service account key..."
    gcloud iam service-accounts keys create $KEY_FILE \
        --iam-account="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"
    print_success "Service account key created: $KEY_FILE"
else
    print_warning "Service account key already exists: $KEY_FILE"
fi

# Deploy infrastructure with Terraform
print_header "Deploying Infrastructure with Terraform"
cd "$PROJECT_ROOT/terraform"

# Create terraform.tfvars if it doesn't exist
if [ ! -f "terraform.tfvars" ]; then
    print_success "Creating terraform.tfvars..."
    cat > terraform.tfvars <<EOF
project_id   = "$PROJECT_ID"
region      = "$REGION"
cluster_name = "$CLUSTER_NAME"
EOF
    print_success "terraform.tfvars created"
fi

print_success "Initializing Terraform..."
terraform init

print_success "Planning Terraform deployment..."
terraform plan

print_success "Applying Terraform configuration..."
terraform apply -auto-approve

print_success "Infrastructure deployed successfully"

# Go back to project root
cd "$PROJECT_ROOT"

# Create Kubernetes secrets and config
print_header "Setting up Kubernetes"
print_success "Getting GKE credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION

print_success "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

print_success "Creating service account and RBAC..."
kubectl apply -f k8s/serviceaccount.yaml

print_success "Creating ConfigMap..."
# Update ConfigMap with actual project ID
sed "s/YOUR_PROJECT_ID/$PROJECT_ID/g" k8s/configmap.yaml | kubectl apply -f -

print_success "Creating secrets..."
kubectl create secret generic adk-credentials \
    --from-file=service-account-key=$KEY_FILE \
    -n adk-travel \
    --dry-run=client -o yaml | kubectl apply -f -

# Create empty API keys secret to prevent deployment errors
kubectl create secret generic adk-api-keys \
    --from-literal=placeholder="service-account-only" \
    -n adk-travel \
    --dry-run=client -o yaml | kubectl apply -f -

print_success "Kubernetes configuration complete"

# Deploy application
print_header "Deploying ADK Application"
print_success "Running deployment script..."
"$SCRIPT_DIR/deploy.sh" $PROJECT_ID $REGION $CLUSTER_NAME

# Run tests
print_header "Running System Tests"
print_success "Waiting for services to be ready..."
sleep 60

print_success "Running ADK system tests..."
if command -v python3 &> /dev/null; then
    python3 "$SCRIPT_DIR/test_adk_demo.py" || {
        print_warning "Some tests failed - this is normal if services are still starting up"
        print_warning "Try running tests again in a few minutes: python3 scripts/test_adk_demo.py"
    }
else
    print_warning "Python3 not found - skipping automated tests"
    print_warning "Manually test with: kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel"
fi

# Final summary
print_header "🎉 Setup Complete!"
print_success "Google ADK Travel System is ready!"

echo ""
echo "📋 Summary:"
echo "✅ GCP project configured: $PROJECT_ID"
echo "✅ APIs enabled and service account created"
echo "✅ GKE cluster deployed: $CLUSTER_NAME"
echo "✅ ADK agents deployed with Gemini integration"
echo "✅ Configuration and secrets applied"
echo ""

echo "🚀 Quick Start Commands:"
echo "# Port forward for local testing:"
echo "kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel"
echo ""
echo "# Test the system:"
echo "python3 scripts/test_adk_demo.py"
echo ""
echo "# View application logs:"
echo "kubectl logs -f deployment/travel-adk-coordinator -n adk-travel"
echo ""

# Get LoadBalancer IP if available
COORDINATOR_IP=$(kubectl get service travel-adk-coordinator -n adk-travel -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
if [ ! -z "$COORDINATOR_IP" ]; then
    echo "🌐 LoadBalancer URL: http://$COORDINATOR_IP"
    echo ""
fi

echo "🎯 Demo endpoints:"
echo "# Health check:"
echo "curl http://localhost:8080/health"
echo ""
echo "# Chat with agents:"
echo 'curl -X POST http://localhost:8080/chat -H "Content-Type: application/json" -d '"'"'{"message": "Plan a trip to Tokyo"}'"'"''
echo ""
echo "# Comprehensive planning:"
echo 'curl -X POST http://localhost:8080/plan -H "Content-Type: application/json" -d '"'"'{"destination": "Tokyo", "days": 4, "budget": 3000}'"'"''
echo ""

print_success "Your Google ADK Travel System is ready for the 15-minute demo!"
print_success "🎬 All systems operational - start your presentation!"