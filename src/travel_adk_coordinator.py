"""
Google ADK Travel Coordinator
Orchestrates multiple ADK agents for comprehensive travel planning using Vertex AI and Gemini
"""

from flask import Flask, request, jsonify
import json
import threading
import time
import os
import logging
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from prometheus_client import Counter, Histogram, Gauge

# Import ADK agents
from src.flight_adk_agent import FlightADKAgent
from src.hotel_adk_agent import HotelADKAgent  
from src.activity_adk_agent import ActivityADKAgent

# Metrics for coordinator
coordinator_requests = Counter('coordinator_requests_total', 'Total coordinator requests', ['endpoint', 'status'])
coordinator_duration = Histogram('coordinator_request_duration_seconds', 'Coordinator request duration')
active_coordinations = Gauge('active_coordinations', 'Active multi-agent coordinations')
agent_utilization = Counter('agent_utilization_total', 'Agent utilization count', ['agent_type', 'request_type'])

class TravelADKCoordinator:
    """Coordinates multiple Google ADK agents for comprehensive travel planning"""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.logger = logging.getLogger(__name__)
        
        # Initialize ADK agents with error handling
        self.agents = {}
        self._initialize_agents()
        
        # Flask application setup
        self.app = Flask(__name__)
        self.app.config['JSON_SORT_KEYS'] = False
        self._setup_routes()
        
        # Conversation memory across agents
        self.coordinator_memory = {}
        
        # Thread pool for concurrent agent queries
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="adk-coordinator")
        
        self.logger.info("ADK Travel Coordinator initialized successfully")
    
    def _initialize_agents(self):
        """Initialize all ADK agents with proper error handling"""
        agent_configs = [
            ("flight", FlightADKAgent),
            ("hotel", HotelADKAgent),
            ("activity", ActivityADKAgent)
        ]
        
        initialized_agents = []
        failed_agents = []
        
        for agent_name, agent_class in agent_configs:
            try:
                self.logger.info(f"Initializing {agent_name} agent...")
                agent = agent_class(self.project_id)
                self.agents[agent_name] = agent
                initialized_agents.append(agent_name)
                self.logger.info(f"✅ {agent_name} agent initialized")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize {agent_name} agent: {e}")
                failed_agents.append(agent_name)
        
        if not self.agents:
            raise RuntimeError("No ADK agents could be initialized")
        
        self.logger.info(f"Coordinator ready with {len(initialized_agents)} agents: {', '.join(initialized_agents)}")
        
        if failed_agents:
            self.logger.warning(f"Failed agents: {', '.join(failed_agents)}")
    
    def _setup_routes(self):
        """Setup Flask routes for ADK coordinator"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Comprehensive health check for all ADK components"""
            start_time = time.time()
            
            try:
                agent_health = {}
                overall_status = "healthy"
                
                # Check each agent's health
                for agent_name, agent in self.agents.items():
                    try:
                        health_result = agent.health_check()
                        agent_health[agent_name] = health_result
                        
                        if health_result.get('status') != 'healthy':
                            overall_status = "degraded"
                    except Exception as e:
                        agent_health[agent_name] = {
                            "status": "unhealthy",
                            "error": str(e)
                        }
                        overall_status = "degraded"
                
                health_status = {
                    "status": overall_status,
                    "service": "travel-adk-coordinator",
                    "adk_version": "1.0",
                    "project_id": self.project_id,
                    "coordinator_stats": {
                        "active_agents": len(self.agents),
                        "active_conversations": len(self.coordinator_memory),
                        "response_time_ms": round((time.time() - start_time) * 1000, 2)
                    },
                    "agents": agent_health,
                    "timestamp": time.time()
                }
                
                coordinator_requests.labels(endpoint="health", status="success").inc()
                return jsonify(health_status)
                
            except Exception as e:
                coordinator_requests.labels(endpoint="health", status="error").inc()
                return jsonify({
                    "status": "unhealthy",
                    "service": "travel-adk-coordinator",
                    "error": str(e),
                    "timestamp": time.time()
                }), 500
        
        @self.app.route('/chat', methods=['POST'])
        def chat_with_coordinator():
            """Main ADK conversation endpoint with intelligent agent routing"""
            start_time = time.time()
            
            try:
                data = request.get_json()
                if not data:
                    coordinator_requests.labels(endpoint="chat", status="error").inc()
                    return jsonify({"error": "JSON data required"}), 400
                
                user_message = data.get('message', '').strip()
                conversation_id = data.get('conversation_id')
                
                if not user_message:
                    coordinator_requests.labels(endpoint="chat", status="error").inc()
                    return jsonify({"error": "Message is required"}), 400
                
                # Route to appropriate agent(s) or coordinate multiple agents
                response = self._coordinate_conversation(user_message, conversation_id)
                
                duration = time.time() - start_time
                coordinator_duration.observe(duration)
                coordinator_requests.labels(endpoint="chat", status="success").inc()
                
                return jsonify(response)
                
            except Exception as e:
                coordinator_requests.labels(endpoint="chat", status="error").inc()
                self.logger.error(f"Chat coordination error: {e}")
                return jsonify({
                    "error": "Internal server error",
                    "message": "Please try again later",
                    "timestamp": time.time()
                }), 500
        
        @self.app.route('/agent/<agent_type>/chat', methods=['POST'])
        def chat_with_agent(agent_type):
            """Direct chat with specific ADK agent"""
            start_time = time.time()
            
            try:
                if agent_type not in self.agents:
                    coordinator_requests.labels(endpoint=f"agent_{agent_type}", status="error").inc()
                    return jsonify({
                        "error": f"Unknown agent type: {agent_type}",
                        "available_agents": list(self.agents.keys())
                    }), 400
                
                data = request.get_json()
                if not data:
                    return jsonify({"error": "JSON data required"}), 400
                
                user_message = data.get('message', '').strip()
                conversation_id = data.get('conversation_id')
                
                if not user_message:
                    return jsonify({"error": "Message is required"}), 400
                
                # Track agent utilization
                agent_utilization.labels(agent_type=agent_type, request_type="direct").inc()
                
                # Route to specific agent
                agent = self.agents[agent_type]
                if conversation_id:
                    result = agent.continue_conversation(user_message, conversation_id)
                else:
                    result = agent.start_conversation(user_message)
                
                duration = time.time() - start_time
                coordinator_duration.observe(duration)
                coordinator_requests.labels(endpoint=f"agent_{agent_type}", status="success").inc()
                
                return jsonify(result)
                
            except Exception as e:
                coordinator_requests.labels(endpoint=f"agent_{agent_type}", status="error").inc()
                self.logger.error(f"Agent {agent_type} chat error: {e}")
                return jsonify({
                    "error": "Agent communication failed",
                    "agent": agent_type,
                    "timestamp": time.time()
                }), 500
        
        @self.app.route('/plan', methods=['POST'])
        def comprehensive_trip_planning():
            """Comprehensive trip planning using multiple ADK agents with advanced coordination"""
            start_time = time.time()
            
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "JSON data required"}), 400
                
                # Extract and validate planning parameters
                destination = data.get('destination', '').strip()
                days = int(data.get('days', 3))
                budget = float(data.get('budget', 2000))
                interests = data.get('interests', [])
                travel_style = data.get('travel_style', 'balanced')
                
                if not destination:
                    coordinator_requests.labels(endpoint="plan", status="error").inc()
                    return jsonify({"error": "Destination is required"}), 400
                
                if days < 1 or days > 30:
                    return jsonify({"error": "Days must be between 1 and 30"}), 400
                
                if budget < 100:
                    return jsonify({"error": "Budget must be at least $100"}), 400
                
                # Generate comprehensive travel plan using all available agents
                plan = self._generate_comprehensive_plan(
                    destination, days, budget, interests, travel_style
                )
                
                duration = time.time() - start_time
                coordinator_duration.observe(duration)
                coordinator_requests.labels(endpoint="plan", status="success").inc()
                
                return jsonify(plan)
                
            except ValueError as e:
                coordinator_requests.labels(endpoint="plan", status="error").inc()
                return jsonify({"error": f"Invalid input: {str(e)}"}), 400
            except Exception as e:
                coordinator_requests.labels(endpoint="plan", status="error").inc()
                self.logger.error(f"Trip planning error: {e}")
                return jsonify({
                    "error": "Trip planning failed",
                    "message": "Please try again with different parameters",
                    "timestamp": time.time()
                }), 500
        
        @self.app.route('/conversations', methods=['GET'])
        def list_conversations():
            """List active conversations across all agents"""
            try:
                conversations = []
                
                for agent_name, agent in self.agents.items():
                    agent_conversations = getattr(agent, 'conversation_memory', {})
                    for conv_id, conv_data in agent_conversations.items():
                        conversations.append({
                            "conversation_id": conv_id,
                            "agent": agent_name,
                            "context": conv_data.get('context', {}),
                            "last_update": conv_data.get('context', {}).get('last_update', 0)
                        })
                
                return jsonify({
                    "total_conversations": len(conversations),
                    "conversations": sorted(conversations, key=lambda x: x['last_update'], reverse=True)
                })
                
            except Exception as e:
                self.logger.error(f"Error listing conversations: {e}")
                return jsonify({"error": "Failed to list conversations"}), 500
        
        @self.app.route('/stats', methods=['GET'])
        def get_coordinator_stats():
            """Get coordinator and agent statistics"""
            try:
                stats = {
                    "coordinator": {
                        "project_id": self.project_id,
                        "active_agents": len(self.agents),
                        "active_conversations": len(self.coordinator_memory)
                    },
                    "agents": {}
                }
                
                for agent_name, agent in self.agents.items():
                    if hasattr(agent, 'get_stats'):
                        stats["agents"][agent_name] = agent.get_stats()
                    else:
                        stats["agents"][agent_name] = {
                            "agent_name": agent_name,
                            "status": "active"
                        }
                
                return jsonify(stats)
                
            except Exception as e:
                self.logger.error(f"Error getting stats: {e}")
                return jsonify({"error": "Failed to get statistics"}), 500
    
    def _coordinate_conversation(self, user_message: str, conversation_id: str = None) -> Dict[str, Any]:
        """Intelligently coordinate conversation across multiple ADK agents"""
        
        if not conversation_id:
            conversation_id = f"coord_{int(time.time())}"
        
        # Analyze user message to determine which agents to involve
        involved_agents = self._determine_agents_needed(user_message)
        
        if not involved_agents:
            # Fallback to all agents if none specifically identified
            involved_agents = list(self.agents.values())
        
        if len(involved_agents) == 1:
            # Single agent conversation
            agent = involved_agents[0]
            agent_utilization.labels(agent_type=agent.agent_name, request_type="single").inc()
            
            if conversation_id in self.coordinator_memory:
                return agent.continue_conversation(user_message, conversation_id)
            else:
                response = agent.start_conversation(user_message, conversation_id)
                self.coordinator_memory[conversation_id] = {"primary_agent": agent.agent_name}
                return response
        else:
            # Multi-agent coordination needed
            agent_utilization.labels(agent_type="coordinator", request_type="multi").inc()
            return self._multi_agent_conversation(user_message, conversation_id, involved_agents)
    
    def _determine_agents_needed(self, message: str) -> List:
        """Intelligently determine which agents are needed based on message content"""
        message_lower = message.lower()
        needed_agents = []
        
        # Enhanced keyword mapping with weights
        agent_keywords = {
            "flight": {
                "high": ["flight", "fly", "airline", "airport", "departure", "arrival", "ticket", "boarding"],
                "medium": ["travel", "trip", "journey", "aviation"]
            },
            "hotel": {
                "high": ["hotel", "accommodation", "stay", "room", "lodge", "resort", "check-in", "booking"],
                "medium": ["sleep", "night", "bed", "suite"]
            },
            "activity": {
                "high": ["activity", "restaurant", "food", "tour", "attraction", "museum", "experience", "sightseeing"],
                "medium": ["eat", "visit", "see", "do", "entertainment", "culture"]
            }
        }
        
        agent_scores = {}
        
        # Calculate scores for each agent
        for agent_name, keywords in agent_keywords.items():
            score = 0
            for word in keywords["high"]:
                score += message_lower.count(word) * 3
            for word in keywords["medium"]:
                score += message_lower.count(word) * 1
            
            if score > 0:
                agent_scores[agent_name] = score
        
        # Select agents based on scores
        if agent_scores:
            # If there's a clear winner (score > 3), use only that agent
            max_score = max(agent_scores.values())
            if max_score >= 3:
                best_agent = max(agent_scores, key=agent_scores.get)
                if best_agent in self.agents:
                    needed_agents.append(self.agents[best_agent])
            else:
                # Multiple agents needed
                for agent_name, score in agent_scores.items():
                    if agent_name in self.agents:
                        needed_agents.append(self.agents[agent_name])
        
        # Comprehensive planning keywords - use all agents
        comprehensive_keywords = ["plan", "trip", "vacation", "travel", "visit", "itinerary", "complete", "comprehensive"]
        if any(word in message_lower for word in comprehensive_keywords):
            return list(self.agents.values())
        
        # If no specific agents identified, use smart fallback
        if not needed_agents:
            # For questions/requests, try the most general agent first
            general_keywords = ["recommend", "suggest", "best", "good", "help", "advice"]
            if any(word in message_lower for word in general_keywords):
                needed_agents = [self.agents.get("activity", list(self.agents.values())[0])]
        
        return needed_agents
    
    def _multi_agent_conversation(self, user_message: str, conversation_id: str, agents: List) -> Dict[str, Any]:
        """Handle conversation involving multiple ADK agents with improved coordination"""
        
        active_coordinations.inc()
        
        try:
            responses = {}
            
            # Use ThreadPoolExecutor for concurrent agent queries
            future_to_agent = {}
            
            with ThreadPoolExecutor(max_workers=len(agents), thread_name_prefix=f"coord-{conversation_id}") as executor:
                for agent in agents:
                    future = executor.submit(self._query_agent_safely, agent, user_message, conversation_id)
                    future_to_agent[future] = agent
                
                # Collect results as they complete
                for future in as_completed(future_to_agent, timeout=30):
                    agent = future_to_agent[future]
                    try:
                        result = future.result()
                        responses[agent.agent_name] = result
                    except Exception as e:
                        self.logger.error(f"Agent {agent.agent_name} failed: {e}")
                        responses[agent.agent_name] = {
                            "error": f"Agent {agent.agent_name} failed: {str(e)}",
                            "agent": agent.agent_name,
                            "timestamp": time.time()
                        }
            
            # Update coordinator memory
            self.coordinator_memory[conversation_id] = {
                "involved_agents": [agent.agent_name for agent in agents],
                "last_update": time.time(),
                "message_count": self.coordinator_memory.get(conversation_id, {}).get("message_count", 0) + 1
            }
            
            # Generate coordinated response
            coordinated_response = {
                "conversation_id": conversation_id,
                "coordinator": "travel-adk-coordinator",
                "multi_agent_response": True,
                "agent_responses": responses,
                "summary": self._generate_coordinator_summary(responses),
                "coordination_quality": self._assess_coordination_quality(responses),
                "timestamp": time.time()
            }
            
            return coordinated_response
            
        finally:
            active_coordinations.dec()
    
    def _query_agent_safely(self, agent, message: str, conversation_id: str) -> Dict[str, Any]:
        """Safely query an agent with timeout and error handling"""
        try:
            if conversation_id in self.coordinator_memory:
                # Check if this agent was involved in previous turns
                involved_agents = self.coordinator_memory[conversation_id].get("involved_agents", [])
                if agent.agent_name in involved_agents:
                    return agent.continue_conversation(message, conversation_id)
            
            return agent.start_conversation(message, conversation_id)
            
        except Exception as e:
            self.logger.error(f"Safe agent query failed for {agent.agent_name}: {e}")
            return {
                "error": str(e),
                "agent": agent.agent_name,
                "timestamp": time.time()
            }
    
    def _generate_coordinator_summary(self, agent_responses: Dict[str, Any]) -> str:
        """Generate an intelligent coordinated summary from multiple agent responses"""
        summaries = []
        successful_agents = []
        failed_agents = []
        
        for agent_name, response in agent_responses.items():
            if isinstance(response, dict):
                if "response" in response and response.get("response"):
                    agent_type = agent_name.replace("-adk-agent", "").replace("-", " ").title()
                    response_text = response['response']
                    
                    # Extract key information from response
                    summary_text = self._extract_key_info(response_text, agent_type)
                    summaries.append(f"**{agent_type}**: {summary_text}")
                    successful_agents.append(agent_type)
                    
                elif "error" in response:
                    agent_type = agent_name.replace("-adk-agent", "").replace("-", " ").title()
                    failed_agents.append(agent_type)
        
        # Build comprehensive summary
        if summaries:
            main_summary = " | ".join(summaries)
            
            # Add coordination context
            if len(successful_agents) > 1:
                coordination_note = f" (Coordinated response from {len(successful_agents)} specialized agents)"
            else:
                coordination_note = ""
            
            if failed_agents:
                failure_note = f" Note: {', '.join(failed_agents)} agent(s) encountered issues."
                main_summary += failure_note
            
            return main_summary + coordination_note
        
        return "Multiple travel agents coordinated to provide comprehensive assistance."
    
    def _extract_key_info(self, response_text: str, agent_type: str) -> str:
        """Extract key information from agent response for summary"""
        # Truncate long responses and extract most important parts
        if len(response_text) <= 200:
            return response_text
        
        # Split into sentences and take the most informative ones
        sentences = response_text.split('. ')
        
        # Priority sentences based on agent type
        priority_keywords = {
            "Flight": ["flight", "airline", "price", "$", "departure", "arrival"],
            "Hotel": ["hotel", "room", "night", "$", "location", "amenities"],
            "Activity": ["activity", "restaurant", "experience", "recommendation"]
        }
        
        keywords = priority_keywords.get(agent_type, [])
        
        # Score sentences based on keyword presence
        scored_sentences = []
        for sentence in sentences:
            score = sum(1 for keyword in keywords if keyword.lower() in sentence.lower())
            scored_sentences.append((sentence.strip(), score))
        
        # Sort by score and take top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Build summary from top sentences
        summary_parts = []
        char_count = 0
        
        for sentence, score in scored_sentences:
            if char_count + len(sentence) <= 180:
                summary_parts.append(sentence)
                char_count += len(sentence)
            else:
                break
        
        if summary_parts:
            return '. '.join(summary_parts) + ('...' if char_count > 150 else '')
        else:
            # Fallback to first 180 characters
            return response_text[:180] + ('...' if len(response_text) > 180 else '')
    
    def _assess_coordination_quality(self, responses: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of multi-agent coordination"""
        total_agents = len(responses)
        successful_responses = sum(1 for r in responses.values() if isinstance(r, dict) and "response" in r)
        error_responses = total_agents - successful_responses
        
        # Calculate response times if available
        response_times = []
        function_calls = 0
        
        for response in responses.values():
            if isinstance(response, dict):
                # Count function calls across all agents
                if "function_calls" in response:
                    function_calls += len(response["function_calls"])
        
        quality_score = (successful_responses / total_agents) * 100 if total_agents > 0 else 0
        
        return {
            "success_rate": f"{quality_score:.1f}%",
            "successful_agents": successful_responses,
            "failed_agents": error_responses,
            "total_function_calls": function_calls,
            "coordination_effectiveness": "high" if quality_score >= 80 else "medium" if quality_score >= 50 else "low"
        }
    
    def _generate_comprehensive_plan(self, destination: str, days: int, budget: int, 
                                   interests: List[str], travel_style: str) -> Dict[str, Any]:
        """Generate comprehensive travel plan using all available ADK agents with advanced coordination"""
        
        plan_id = f"plan_{int(time.time())}"
        self.logger.info(f"Generating comprehensive plan {plan_id} for {destination}")
        
        # Create specialized queries for each agent based on parameters
        queries = self._create_specialized_queries(destination, days, budget, interests, travel_style)
        
        # Query all available agents concurrently
        results = {}
        
        with ThreadPoolExecutor(max_workers=len(self.agents), thread_name_prefix=f"plan-{plan_id}") as executor:
            future_to_agent = {}
            
            for agent_name, agent in self.agents.items():
                if agent_name in queries:
                    query = queries[agent_name]
                    future = executor.submit(self._execute_planning_query, agent, query, plan_id)
                    future_to_agent[future] = agent_name
            
            # Collect results with timeout handling
            for future in as_completed(future_to_agent, timeout=45):
                agent_name = future_to_agent[future]
                try:
                    result = future.result()
                    results[agent_name] = result
                    self.logger.info(f"Plan query completed for {agent_name}")
                except Exception as e:
                    self.logger.error(f"Plan query failed for {agent_name}: {e}")
                    results[agent_name] = {"error": f"Failed to get {agent_name} recommendations: {str(e)}"}
        
        # Compile comprehensive plan with intelligent synthesis
        comprehensive_plan = {
            "plan_id": plan_id,
            "destination": destination,
            "duration_days": days,
            "budget_usd": budget,
            "travel_style": travel_style,
            "interests": interests,
            "generated_by": "Google ADK Travel Coordinator",
            "adk_version": "1.0",
            "agent_recommendations": results,
            "coordinator_summary": self._create_plan_summary(results, destination, days),
            "intelligent_insights": self._generate_intelligent_insights(results, destination, budget, travel_style),
            "next_steps": self._generate_smart_next_steps(results, destination),
            "budget_breakdown": self._analyze_budget_breakdown(results, budget),
            "generated_at": time.time(),
            "plan_quality": self._assess_plan_quality(results)
        }
        
        return comprehensive_plan
    
    def _create_specialized_queries(self, destination: str, days: int, budget: int, 
                                  interests: List[str], travel_style: str) -> Dict[str, str]:
        """Create specialized queries for each agent based on user parameters"""
        
        # Budget allocation strategy
        flight_budget = int(budget * 0.4)  # 40% for flights
        hotel_budget = int(budget * 0.35)  # 35% for accommodation
        activity_budget = int(budget * 0.25)  # 25% for activities
        
        hotel_per_night = hotel_budget // max(days - 1, 1)  # Assuming days-1 nights
        
        # Interest-based query enhancement
        interest_context = ""
        if interests:
            interest_context = f" with focus on {', '.join(interests)} experiences"
        
        # Travel style context
        style_context = {
            "budget": "budget-conscious and value-focused",
            "mid-range": "balanced comfort and value",
            "luxury": "premium and high-end",
            "business": "business travel optimized",
            "adventure": "adventure and unique experiences focused"
        }.get(travel_style, "balanced")
        
        queries = {}
        
        if "flight" in self.agents:
            queries["flight"] = (
                f"Find the best flight options to {destination} for a {days}-day trip. "
                f"Budget around ${flight_budget}, {style_context} options preferred{interest_context}. "
                f"Consider both direct and connecting flights, and suggest optimal timing."
            )
        
        if "hotel" in self.agents:
            queries["hotel"] = (
                f"Find {travel_style} accommodation in {destination} for {days-1} nights. "
                f"Budget around ${hotel_per_night} per night. Location should be convenient for "
                f"exploring the city{interest_context}. Consider neighborhood safety and transportation access."
            )
        
        if "activity" in self.agents:
            queries["activity"] = (
                f"Recommend a {days}-day itinerary for {destination}{interest_context}. "
                f"Activity budget around ${activity_budget}, {style_context} preferences. "
                f"Include must-see attractions, dining recommendations, and unique local experiences."
            )
        
        return queries
    
    def _execute_planning_query(self, agent, query: str, plan_id: str) -> Dict[str, Any]:
        """Execute a planning query for a specific agent"""
        try:
            return agent.start_conversation(query, plan_id)
        except Exception as e:
            self.logger.error(f"Planning query failed for {agent.agent_name}: {e}")
            return {"error": str(e), "agent": agent.agent_name}
    
    def _create_plan_summary(self, results: Dict[str, Any], destination: str, days: int) -> str:
        """Create an intelligent coordinated summary of the travel plan"""
        
        successful_agents = [name for name, result in results.items() 
                           if isinstance(result, dict) and "response" in result]
        
        base_summary = (
            f"Complete {days}-day travel plan for {destination} generated using Google ADK agents "
            f"with Vertex AI and Gemini. "
        )
        
        if len(successful_agents) >= 3:
            detail_summary = (
                "Includes personalized flight recommendations, carefully selected accommodation "
                "options matching your travel style, and curated activities tailored to your interests. "
            )
        elif len(successful_agents) >= 2:
            detail_summary = (
                f"Includes recommendations from {len(successful_agents)} specialized agents. "
            )
        else:
            detail_summary = "Partial recommendations available. "
        
        ai_summary = (
            "Each recommendation is powered by advanced AI for maximum relevance to your preferences "
            "and travel requirements."
        )
        
        return base_summary + detail_summary + ai_summary
    
    def _generate_intelligent_insights(self, results: Dict[str, Any], destination: str, 
                                     budget: int, travel_style: str) -> List[str]:
        """Generate intelligent insights based on the coordinated results"""
        insights = []
        
        # Analyze results for insights
        has_flight_data = "flight" in results and "error" not in results["flight"]
        has_hotel_data = "hotel" in results and "error" not in results["hotel"]
        has_activity_data = "activity" in results and "error" not in results["activity"]
        
        if has_flight_data and has_hotel_data:
            insights.append(
                f"Your {travel_style} travel style is well-suited for {destination}. "
                "Flight and accommodation options align with your preferences."
            )
        
        if budget >= 2000:
            insights.append(
                "Your budget allows for premium experiences. Consider upgrading flights or accommodation "
                "for enhanced comfort and unique amenities."
            )
        elif budget <= 800:
            insights.append(
                "Budget-conscious planning detected. Look for package deals and off-peak travel times "
                "to maximize value for your investment."
            )
        
        if has_activity_data:
            insights.append(
                f"Local activities in {destination} offer diverse experiences. "
                "Consider booking popular attractions in advance to avoid disappointment."
            )
        
        # Seasonal insights (simplified)
        import datetime
        current_month = datetime.datetime.now().month
        if current_month in [12, 1, 2]:
            insights.append("Winter travel considerations: Check weather conditions and pack accordingly.")
        elif current_month in [6, 7, 8]:
            insights.append("Summer travel peak season: Book accommodations early and expect higher prices.")
        
        return insights[:3]  # Limit to top 3 insights
    
    def _generate_smart_next_steps(self, results: Dict[str, Any], destination: str) -> List[str]:
        """Generate intelligent next steps based on available results"""
        steps = []
        
        if "flight" in results and "error" not in results["flight"]:
            steps.append("Review and compare flight options, considering timing and connections")
            steps.append("Book preferred flights to secure seats and pricing")
        
        if "hotel" in results and "error" not in results["hotel"]:
            steps.append("Confirm hotel availability for your exact dates and book reservation")
            steps.append("Check hotel cancellation policies and payment requirements")
        
        if "activity" in results and "error" not in results["activity"]:
            steps.append("Research and book time-sensitive activities and restaurant reservations")
            steps.append("Download offline maps and translation apps for easier navigation")
        
        # Universal steps
        steps.extend([
            f"Check visa and passport requirements for {destination}",
            "Review travel insurance options for international travel",
            "Notify banks of travel plans to avoid card issues",
            "Check current health and safety recommendations"
        ])
        
        return steps[:6]  # Limit to 6 most important steps
    
    def _analyze_budget_breakdown(self, results: Dict[str, Any], total_budget: int) -> Dict[str, Any]:
        """Analyze and provide budget breakdown insights"""
        breakdown = {
            "total_budget": total_budget,
            "currency": "USD",
            "allocation": {
                "flights": {"allocated": int(total_budget * 0.4), "percentage": 40},
                "accommodation": {"allocated": int(total_budget * 0.35), "percentage": 35},
                "activities": {"allocated": int(total_budget * 0.25), "percentage": 25}
            },
            "recommendations": []
        }
        
        # Add budget recommendations based on total
        if total_budget >= 3000:
            breakdown["recommendations"].append("Premium budget allows for luxury upgrades")
            breakdown["recommendations"].append("Consider business class flights or 5-star hotels")
        elif total_budget >= 1500:
            breakdown["recommendations"].append("Comfortable mid-range budget")
            breakdown["recommendations"].append("Good balance of comfort and experiences")
        else:
            breakdown["recommendations"].append("Budget-conscious travel")
            breakdown["recommendations"].append("Focus on value accommodations and free activities")
        
        return breakdown
    
    def _assess_plan_quality(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the overall quality of the generated plan"""
        total_agents = len(self.agents)
        successful_results = len([r for r in results.values() if "error" not in r])
        
        completeness = (successful_results / total_agents) * 100 if total_agents > 0 else 0
        
        quality_assessment = {
            "completeness_percentage": round(completeness, 1),
            "successful_components": successful_results,
            "total_components": total_agents,
            "overall_rating": (
                "Excellent" if completeness >= 90 else
                "Good" if completeness >= 70 else
                "Fair" if completeness >= 50 else
                "Needs Improvement"
            ),
            "recommendations": []
        }
        
        if completeness < 100:
            missing_components = [name for name, result in results.items() if "error" in result]
            quality_assessment["recommendations"].append(
                f"Some components had issues: {', '.join(missing_components)}. "
                "Consider trying again or contacting support."
            )
        
        return quality_assessment
    
    def run(self, host='0.0.0.0', port=8080, debug=False):
        """Run the ADK Travel Coordinator with proper configuration"""
        self.logger.info(f"Starting Travel ADK Coordinator on {host}:{port}")
        
        # Configure Flask for production
        if not debug:
            self.app.config['ENV'] = 'production'
            self.app.config['DEBUG'] = False
            self.app.config['TESTING'] = False
        
        try:
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        except Exception as e:
            self.logger.error(f"Failed to start coordinator: {e}")
            raise
        finally:
            # Cleanup
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True)
            self.logger.info("Travel ADK Coordinator shutdown complete")
    
    def shutdown(self):
        """Graceful shutdown of the coordinator and all agents"""
        self.logger.info("Initiating graceful shutdown of Travel ADK Coordinator")
        
        # Shutdown thread pool
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        
        # Clear coordinator memory
        conversation_count = len(self.coordinator_memory)
        self.coordinator_memory.clear()
        
        # Shutdown individual agents
        for agent_name, agent in self.agents.items():
            try:
                if hasattr(agent, 'shutdown'):
                    agent.shutdown()
                self.logger.info(f"Agent {agent_name} shutdown complete")
            except Exception as e:
                self.logger.error(f"Error shutting down agent {agent_name}: {e}")
        
        self.logger.info(f"Coordinator shutdown complete. Cleared {conversation_count} conversations.")