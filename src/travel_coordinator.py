# ====================================
# File: src/travel_coordinator.py
# ====================================
from flask import Flask, request, jsonify
from src.flight_agent import FlightAgent
from src.hotel_agent import HotelAgent
from src.activity_agent import ActivityAgent
import json
import threading
import time
from typing import Dict, Any

class TravelCoordinator:
    """Coordinates multiple agents to handle complex travel requests"""
    
    def __init__(self):
        self.flight_agent = FlightAgent()
        self.hotel_agent = HotelAgent()
        self.activity_agent = ActivityAgent()
        
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                "status": "healthy",
                "service": "travel-coordinator",
                "agents": {
                    "flight": self.flight_agent.health_check(),
                    "hotel": self.hotel_agent.health_check(),
                    "activity": self.activity_agent.health_check()
                }
            })
        
        @self.app.route('/plan', methods=['POST'])
        def plan_trip():
            try:
                data = request.get_json()
                query = data.get('query', '')
                destination = data.get('destination', '')
                days = data.get('days', 3)
                budget = data.get('budget', 1000)
                
                # Coordinate agents
                plan = self._coordinate_trip_planning(query, destination, days, budget)
                
                return jsonify(plan)
                
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/agent/<agent_type>', methods=['POST'])
        def query_agent(agent_type):
            try:
                data = request.get_json()
                query = data.get('query', '')
                context = data.get('context', {})
                
                agent_map = {
                    'flight': self.flight_agent,
                    'hotel': self.hotel_agent,
                    'activity': self.activity_agent
                }
                
                if agent_type not in agent_map:
                    return jsonify({"error": "Unknown agent type"}), 400
                
                result = agent_map[agent_type].process_request(query, context)
                return jsonify(result)
                
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    
    def _coordinate_trip_planning(self, query: str, destination: str, days: int, budget: int) -> Dict[str, Any]:
        """Coordinate multiple agents for comprehensive trip planning"""
        
        # Create context for agents
        context = {
            "destination": destination,
            "days": days,
            "budget": budget,
            "coordination_id": f"trip_{int(time.time())}"
        }
        
        # Query agents in parallel
        results = {}
        threads = []
        
        def query_flight_agent():
            flight_query = f"Find flights to {destination} for {days} days"
            results['flights'] = self.flight_agent.process_request(flight_query, context)
        
        def query_hotel_agent():
            hotel_query = f"Find hotels in {destination} for {days} nights within budget"
            results['hotels'] = self.hotel_agent.process_request(hotel_query, context)
        
        def query_activity_agent():
            activity_query = f"Recommend activities in {destination} for {days} days"
            results['activities'] = self.activity_agent.process_request(activity_query, context)
        
        # Execute in parallel
        threads = [
            threading.Thread(target=query_flight_agent),
            threading.Thread(target=query_hotel_agent),
            threading.Thread(target=query_activity_agent)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Compile comprehensive plan
        plan = {
            "trip_id": context["coordination_id"],
            "destination": destination,
            "duration": f"{days} days",
            "budget": budget,
            "flights": results.get('flights', {}),
            "hotels": results.get('hotels', {}),
            "activities": results.get('activities', {}),
            "summary": self._generate_summary(results, destination, days, budget),
            "total_estimated_cost": self._calculate_total_cost(results),
            "timestamp": time.time()
        }
        
        return plan
    
    def _generate_summary(self, results: Dict, destination: str, days: int, budget: int) -> str:
        """Generate trip summary from agent results"""
        flight_count = len(results.get('flights', {}).get('results', []))
        hotel_count = len(results.get('hotels', {}).get('results', []))
        activity_count = len(results.get('activities', {}).get('results', []))
        
        return f"Found {flight_count} flight options, {hotel_count} hotels, and {activity_count} activities for your {days}-day trip to {destination}."
    
    def _calculate_total_cost(self, results: Dict) -> int:
        """Calculate estimated total cost"""
        total = 0
        
        # Get cheapest flight
        flights = results.get('flights', {}).get('results', [])
        if flights:
            total += min(flight['price'] for flight in flights)
        
        # Get cheapest hotel per night
        hotels = results.get('hotels', {}).get('results', [])
        if hotels:
            min_hotel_price = min(hotel['price_per_night'] for hotel in hotels)
            total += min_hotel_price * 3  # Assuming 3 nights
        
        # Add activity costs
        activities = results.get('activities', {}).get('results', [])
        if activities:
            total += sum(activity['price'] for activity in activities[:3])  # Top 3 activities
        
        return total

    def run(self, host='0.0.0.0', port=8080, debug=False):
        """Run the Flask application"""
        self.app.run(host=host, port=port, debug=debug)
