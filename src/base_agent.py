# ====================================
# File: src/base_agent.py
# ====================================
from abc import ABC, abstractmethod
import logging
import json
import time
from typing import Dict, Any, Optional
from kubernetes import client, config
from prometheus_client import Counter, Histogram, Gauge

# Metrics
request_count = Counter('agent_requests_total', 'Total requests', ['agent_type', 'status'])
request_duration = Histogram('agent_request_duration_seconds', 'Request duration')
active_connections = Gauge('agent_active_connections', 'Active connections')

class BaseAgent(ABC):
    """Base class for all ADK agents"""
    
    def __init__(self, agent_name: str, specialization: str):
        self.agent_name = agent_name
        self.specialization = specialization
        self.logger = self._setup_logging()
        self.k8s_client = self._setup_kubernetes()
        
    def _setup_logging(self):
        """Setup structured logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='{"timestamp": "%(asctime)s", "agent": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
        )
        return logging.getLogger(self.agent_name)
    
    def _setup_kubernetes(self):
        """Initialize Kubernetes client"""
        try:
            # Try in-cluster config first
            config.load_incluster_config()
        except config.ConfigException:
            # Fallback to local config for development
            config.load_kube_config()
        
        return client.CoreV1Api()
    
    @abstractmethod
    def process_request(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process agent request - must be implemented by subclasses"""
        pass
    
    def health_check(self) -> Dict[str, str]:
        """Health check endpoint"""
        return {
            "status": "healthy",
            "agent": self.agent_name,
            "specialization": self.specialization,
            "timestamp": str(time.time())
        }
    
    def _log_interaction(self, query: str, response: Dict[str, Any], duration: float):
        """Log interaction with metrics"""
        request_count.labels(agent_type=self.agent_name, status="success").inc()
        request_duration.observe(duration)
        
        self.logger.info(f"Processed request: {query[:100]}... Duration: {duration:.2f}s")