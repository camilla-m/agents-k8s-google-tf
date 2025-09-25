# ====================================
# File: src/flight_agent.py
# ====================================
from src.base_agent import BaseAgent
import requests
import json
from typing import Dict, Any, Optional, List

class FlightAgent(BaseAgent):
    """Specialized agent for flight search and booking"""
    
    def __init__(self):
        super().__init__("flight-agent", "flight_search_and_booking")
        self.flight_apis = {
            "search": "https://api.amadeus.com/v2/shopping/flight-offers",
            "book": "https://api.amadeus.com/v1/booking/flight-orders"
        }
    
    def process_request(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process flight-related requests"""
        start_time = time.time()
        
        try:
            # Parse query for flight parameters
            flight_params = self._parse_flight_query(query)
            
            # Search flights
            flight_options = self._search_flights(flight_params)
            
            # Format response
            response = {
                "agent": self.agent_name,
                "type": "flight_search",
                "query": query,
                "results": flight_options,
                "context": context or {}
            }
            
            duration = time.time() - start_time
            self._log_interaction(query, response, duration)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing flight request: {str(e)}")
            return {
                "agent": self.agent_name,
                "error": str(e),
                "query": query
            }
    
    def _parse_flight_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language query to extract flight parameters"""
        # Simplified parsing - in production, use NLP/ADK parsing
        params = {
            "origin": "SFO",  # Default values
            "destination": "NRT",
            "departure_date": "2025-10-15",
            "return_date": "2025-10-22",
            "passengers": 1
        }
        
        # Extract from query (simplified)
        if "tokyo" in query.lower():
            params["destination"] = "NRT"
        if "new york" in query.lower():
            params["destination"] = "JFK"
        if "london" in query.lower():
            params["destination"] = "LHR"
            
        return params
    
    def _search_flights(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Mock flight search - replace with real API"""
        # Mock flight data
        mock_flights = [
            {
                "flight_id": "AA123",
                "airline": "American Airlines",
                "origin": params["origin"],
                "destination": params["destination"],
                "departure_time": "08:00",
                "arrival_time": "14:30",
                "price": 850,
                "currency": "USD",
                "duration": "11h 30m",
                "stops": 0
            },
            {
                "flight_id": "UA456",
                "airline": "United Airlines",
                "origin": params["origin"],
                "destination": params["destination"],
                "departure_time": "15:20",
                "arrival_time": "21:45",
                "price": 920,
                "currency": "USD",
                "duration": "11h 25m",
                "stops": 0
            }
        ]
        
        return mock_flights