#!/bin/bash
set -e

# Google ADK Travel System - Status Script
# Quick snapshot of the GCP + Kubernetes state, referenced from setup.sh's summary.

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================${NC}"
}
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

PROJECT_ID=${1:-""}
REGION=${2:-"us-central1"}
CLUSTER_NAME=${3:-"adk-travel-cluster"}
NAMESPACE="adk-travel"

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 <PROJECT_ID> [REGION] [CLUSTER_NAME]"
    exit 1
fi

print_header "GCP Project"
gcloud config set project "$PROJECT_ID" --quiet
echo "Project: $PROJECT_ID | Region: $REGION | Cluster: $CLUSTER_NAME"

print_header "GKE Cluster"
if gcloud container clusters describe "$CLUSTER_NAME" --region "$REGION" \
    --format="table(name,status,currentNodeCount,currentMasterVersion)" 2>/dev/null; then
    print_success "Cluster reachable"
else
    print_error "Cluster $CLUSTER_NAME not found in $REGION"
    exit 1
fi

print_header "Kubernetes Resources ($NAMESPACE)"
gcloud container clusters get-credentials "$CLUSTER_NAME" --region "$REGION" --quiet >/dev/null 2>&1

if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
    print_warning "Namespace $NAMESPACE does not exist yet - nothing deployed"
    exit 0
fi

echo ""
echo "--- Pods ---"
kubectl get pods -n "$NAMESPACE" -o wide

echo ""
echo "--- Services ---"
kubectl get services -n "$NAMESPACE" -o wide

echo ""
echo "--- Deployments ---"
kubectl get deployments -n "$NAMESPACE"

NOT_READY=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | grep -v "Running\|Completed" | wc -l | tr -d ' ')
if [ "$NOT_READY" != "0" ]; then
    print_warning "$NOT_READY pod(s) not in a healthy state:"
    kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running
    echo ""
    echo "--- Recent events ---"
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -15
else
    print_success "All pods Running"
fi

COORDINATOR_IP=$(kubectl get service travel-adk-coordinator -n "$NAMESPACE" \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
echo ""
if [ -n "$COORDINATOR_IP" ]; then
    print_success "LoadBalancer IP: http://$COORDINATOR_IP"
    echo "curl http://$COORDINATOR_IP/health"
else
    print_warning "No LoadBalancer IP yet. Use port-forward instead:"
    echo "kubectl port-forward service/travel-adk-coordinator 8080:80 -n $NAMESPACE"
fi
