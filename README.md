
# ====================================
# Demo Setup Commands
# ====================================
"""
# Complete Google ADK Demo Setup

# 1. Prerequisites
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required APIs
gcloud services enable \
  container.googleapis.com \
  compute.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com

# 3. Create service account for ADK
gcloud iam service-accounts create adk-travel-sa \
  --display-name="ADK Travel Service Account"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:adk-travel-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud iam service-accounts keys create adk-key.json \
  --iam-account=adk-travel-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com

# 4. Create Kubernetes secret with ADK credentials
kubectl create namespace adk-travel
kubectl create secret generic adk-credentials \
  --from-file=service-account-key=adk-key.json \
  -n adk-travel

# 5. Update ConfigMap with your project ID
kubectl create configmap adk-config \
  --from-literal=GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID \
  --from-literal=GOOGLE_CLOUD_LOCATION=us-central1 \
  --from-literal=ADK_VERSION=1.0 \
  -n adk-travel

# 6. Deploy with corrected script
./scripts/deploy.sh YOUR_PROJECT_ID

# 7. Test ADK system
python3 scripts/test_adk_demo.py

# 8. For demo presentation
kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel

# 9. Demo API calls
# Chat with individual agent
"""
curl -X POST http://localhost:8080/agent/flight/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need flights to Tokyo next month"}'
"""

# Multi-agent coordination  
"""
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Plan a complete Tokyo trip with flights, hotels, and cultural activities"}'
"""

# Comprehensive planning
"""
curl -X POST http://localhost:8080/plan \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Tokyo",
    "days": 4, 
    "budget": 3000,
    "interests": ["cultural", "food", "technology"],
    "travel_style": "mid-range"
  }'
"""

# Demo Commands for Presentation

# 1. Quick Setup (run this before demo)
./scripts/quick_setup.sh your-project-id

# 2. Check cluster status
kubectl get nodes
kubectl get pods -n adk-travel -o wide
kubectl get services -n adk-travel

# 3. Scale agents (show auto-scaling)
kubectl scale deployment flight-agent --replicas=5 -n adk-travel
watch kubectl get pods -n adk-travel

# 4. Check metrics
kubectl port-forward service/travel-coordinator 8090:8090 -n adk-travel
# Visit http://localhost:8090/metrics

# 5. Test load balancing
for i in {1..10}; do curl -s http://LOAD_BALANCER_IP/health | jq .service; done

# 6. View logs (great for demo)
kubectl logs -f deployment/travel-coordinator -n adk-travel --tail=20

# 7. Monitor with kubectl top
kubectl top pods -n adk-travel
kubectl top nodes

# 8. Test auto-scaling with load
kubectl run -i --tty load-generator --rm --image=busybox --restart=Never -- /bin/sh
# Inside the pod: while true; do wget -q -O- http://travel-coordinator.adk-travel.svc.cluster.local/health; done

# 9. Show HPA in action
kubectl get hpa -n adk-travel -w

# 10. Network policies (security demo)
kubectl get networkpolicies -n adk-travel

# 11. Demo API calls
# Simple health check
curl -X GET http://localhost:8080/health | jq

# Individual agent test
curl -X POST http://localhost:8080/agent/flight \
  -H "Content-Type: application/json" \
  -d '{"query": "flights to Tokyo", "context": {"destination": "Tokyo"}}' | jq

# Full trip planning
curl -X POST http://localhost:8080/plan \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Plan an amazing 3-day trip to Tokyo",
    "destination": "Tokyo", 
    "days": 3, 
    "budget": 2500
  }' | jq

# 12. Terraform commands
"""
cd terraform
terraform plan
terraform apply -auto-approve
terraform show
terraform destroy -auto-approve
"""