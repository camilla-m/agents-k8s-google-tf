# Demo Commands for Presentation

# 1. Check cluster status
kubectl get nodes
kubectl get pods -n adk-travel
kubectl get services -n adk-travel

# 2. Scale agents
kubectl scale deployment flight-agent --replicas=5 -n adk-travel

# 3. Check metrics
kubectl port-forward service/travel-coordinator 8090:8090 -n adk-travel
# Visit http://localhost:8090/metrics

# 4. Test load balancing
for i in {1..10}; do curl http://LOAD_BALANCER_IP/health; done

# 5. View logs
kubectl logs -f deployment/travel-coordinator -n adk-travel

# 6. Monitor with kubectl top
kubectl top pods -n adk-travel
kubectl top nodes

# 7. Test auto-scaling
# Generate load to trigger HPA
kubectl run -i --tty load-generator --rm --image=busybox --restart=Never -- /bin/sh
# while true; do wget -q -O- http://travel-coordinator/health; done# agents-k8s-google-tf
