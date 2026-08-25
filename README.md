# 🚀 ADK Travel Agents

A simple, scalable AI-powered travel assistant system built with:
- **[Google Agent Development Kit](https://google.github.io/adk-docs/) (`google-adk`)** for the agents themselves - three specialist agents (flight/hotel/activity) plus a coordinator that calls them as tools, served with the framework's own dev UI (`/dev-ui`) and REST API
- **Vertex AI / Gemini** as the underlying model, via GKE Workload Identity (no API keys)
- **Google Kubernetes Engine (GKE)** for container orchestration
- **Terraform** for infrastructure as code

Based on the [camilla-m/agents-k8s-google-tf](https://github.com/camilla-m/agents-k8s-google-tf) repository, simplified for easy deployment and demo purposes.

## 🎯 What This Does

- **Flight Agent**: AI-powered flight search and recommendations
- **Travel Coordinator**: Orchestrates multiple agents for complete trip planning
- **Pure AI Experience**: No database storage, just intelligent agent interactions
- **Cloud-Native**: Scalable on Google Cloud with Kubernetes

## 🚀 Quick Start

Follow these steps to deploy the system automatically:

### 1. Clone the repository and enter the directory
```bash
git clone https://github.com/camilla-m/agents-k8s-google-tf.git
cd agents-k8s-google-tf
```

### 2. Run the automated deployment script
This script initializes Terraform, provisions the GKE cluster, creates the service account, configures Workload Identity bindings, builds the Docker image, and deploys the coordinator application.
```bash
chmod +x ./scripts/setup.sh
./scripts/setup.sh YOUR_GCP_PROJECT_ID
```
*(Note: If the setup encounters any transient API enablement errors, rerun the script to resume)*

### 3. Test the agents
Start port-forwarding to the coordinator service:
```bash
kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel
```

Open the **ADK dev console** in your browser - google-adk's own UI for chatting with
the agents and watching tool calls / sub-agent delegation happen live:
```
http://localhost:8080/dev-ui/
```

Or send a chat request from the terminal instead:
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Plan a trip to Tokyo"}'
```

There's also a small standalone test page at [ui/index.html](ui/index.html) - open it
directly in a browser (no server needed) and point it at your LoadBalancer IP or
`http://localhost:8080` if you're port-forwarding.

## 🧪 Testing the Agents

### Health Check
```bash
curl http://localhost:8080/health
```

### Flight Agent
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need flights to Tokyo next month"}'
```

### Travel Coordinator
```bash
curl -X POST http://localhost:8080/plan \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Tokyo", 
    "days": 4, 
    "budget": 3000,
    "interests": ["cultural", "food"]
  }'
```

## 🔧 Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Load Balancer │────│ Travel Coordinator │────│  Flight Agent   │
│   (GKE Service) │    │   (Orchestrator)   │    │  (AI Powered)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Google AI       │
                       │ Platform (ADK)  │
                       │ Gemini Pro      │
                       └─────────────────┘
```

## 📊 Key Features

- ✅ **No Database Required** - Pure AI agent interactions
- ✅ **Scalable** - manually via `kubectl scale` (no HorizontalPodAutoscaler is defined yet - add one in k8s/ if you need automatic scaling)
- ✅ **Cloud-Native** - Built for Google Cloud Platform
- ✅ **AI-Powered** - Uses Google's latest AI models
- ✅ **Simple** - Easy to deploy and understand
- ✅ **Production-Ready** - Health checks, monitoring

## 🛠️ Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Terraform](https://terraform.io/downloads)
- [Docker](https://docs.docker.com/get-docker/)
- Google Cloud Project with billing enabled

## 📚 Commands Reference

### Deployment
```bash
./scripts/setup.sh PROJECT_ID  [REGION]        # Quick setup
./scripts/deploy.sh PROJECT_ID [REGION]        # Full deployment
```

### Testing
```bash
python3 scripts/test_adk_demo.py               # Automated tests
python3 scripts/test_adk_demo.py --quick       # Quick tests
```

### Cleanup
```bash
./scripts/cleanup.sh PROJECT_ID [REGION]       # Remove all resources
```

## 🔐 Security

- **Workload Identity** for secure GCP service authentication
- **Non-root containers** for enhanced security

## 💰 Cost Optimization

- **Preemptible nodes** in development environment
- **Horizontal Pod Autoscaling** to scale based on demand
- **Efficient resource requests** and limits

## 🚨 Troubleshooting

### Common Issues
```bash
# Authentication issues
gcloud auth login
gcloud auth application-default login

# Cluster access
gcloud container clusters get-credentials adk-travel-cluster --region=us-central1

# Pod issues
kubectl describe pod <pod-name> -n adk-travel
kubectl logs <pod-name> -n adk-travel
```

### Useful Debug Commands
```bash
kubectl get events --sort-by='.lastTimestamp' -n adk-travel
kubectl get all -n adk-travel
kubectl top pods -n adk-travel
```

## 📈 Scaling

```bash
# Scale the Travel Coordinator (which runs all agents)
kubectl scale deployment travel-adk-coordinator --replicas=3 -n adk-travel

# Monitor pods
kubectl get pods -n adk-travel
```

## 🎯 Demo Script

Perfect for presentations and demos:

```bash
# 1. Show the deployment
kubectl get all -n adk-travel

# 2. Port forward for demo
kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel &

# 3. Demo the AI agents
curl -X POST http://localhost:8080/chat -H "Content-Type: application/json" \
  -d '{"message": "Plan a 3-day cultural trip to Tokyo with a $2000 budget"}'

# 4. Show real-time logs
kubectl logs -f deployment/travel-adk-coordinator -n adk-travel --tail=10
```

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

**🚀 Ready to deploy AI-powered travel agents on Google Cloud? Start with:**
```bash
chmod +x ./scripts/setup.sh
./scripts/setup.sh your-project-id
```