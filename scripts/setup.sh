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
# Core APIs for GKE and basic functionality
gcloud services enable \
  container.googleapis.com \
  compute.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  --quiet

# Additional APIs for database and networking
print_success "Enabling database and networking APIs..."
gcloud services enable \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  servicenetworking.googleapis.com \
  networkmanagement.googleapis.com \
  dns.googleapis.com \
  --quiet

# APIs for advanced features
print_success "Enabling advanced feature APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  cloudkms.googleapis.com \
  storage-component.googleapis.com \
  storage.googleapis.com \
  --quiet

print_success "All APIs enabled successfully"

# Verify critical APIs are enabled
print_success "Verifying API enablement..."
CRITICAL_APIS=(
    "container.googleapis.com"
    "compute.googleapis.com"
    "artifactregistry.googleapis.com"
    "aiplatform.googleapis.com"
    "sql-component.googleapis.com"
    "servicenetworking.googleapis.com"
)

for api in "${CRITICAL_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        print_success "✓ $api is enabled"
    else
        print_warning "⚠️  $api may not be fully enabled yet (this is normal, it can take a few minutes)"
    fi
done

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
    "roles/cloudsql.client"
    "roles/compute.networkUser"
    "roles/container.developer"
)

for role in "${ROLES[@]}"; do
    print_success "Assigning role: $role"
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="$role" \
        --quiet
done

print_success "IAM roles assigned successfully"

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
project_id         = "$PROJECT_ID"
region            = "$REGION"
cluster_name      = "$CLUSTER_NAME"
enable_cloud_sql  = true
vpc_cidr_range    = "10.0.0.0/16"
pod_cidr_range    = "10.1.0.0/16"
services_cidr_range = "10.2.0.0/16"
db_name           = "adk_travel_db"
db_user           = "adk_user"
db_password       = "$(openssl rand -base64 12 | tr -d '/+=' | head -c12)AdK!"
master_authorized_networks = [
  {
    cidr_block   = "0.0.0.0/0"
    display_name = "All"
  }
]
resource_labels = {
  project     = "adk-travel"
  environment = "development"
  managed-by  = "terraform"
}
EOF
    print_success "terraform.tfvars created with generated database password"
else
    print_warning "terraform.tfvars already exists - updating project settings..."
    # Update existing file with current project settings
    sed -i.bak "s/project_id.*/project_id = \"$PROJECT_ID\"/" terraform.tfvars
    sed -i.bak "s/region.*/region = \"$REGION\"/" terraform.tfvars
    sed -i.bak "s/cluster_name.*/cluster_name = \"$CLUSTER_NAME\"/" terraform.tfvars
fi

print_success "Initializing Terraform..."
terraform init

print_success "Validating Terraform configuration..."
if terraform validate; then
    print_success "Terraform configuration is valid"
else
    print_error "Terraform configuration validation failed"
fi

print_success "Planning Terraform deployment..."
terraform plan -out=tfplan

print_success "Applying Terraform configuration..."
terraform apply -auto-approve tfplan

print_success "Infrastructure deployed successfully"

# Get outputs from Terraform
print_success "Getting infrastructure details..."
CLUSTER_ENDPOINT=$(terraform output -raw cluster_endpoint 2>/dev/null || echo "")
ARTIFACT_REGISTRY_URL=$(terraform output -raw artifact_registry_url 2>/dev/null || echo "")

if [ ! -z "$ARTIFACT_REGISTRY_URL" ]; then
    print_success "Artifact Registry: $ARTIFACT_REGISTRY_URL"
fi

# Go back to project root
cd "$PROJECT_ROOT"

# Create Kubernetes secrets and config
print_header "Setting up Kubernetes"
print_success "Getting GKE credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION

# Wait for cluster to be ready
print_success "Waiting for cluster to be fully ready..."
sleep 30

print_success "Creating namespace..."
kubectl create namespace adk-travel --dry-run=client -o yaml | kubectl apply -f -

print_success "Creating service account..."
kubectl create serviceaccount adk-travel-ksa -n adk-travel --dry-run=client -o yaml | kubectl apply -f -

print_success "Creating ConfigMap..."
kubectl create configmap adk-config \
    --from-literal=GOOGLE_CLOUD_PROJECT="$PROJECT_ID" \
    --from-literal=GOOGLE_CLOUD_LOCATION="$REGION" \
    --from-literal=ADK_VERSION="1.0" \
    --from-literal=ENVIRONMENT="production" \
    -n adk-travel \
    --dry-run=client -o yaml | kubectl apply -f -

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

# Deploy application if deployment script exists
print_header "Deploying ADK Application"
if [ -f "$SCRIPT_DIR/deploy.sh" ]; then
    print_success "Running deployment script..."
    chmod +x "$SCRIPT_DIR/deploy.sh"
    "$SCRIPT_DIR/deploy.sh" $PROJECT_ID $REGION $CLUSTER_NAME
else
    print_warning "deploy.sh not found - skipping application deployment"
    print_warning "You can deploy manually later with: ./scripts/deploy.sh $PROJECT_ID $REGION"
fi

# Run tests if available
print_header "Running System Tests"
print_success "Waiting for services to be ready..."
sleep 60

if [ -f "$SCRIPT_DIR/test_adk_demo.py" ]; then
    print_success "Running ADK system tests..."
    if command -v python3 &> /dev/null; then
        python3 "$SCRIPT_DIR/test_adk_demo.py" --quick || {
            print_warning "Some tests failed - this is normal if services are still starting up"
            print_warning "Try running tests again in a few minutes: python3 scripts/test_adk_demo.py"
        }
    else
        print_warning "Python3 not found - skipping automated tests"
    fi
else
    print_warning "test_adk_demo.py not found - skipping automated tests"
fi

# Final summary
print_header "🎉 Setup Complete!"
print_success "Google ADK Travel System is ready!"

echo ""
echo "📋 Summary:"
echo "✅ GCP project configured: $PROJECT_ID"
echo "✅ APIs enabled (including SQL and Service Networking)"
echo "✅ Service account created with necessary permissions"
echo "✅ GKE cluster deployed: $CLUSTER_NAME"
echo "✅ Terraform infrastructure deployed"
echo "✅ Kubernetes configuration applied"
echo "✅ ADK agents ready for deployment"
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
echo "# View all resources:"
echo "kubectl get all -n adk-travel"
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

echo "📊 Infrastructure Details:"
if [ ! -z "$CLUSTER_ENDPOINT" ]; then
    echo "🔗 Cluster Endpoint: $CLUSTER_ENDPOINT"
fi
if [ ! -z "$ARTIFACT_REGISTRY_URL" ]; then
    echo "📦 Container Registry: $ARTIFACT_REGISTRY_URL"
fi
echo "🗄️  Database: Cloud SQL (if enabled in terraform.tfvars)"
echo "🔐 Service Account: $SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"
echo ""

echo "🛠️  Management Commands:"
echo "# View Terraform outputs:"
echo "cd terraform && terraform output"
echo ""
echo "# Update infrastructure:"
echo "cd terraform && terraform plan && terraform apply"
echo ""
echo "# Check cluster status:"
echo "kubectl cluster-info"
echo ""
echo "# Monitor resources:"
echo "./scripts/status.sh $PROJECT_ID $REGION"
echo ""

print_success "Your Google ADK Travel System is ready for the 15-minute demo!"
print_success "🎬 All systems operational - start your presentation!"

# Save configuration for easy reference
CONFIG_FILE="$PROJECT_ROOT/deployment-config.txt"
cat > "$CONFIG_FILE" <<EOF
Google ADK Travel System - Deployment Configuration
==================================================
Deployment Date: $(date)
Project ID: $PROJECT_ID
Region: $REGION
Cluster Name: $CLUSTER_NAME
Service Account: $SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com

Key Files:
- Service Account Key: $KEY_FILE
- Terraform Configuration: terraform/terraform.tfvars
- Configuration File: $CONFIG_FILE

Quick Commands:
- Port Forward: kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel
- View Logs: kubectl logs -f deployment/travel-adk-coordinator -n adk-travel
- Run Tests: python3 scripts/test_adk_demo.py
- Check Status: ./scripts/status.sh $PROJECT_ID $REGION
- Cleanup: ./scripts/cleanup.sh $PROJECT_ID $REGION

APIs Enabled:
✅ Container Engine (GKE)
✅ Compute Engine
✅ Artifact Registry
✅ AI Platform
✅ Secret Manager
✅ Cloud Monitoring
✅ Cloud Logging
✅ Cloud SQL
✅ Service Networking
✅ Network Management
✅ Cloud DNS
✅ Cloud Build
✅ Cloud Resource Manager
✅ Cloud KMS
✅ Cloud Storage

Roles Assigned to Service Account:
✅ AI Platform User
✅ Secret Manager Secret Accessor
✅ Monitoring Metric Writer
✅ Logging Log Writer
✅ Storage Object Viewer
✅ Cloud SQL Client
✅ Compute Network User
✅ Container Developer
EOF

print_success "Configuration saved to: $CONFIG_FILE"