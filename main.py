#!/usr/bin/env python3
"""
Google ADK Travel System - Main Entry Point
Runs the Travel ADK Coordinator with multiple specialized agents using Vertex AI and Gemini
"""

import os
import sys
import logging
import signal
import time
from prometheus_client import start_http_server

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def setup_logging():
    """Setup structured logging for the application"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Configure logging format for cloud environments
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "adk-coordinator", "message": "%(message)s", "module": "%(name)s"}',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    # Set specific log levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

def validate_environment():
    """Validate required environment variables and configuration"""
    logger = logging.getLogger(__name__)
    
    # Required environment variables
    required_vars = {
        'GOOGLE_CLOUD_PROJECT': 'Google Cloud project ID is required for ADK functionality'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var}: {description}")
    
    if missing_vars:
        logger.error("Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        return False
    
    # Optional but recommended variables
    recommended_vars = {
        'GOOGLE_CLOUD_LOCATION': 'us-central1',
        'GOOGLE_APPLICATION_CREDENTIALS': '/var/secrets/google/service-account-key'
    }
    
    for var, default in recommended_vars.items():
        value = os.getenv(var, default)
        if var == 'GOOGLE_APPLICATION_CREDENTIALS':
            if not os.path.exists(value):
                logger.warning(f"{var} file not found at {value} - ADK may not work properly")
        logger.info(f"{var}: {value}")
    
    return True

def setup_metrics_server():
    """Setup Prometheus metrics server"""
    logger = logging.getLogger(__name__)
    metrics_port = int(os.getenv('METRICS_PORT', 8090))
    
    try:
        start_http_server(metrics_port)
        logger.info(f"📊 Metrics server started on port {metrics_port}")
        logger.info(f"📊 Metrics available at: http://localhost:{metrics_port}/metrics")
        return metrics_port
    except Exception as e:
        logger.warning(f"Could not start metrics server on port {metrics_port}: {e}")
        return None

def setup_signal_handlers(coordinator):
    """Setup graceful shutdown handlers"""
    logger = logging.getLogger(__name__)
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        
        # Give the coordinator a chance to cleanup
        if hasattr(coordinator, 'shutdown'):
            coordinator.shutdown()
        
        logger.info("Shutdown complete")
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def print_startup_info(project_id, host, port, metrics_port, debug):
    """Print comprehensive startup information"""
    logger = logging.getLogger(__name__)
    
    # ASCII Art for Google ADK
    startup_banner = """
    ╔═══════════════════════════════════════════════════╗
    ║              Google ADK Travel System             ║
    ║          Multi-Agent AI on Kubernetes            ║
    ╚═══════════════════════════════════════════════════╝
    """
    
    print(startup_banner)
    
    logger.info("🚀 Starting Google ADK Travel Coordinator")
    logger.info(f"🤖 ADK Version: 1.0")
    logger.info(f"🏗️  Project: {project_id}")
    logger.info(f"📍 Host: {host}:{port}")
    
    if metrics_port:
        logger.info(f"📊 Metrics: http://localhost:{metrics_port}/metrics")
    
    logger.info(f"🐍 Python: {sys.version.split()[0]}")
    logger.info(f"🔧 Debug Mode: {'Enabled' if debug else 'Disabled'}")
    
    # Agent information
    logger.info("🤖 ADK Agents:")
    logger.info("   • Flight Agent: Vertex AI + Gemini for flight search & booking")
    logger.info("   • Hotel Agent: AI-powered hotel recommendations & availability")
    logger.info("   • Activity Agent: Personalized activity & dining suggestions")
    logger.info("   • Coordinator: Multi-agent orchestration & conversation management")
    
    # Health check info
    logger.info(f"💚 Health Check: http://{host}:{port}/health")
    logger.info(f"💬 Chat Endpoint: http://{host}:{port}/chat")
    logger.info(f"📋 Plan Endpoint: http://{host}:{port}/plan")

def main():
    """Main application entry point"""
    
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Validate environment
        if not validate_environment():
            logger.error("❌ Environment validation failed")
            sys.exit(1)
        
        # Get configuration
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 8080))
        debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # Setup metrics server
        metrics_port = setup_metrics_server()
        
        # Print startup information
        print_startup_info(project_id, host, port, metrics_port, debug)
        
        # Import and initialize coordinator (after environment validation)
        logger.info("🔄 Initializing ADK Travel Coordinator...")
        
        try:
            from src.travel_adk_coordinator import TravelADKCoordinator
            coordinator = TravelADKCoordinator(project_id)
            logger.info("✅ ADK Travel Coordinator initialized successfully")
        except ImportError as e:
            logger.error(f"❌ Failed to import TravelADKCoordinator: {e}")
            logger.error("Ensure the src/ directory contains all required files")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Failed to initialize ADK coordinator: {e}")
            logger.error("Check your Google Cloud credentials and project configuration")
            sys.exit(1)
        
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(coordinator)
        
        # Health check before starting
        logger.info("🔍 Running pre-startup health checks...")
        try:
            # Test that agents can be initialized
            health_status = {
                "flight": coordinator.flight_agent.health_check(),
                "hotel": coordinator.hotel_agent.health_check(), 
                "activity": coordinator.activity_agent.health_check()
            }
            
            healthy_agents = sum(1 for status in health_status.values() if status.get('status') == 'healthy')
            logger.info(f"✅ Health check passed: {healthy_agents}/3 agents healthy")
            
            if healthy_agents < 3:
                logger.warning("⚠️  Some agents may not be fully initialized")
                for agent_name, status in health_status.items():
                    if status.get('status') != 'healthy':
                        logger.warning(f"   {agent_name}: {status.get('status', 'unknown')}")
            
        except Exception as e:
            logger.warning(f"⚠️  Pre-startup health check failed: {e}")
            logger.info("Continuing startup - health endpoint will provide detailed status")
        
        # Final startup message
        logger.info("="*70)
        logger.info("🎯 Google ADK Travel System Ready!")
        logger.info("="*70)
        logger.info("📖 Usage Examples:")
        logger.info(f'   curl -X POST http://{host}:{port}/chat -H "Content-Type: application/json" -d \'{{"message": "Plan a trip to Tokyo"}}\'')
        logger.info(f'   curl -X POST http://{host}:{port}/agent/flight/chat -H "Content-Type: application/json" -d \'{{"message": "Find flights to Tokyo"}}\'')
        logger.info(f'   curl http://{host}:{port}/health')
        logger.info("="*70)
        
        # Start the coordinator
        logger.info("🚀 Starting Flask application...")
        coordinator.run(host=host, port=port, debug=debug)
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown initiated by user")
    except Exception as e:
        logger.error(f"💥 Fatal error during startup: {e}")
        logger.error("Check logs above for details")
        sys.exit(1)
    finally:
        logger.info("👋 Google ADK Travel System shutdown complete")

if __name__ == "__main__":
    main()