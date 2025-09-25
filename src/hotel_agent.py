# ====================================
# File: src/hotel_agent.py
# ====================================
from src.base_agent import BaseAgent
import time
from typing import Dict, Any, Optional, List

class HotelAgent(BaseAgent):
    """Specialized agent for hotel search and booking"""
    
    def __init__(self):
        super().__init__("hotel-agent", "hotel_search_and_booking")
        self.hotel_apis = {
            "search": "https://api.booking.com/v1/hotels",
            "book": "https://api.booking.com/v1/bookings"
        }
    
    def process_request(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process hotel-related requests"""
        start_time = time.time()
        
        try:
            # Parse query for hotel parameters
            hotel_params = self._parse_hotel_query(query)
            
            # Search hotels
            hotel_options = self._search_hotels(hotel_params)
            
            # Format response
            response = {
                "agent": self.agent_name,
                "type": "hotel_search",
                "query": query,
                "results": hotel_options,
                "context": context or {}
            }
            
            duration = time.time() - start_time
            self._log_interaction(query, response, duration)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing hotel request: {str(e)}")
            return {
                "agent": self.agent_name,
                "error": str(e),
                "query": query
            }
    
    def _parse_hotel_query(self, query: str) -> Dict[str, Any]:
        """Parse query for hotel search parameters"""
        params = {
            "destination": "Tokyo",
            "check_in": "2025-10-15",
            "check_out": "2025-10-22",
            "guests": 2,
            "rooms": 1
        }
        
        # Extract parameters from query
        if "tokyo" in query.lower():
            params["destination"] = "Tokyo"
        if "luxury" in query.lower():
            params["category"] = "luxury"
        if "budget" in query.lower():
            params["category"] = "budget"
            
        return params
    
    def _search_hotels(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Mock hotel search"""
        mock_hotels = [
            {
                "hotel_id": "HTL001",
                "name": "Park Hyatt Tokyo",
                "location": "Shinjuku",
                "rating": 5,
                "price_per_night": 450,
                "currency": "USD",
                "amenities": ["WiFi", "Pool", "Spa", "Restaurant"],
                "distance_to_center": "2.1 km"
            },
            {
                "hotel_id": "HTL002",
                "name": "Shibuya Excel Hotel",
                "location": "Shibuya",
                "rating": 4,
                "price_per_night": 280,
                "currency": "USD",
                "amenities": ["WiFi", "Restaurant", "Business Center"],
                "distance_to_center": "1.8 km"
            }
        ]
        
        return mock_hotels
