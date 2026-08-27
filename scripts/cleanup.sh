#!/bin/bash
set -e

# Google ADK Travel System - Cleanup Script
# Tears down everything created by scripts/setup.sh: Kubernetes resources,
# the Terraform-managed GKE cluster/VPC, and the IAM service account/bindings.
#
# Referenced from README.md and from setup.sh's final summary - kept here so
# a demo/lab run doesn't leave a GKE cluster (and its nodes) billing forever.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ID=${1:-""}
REGION=${2:-"us-central1"}
CLUSTER_NAME=${3:-"adk-travel-cluster"}
SERVICE_ACCOUNT_NAME="adk-travel-sa"
NAMESPACE="adk-travel"

print_header() {
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================${NC}"
}
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; exit 1; }

if [ -z "$PROJECT_ID" ]; then
    print_error "Usage: $0 <PROJECT_ID> [REGION] [CLUSTER_NAME]"
fi

print_header "Google ADK Travel System - Cleanup"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Cluster: $CLUSTER_NAME"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

gcloud config set project "$PROJECT_ID" --quiet

# Delete Kubernetes resources first (namespace teardown also drops the LoadBalancer,
# avoiding an orphaned GCP forwarding rule/external IP left behind after the cluster
# is gone).
print_header "Deleting Kubernetes resources"
if gcloud container clusters describe "$CLUSTER_NAME" --region "$REGION" &>/dev/null; then
    gcloud container clusters get-credentials "$CLUSTER_NAME" --region "$REGION" --quiet || true
    if kubectl get namespace "$NAMESPACE" &>/dev/null; then
        print_success "Deleting namespace $NAMESPACE (this also removes the LoadBalancer)..."
        kubectl delete namespace "$NAMESPACE" --wait=true --timeout=180s || \
            print_warning "Namespace deletion timed out or failed - continuing anyway"
    else
        print_warning "Namespace $NAMESPACE not found - skipping"
    fi
else
    print_warning "Cluster $CLUSTER_NAME not found in $REGION - skipping Kubernetes cleanup"
fi

# Destroy Terraform-managed infrastructure (GKE cluster, VPC, subnets, firewall rules)
print_header "Destroying Terraform infrastructure"
cd "$PROJECT_ROOT/terraform"
if [ -f "terraform.tfvars" ]; then
    terraform init -input=false
    terraform destroy -auto-approve \
        -var="project_id=$PROJECT_ID" \
        -var="region=$REGION" \
        -var="cluster_name=$CLUSTER_NAME" || \
        print_warning "terraform destroy reported errors - check remaining resources manually in the GCP Console"
else
    print_warning "terraform.tfvars not found - skipping Terraform destroy (nothing to do or state is elsewhere)"
fi
cd "$PROJECT_ROOT"

# Remove IAM bindings and the service account created directly by setup.sh
print_header "Removing IAM service account"
if gcloud iam service-accounts describe "$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" &>/dev/null; then
    print_success "Deleting service account $SERVICE_ACCOUNT_NAME..."
    gcloud iam service-accounts delete "$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" --quiet || \
        print_warning "Could not delete service account - it may still have bindings, check manually"
else
    print_warning "Service account $SERVICE_ACCOUNT_NAME not found - skipping"
fi

print_header "🧹 Cleanup Complete"
print_success "Kubernetes namespace, GKE cluster/VPC, and service account removed (where they existed)."
print_warning "Artifact Registry images and any Cloud SQL instance are NOT deleted by this script -"
print_warning "remove them manually if you created them, to avoid ongoing storage/DB charges:"
echo "  gcloud artifacts repositories delete adk-travel --location=$REGION --quiet"
echo "  gcloud sql instances list   # then: gcloud sql instances delete <name> --quiet"
