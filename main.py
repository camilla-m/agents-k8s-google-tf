# ====================================
# File: main.py
# ====================================
from src.travel_coordinator import TravelCoordinator
import os
from prometheus_client import start_http_server

def main():
    """Main application entry point"""
    
    # Start Prometheus metrics server
    metrics_port = int(os.getenv('METRICS_PORT', 8090))
    start_http_server(metrics_port)
    
    # Initialize and run travel coordinator
    coordinator = TravelCoordinator()
    
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print(f"Starting Travel Coordinator on {host}:{port}")
    print(f"Metrics available on port {metrics_port}")
    
    coordinator.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    main()