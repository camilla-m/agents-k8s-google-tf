#!/bin/bash

# Deploy script for ADK Travel Agents on GKE with Terraform
# Usage: ./scripts/deploy.sh PROJECT_ID [REGION]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_REGION="us-central1"
DEFAULT_CLUSTER_NAME="adk-travel-cluster"
NAMESPACE="adk-travel"
SERVICE_ACCOUNT_NAME="adk-travel-sa"

# Function to print colored output
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
}

# Function to check if command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# Function to show usage
usage() {
    echo "Usage: $0 PROJECT_ID [REGION]"
    echo ""
    echo "Arguments:"
    echo "  PROJECT_ID    Google Cloud Project ID (required)"
    echo "  REGION        Google Cloud Region (optional, default: us-central1)"
    echo ""
    echo "Examples:"
    echo "  $0 my-gcp-project"
    echo "  $0 my-gcp-project us-west1"
    exit 1
}

# Validate arguments
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    usage
fi

PROJECT_ID="$1"
REGION="${2:-$DEFAULT_REGION}"

print_status "Starting deployment for project: ${PROJECT_ID} in region: ${REGION}"

# Validate project ID format
if [[ ! $PROJECT_ID =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]]; then
    print_error "Invalid project ID format. Project ID must be 6-30 characters, start with lowercase letter, and contain only lowercase letters, digits, and hyphens."
    exit 1
fi

# Check required tools
print_status "Checking required tools..."
check_command "gcloud"
check_command "kubectl"
check_command "terraform"
check_command "docker"

# Set gcloud project
print_status "Setting up gcloud configuration..."
gcloud config set project "${PROJECT_ID}"

# Enable required APIs
print_status "Enabling required Google Cloud APIs..."
gcloud services enable \
    container.googleapis.com \
    compute.googleapis.com \
    artifactregistry.googleapis.com \
    aiplatform.googleapis.com \
    --quiet

# Create service account if it doesn't exist
print_status "Creating service account..."
if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" &>/dev/null; then
    gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
        --display-name="ADK Travel Service Account" \
        --description="Service account for ADK Travel agents"
else
    print_warning "Service account ${SERVICE_ACCOUNT_NAME} already exists, skipping creation."
fi

# Assign IAM roles to service account
print_status "Assigning IAM roles..."
ROLES=(
    "roles/aiplatform.user"
    "roles/storage.objectViewer"
    "roles/logging.logWriter"
    "roles/monitoring.metricWriter"
    "roles/container.developer"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="${role}" \
        --quiet
done

# Create service account key if it doesn't exist
KEY_FILE="adk-key.json"
if [ ! -f "${KEY_FILE}" ]; then
    print_status "Creating service account key..."
    gcloud iam service-accounts keys create "${KEY_FILE}" \
        --iam-account="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
else
    print_warning "Service account key file already exists, skipping creation."
fi

# Initialize and apply Terraform
print_status "Initializing Terraform..."
cd terraform

# Create terraform.tfvars if it doesn't exist
TFVARS_FILE="terraform.tfvars"
if [ ! -f "${TFVARS_FILE}" ]; then
    print_status "Creating terraform.tfvars file..."
    cat > "${TFVARS_FILE}" << EOF
project_id = "${PROJECT_ID}"
region     = "${REGION}"
cluster_name = "${DEFAULT_CLUSTER_NAME}"
namespace = "${NAMESPACE}"
EOF
else
    print_warning "terraform.tfvars already exists, please verify its contents."
fi

# Initialize Terraform
terraform init

# Validate Terraform configuration
print_status "Validating Terraform configuration..."
terraform validate

# Plan Terraform deployment
print_status "Planning Terraform deployment..."
terraform plan -var="project_id=${PROJECT_ID}" -var="region=${REGION}"

# Apply Terraform configuration
print_status "Applying Terraform configuration..."
terraform apply -auto-approve -var="project_id=${PROJECT_ID}" -var="region=${REGION}"

# Get cluster credentials
print_status "Getting GKE cluster credentials..."
gcloud container clusters get-credentials "${DEFAULT_CLUSTER_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}"

cd ..

# Create namespace if it doesn't exist
print_status "Creating Kubernetes namespace..."
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# Create Kubernetes secrets
print_status "Creating Kubernetes secrets..."
kubectl create secret generic adk-credentials \
    --from-file=service-account-key="${KEY_FILE}" \
    -n "${NAMESPACE}" \
    --dry-run=client -o yaml | kubectl apply -f -

# Create ConfigMap
print_status "Creating Kubernetes ConfigMap..."
kubectl create configmap adk-config \
    --from-literal=GOOGLE_CLOUD_PROJECT="${PROJECT_ID}" \
    --from-literal=GOOGLE_CLOUD_LOCATION="${REGION}" \
    --from-literal=ADK_VERSION="1.0" \
    -n "${NAMESPACE}" \
    --dry-run=client -o yaml | kubectl apply -f -

# Build and push Docker images (if Dockerfile exists)
if [ -d "docker" ]; then
    print_status "Building and pushing Docker images..."
    
    # Create Artifact Registry repository if it doesn't exist
    REPO_NAME="adk-travel"
    if ! gcloud artifacts repositories describe "${REPO_NAME}" \
        --location="${REGION}" \
        --format="value(name)" &>/dev/null; then
        
        print_status "Creating Artifact Registry repository..."
        gcloud artifacts repositories create "${REPO_NAME}" \
            --repository-format=docker \
            --location="${REGION}" \
            --description="ADK Travel agents Docker images"
    fi
    
    # Configure Docker for Artifact Registry
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
    
    # Build and push each service
    for dockerfile in docker/*/Dockerfile; do
        if [ -f "$dockerfile" ]; then
            service_dir=$(dirname "$dockerfile")
            service_name=$(basename "$service_dir")
            image_tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${service_name}:latest"
            
            print_status "Building ${service_name} image..."
            docker build -t "${image_tag}" "${service_dir}"
            
            print_status "Pushing ${service_name} image..."
            docker push "${image_tag}"
        fi
    done
fi

# Apply Kubernetes manifests
if [ -d "k8s" ]; then
    print_status "Applying Kubernetes manifests..."
    
    # Replace placeholders in manifests
    find k8s -name "*.yaml" -type f -exec sed -i.bak \
        -e "s/YOUR_PROJECT_ID/${PROJECT_ID}/g" \
        -e "s/YOUR_REGION/${REGION}/g" \
        -e "s/YOUR_NAMESPACE/${NAMESPACE}/g" {} \;
    
    # Apply manifests
    kubectl apply -f k8s/ -n "${NAMESPACE}"
    
    # Restore original files
    find k8s -name "*.yaml.bak" -type f -exec sh -c 'mv "$1" "${1%.bak}"' _ {} \;
else
    print_warning "No k8s directory found, skipping Kubernetes manifest deployment."
fi

# Wait for deployments to be ready
print_status "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=600s deployment --all -n "${NAMESPACE}"

# Get service information
print_status "Getting service information..."
kubectl get services -n "${NAMESPACE}"

# Check pod status
print_status "Checking pod status..."
kubectl get pods -n "${NAMESPACE}" -o wide

# Get ingress information (if exists)
if kubectl get ingress -n "${NAMESPACE}" &>/dev/null; then
    print_status "Getting ingress information..."
    kubectl get ingress -n "${NAMESPACE}"
fi

# Output useful information
print_success "Deployment completed successfully!"
echo ""
echo "=== Deployment Information ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Cluster Name: ${DEFAULT_CLUSTER_NAME}"
echo "Namespace: ${NAMESPACE}"
echo ""
echo "=== Useful Commands ==="
echo "Get pods: kubectl get pods -n ${NAMESPACE}"
echo "Get services: kubectl get services -n ${NAMESPACE}"
echo "View logs: kubectl logs -f deployment/<deployment-name> -n ${NAMESPACE}"
echo "Port forward: kubectl port-forward service/<service-name> 8080:80 -n ${NAMESPACE}"
echo ""
echo "=== Testing Commands ==="
echo "Health check: curl -X GET http://localhost:8080/health"
echo "Flight agent: curl -X POST http://localhost:8080/agent/flight/chat -H 'Content-Type: application/json' -d '{\"message\": \"I need flights to Tokyo next month\"}'"
echo "Travel planner: curl -X POST http://localhost:8080/chat -H 'Content-Type: application/json' -d '{\"message\": \"Plan a complete Tokyo trip with flights, hotels, and cultural activities\"}'"

# Save deployment info to file
INFO_FILE="deployment-info.txt"
cat > "${INFO_FILE}" << EOF
ADK Travel Agents Deployment Information
========================================

Deployment Date: $(date)
Project ID: ${PROJECT_ID}
Region: ${REGION}
Cluster Name: ${DEFAULT_CLUSTER_NAME}
Namespace: ${NAMESPACE}

Service Account: ${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com

Useful Commands:
- Get cluster credentials: gcloud container clusters get-credentials ${DEFAULT_CLUSTER_NAME} --region=${REGION} --project=${PROJECT_ID}
- View pods: kubectl get pods -n ${NAMESPACE}
- View services: kubectl get services -n ${NAMESPACE}
- Port forward: kubectl port-forward service/travel-adk-coordinator 8080:80 -n ${NAMESPACE}

Testing Endpoints (after port-forward):
- Health: curl http://localhost:8080/health
- Flight Agent: curl -X POST http://localhost:8080/agent/flight/chat -H 'Content-Type: application/json' -d '{"message": "Find flights to Tokyo"}'
- Travel Coordinator: curl -X POST http://localhost:8080/chat -H 'Content-Type: application/json' -d '{"message": "Plan a trip to Tokyo"}'
EOF

print_success "Deployment information saved to ${INFO_FILE}"

# Cleanup temporary files
if [ -f "${KEY_FILE}.bak" ]; then
    rm "${KEY_FILE}.bak"
fi

print_success "All done! Your ADK Travel agents are now deployed and running on GKE."