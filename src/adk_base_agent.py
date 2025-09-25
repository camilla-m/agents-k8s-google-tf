"""
Google ADK Base Agent
Base class for all ADK agents using Vertex AI and Gemini
"""

import vertexai
from vertexai.generative_models import GenerativeModel, Tool
from abc import ABC, abstractmethod
import logging
import json
import time
import os
from typing import Dict, Any, Optional, List
from kubernetes import client, config
from prometheus_client import Counter, Histogram
from google.cloud import secretmanager

# Metrics for monitoring ADK agent performance
adk_request_count = Counter('adk_agent_requests_total', 'Total ADK requests', ['agent_type', 'status'])
adk_request_duration = Histogram('adk_agent_request_duration_seconds', 'ADK request duration')
adk_conversation_turns = Counter('adk_conversation_turns_total', 'Conversation turns', ['agent_type'])
adk_function_calls = Counter('adk_function_calls_total', 'Function calls by agents', ['agent_type', 'function_name'])

class ADKBaseAgent(ABC):
    """Base class for Google ADK agents using Vertex AI and Gemini"""
    
    def __init__(self, agent_name: str, specialization: str, project_id: str = None):
        self.agent_name = agent_name
        self.specialization = specialization
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
        
        # Initialize components
        self.logger = self._setup_logging()
        self.k8s_client = self._setup_kubernetes()
        
        # Initialize Vertex AI and Gemini
        try:
            self._setup_vertex_ai()
        except Exception as e:
            self.logger.error(f"Failed to initialize Vertex AI: {e}")
            raise
        
        # Conversation memory (in production, use Cloud Firestore/Redis)
        self.conversation_memory = {}
        
        self.logger.info(f"ADK Agent {self.agent_name} initialized successfully")
        
    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging for ADK agent"""
        logger = logging.getLogger(f"adk.{self.agent_name}")
        return logger
    
    def _setup_kubernetes(self):
        """Initialize Kubernetes client"""
        try:
            config.load_incluster_config()
            self.logger.info("Loaded in-cluster Kubernetes config")
        except config.ConfigException:
            try:
                config.load_kube_config()
                self.logger.info("Loaded local Kubernetes config")
            except Exception as e:
                self.logger.warning(f"Could not load Kubernetes config: {e}")
                return None
        
        try:
            return client.CoreV1Api()
        except Exception as e:
            self.logger.warning(f"Failed to create Kubernetes client: {e}")
            return None
    
    def _setup_vertex_ai(self):
        """Initialize Vertex AI and Gemini"""
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for ADK functionality")
        
        try:
            # Initialize Vertex AI
            vertexai.init(project=self.project_id, location=self.location)
            
            # Define tools/functions this agent can call
            self.tools = self._define_tools()
            
            # Create generative model with tools
            model_kwargs = {
                "model_name": "gemini-1.5-pro",
                "system_instruction": self._get_system_instruction()
            }
            
            if self.tools:
                model_kwargs["tools"] = self.tools
            
            self.model = GenerativeModel(**model_kwargs)
            
            self.logger.info(f"Vertex AI initialized for project {self.project_id} in {self.location}")
            
            # Test the model with a simple query
            try:
                test_chat = self.model.start_chat()
                test_response = test_chat.send_message("Hello, are you working?")
                self.logger.info("Gemini model test successful")
            except Exception as e:
                self.logger.warning(f"Gemini model test failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Vertex AI: {e}")
            raise
    
    @abstractmethod
    def _define_tools(self) -> Optional[List[Tool]]:
        """Define tools/functions available to this agent - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _get_system_instruction(self) -> str:
        """Get system instruction for this agent - must be implemented by subclasses"""
        pass
    
    def start_conversation(self, user_message: str, conversation_id: str = None) -> Dict[str, Any]:
        """Start a new conversation with the ADK agent"""
        start_time = time.time()
        
        if not conversation_id:
            conversation_id = f"{self.agent_name}_{int(time.time())}"
            
        self.logger.info(f"Starting conversation {conversation_id} with message: {user_message[:100]}...")
            
        try:
            # Initialize conversation in memory
            if conversation_id not in self.conversation_memory:
                self.conversation_memory[conversation_id] = {
                    "history": [],
                    "context": {
                        "agent": self.agent_name, 
                        "specialization": self.specialization,
                        "created_at": time.time()
                    }
                }
            
            # Start chat session with Gemini
            chat = self.model.start_chat(history=self.conversation_memory[conversation_id]["history"])
            
            # Send message and get response
            response = chat.send_message(user_message)
            
            # Handle function calls if any
            function_calls = []
            response_text = response.text
            
            # Check for function calls in the response
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_call = part.function_call
                            self.logger.info(f"Function call detected: {function_call.name}")
                            
                            # Execute the function call
                            function_response = self._handle_function_call(function_call)
                            function_calls.append({
                                "name": function_call.name,
                                "args": dict(function_call.args),
                                "result": function_response
                            })
                            
                            # Send function response back to model
                            function_response_message = f"Function {function_call.name} returned: {json.dumps(function_response)}"
                            response = chat.send_message(function_response_message)
                            response_text = response.text
            
            # Update conversation memory
            self.conversation_memory[conversation_id]["history"] = chat.history[-10:]  # Keep last 10 exchanges
            self.conversation_memory[conversation_id]["context"]["last_update"] = time.time()
            
            # Format response
            result = {
                "conversation_id": conversation_id,
                "agent": self.agent_name,
                "response": response_text,
                "function_calls": function_calls,
                "context": self.conversation_memory[conversation_id]["context"],
                "timestamp": time.time()
            }
            
            # Metrics and logging
            duration = time.time() - start_time
            adk_conversation_turns.labels(agent_type=self.agent_name).inc()
            adk_request_count.labels(agent_type=self.agent_name, status="success").inc()
            adk_request_duration.observe(duration)
            
            # Log function calls for metrics
            for fc in function_calls:
                adk_function_calls.labels(agent_type=self.agent_name, function_name=fc['name']).inc()
            
            self.logger.info(f"ADK conversation completed in {duration:.2f}s with {len(function_calls)} function calls")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            adk_request_count.labels(agent_type=self.agent_name, status="error").inc()
            adk_request_duration.observe(duration)
            
            self.logger.error(f"ADK conversation error after {duration:.2f}s: {str(e)}")
            return {
                "conversation_id": conversation_id,
                "agent": self.agent_name,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def continue_conversation(self, user_message: str, conversation_id: str) -> Dict[str, Any]:
        """Continue an existing conversation"""
        self.logger.info(f"Continuing conversation {conversation_id}")
        return self.start_conversation(user_message, conversation_id)
    
    def _handle_function_call(self, function_call) -> Dict[str, Any]:
        """Handle function calls from Gemini"""
        function_name = function_call.name
        function_args = dict(function_call.args)
        
        self.logger.info(f"ADK function call: {function_name} with args: {function_args}")
        
        # Call the appropriate tool function
        tool_method_name = f"_tool_{function_name}"
        if hasattr(self, tool_method_name):
            try:
                result = getattr(self, tool_method_name)(**function_args)
                self.logger.info(f"Function {function_name} executed successfully")
                return result
            except Exception as e:
                self.logger.error(f"Error executing tool {function_name}: {e}")
                return {"error": f"Tool {function_name} failed: {str(e)}"}
        else:
            self.logger.warning(f"Tool method {tool_method_name} not implemented")
            return {"error": f"Tool {function_name} not implemented"}
    
    def get_conversation_history(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation history for a specific conversation"""
        return self.conversation_memory.get(conversation_id)
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a specific conversation from memory"""
        if conversation_id in self.conversation_memory:
            del self.conversation_memory[conversation_id]
            self.logger.info(f"Cleared conversation {conversation_id}")
            return True
        return False
    
    def clear_old_conversations(self, max_age_hours: int = 24) -> int:
        """Clear conversations older than specified hours"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        old_conversations = []
        for conv_id, conv_data in self.conversation_memory.items():
            last_update = conv_data.get('context', {}).get('last_update', 0)
            if current_time - last_update > max_age_seconds:
                old_conversations.append(conv_id)
        
        for conv_id in old_conversations:
            del self.conversation_memory[conv_id]
        
        if old_conversations:
            self.logger.info(f"Cleared {len(old_conversations)} old conversations")
        
        return len(old_conversations)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "agent_name": self.agent_name,
            "specialization": self.specialization,
            "active_conversations": len(self.conversation_memory),
            "project_id": self.project_id,
            "location": self.location,
            "tools_available": len(self.tools) if self.tools else 0
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive ADK agent health check"""
        health_status = {
            "status": "healthy",
            "agent": self.agent_name,
            "specialization": self.specialization,
            "adk_version": "1.0",
            "vertex_ai_project": self.project_id,
            "vertex_ai_location": self.location,
            "active_conversations": len(self.conversation_memory),
            "tools_available": len(self.tools) if self.tools else 0,
            "timestamp": str(time.time())
        }
        
        # Test Vertex AI connectivity
        try:
            test_chat = self.model.start_chat()
            test_response = test_chat.send_message("Health check test")
            health_status["vertex_ai_status"] = "connected"
        except Exception as e:
            health_status["vertex_ai_status"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        # Test Kubernetes connectivity
        if self.k8s_client:
            try:
                # Try to list pods in the current namespace
                self.k8s_client.list_namespaced_pod(namespace="adk-travel", limit=1)
                health_status["kubernetes_status"] = "connected"
            except Exception as e:
                health_status["kubernetes_status"] = f"error: {str(e)}"
        else:
            health_status["kubernetes_status"] = "not_available"
        
        return health_status
    
    def shutdown(self):
        """Graceful shutdown of the agent"""
        self.logger.info(f"Shutting down ADK agent {self.agent_name}")
        
        # Clear conversations to free memory
        conversation_count = len(self.conversation_memory)
        self.conversation_memory.clear()
        
        self.logger.info(f"Cleared {conversation_count} conversations during shutdown")