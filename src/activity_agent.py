# ====================================
# File: src/activity_agent.py
# ====================================
from src.base_agent import BaseAgent
import time
from typing import Dict, Any, Optional, List

class ActivityAgent(BaseAgent):
    """Specialized agent for activity and experience recommendations"""
    
    def __init__(self):
        super().__init__("activity-agent", "activity_recommendations")
        
    def process_request(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process activity recommendation requests"""
        start_time = time.time()
        
        try:
            # Parse query for activity preferences
            activity_params = self._parse_activity_query(query)
            
            # Get recommendations
            activities = self._get_activities(activity_params)
            
            # Format response
            response = {
                "agent": self.agent_name,
                "type": "activity_recommendations",
                "query": query,
                "results": activities,
                "context": context or {}
            }
            
            duration = time.time() - start_time
            self._log_interaction(query, response, duration)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing activity request: {str(e)}")
            return {
                "agent": self.agent_name,
                "error": str(e),
                "query": query
            }
    
    def _parse_activity_query(self, query: str) -> Dict[str, Any]:
        """Parse query for activity preferences"""
        params = {
            "destination": "Tokyo",
            "duration": 3,  # days
            "interests": []
        }
        
        # Extract interests from query
        interests_map = {
            "temple": "cultural",
            "museum": "cultural",
            "sushi": "food",
            "shopping": "shopping",
            "nightlife": "entertainment",
            "nature": "outdoor"
        }
        
        for keyword, category in interests_map.items():
            if keyword in query.lower():
                params["interests"].append(category)
                
        return params
    
    def _get_activities(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Mock activity recommendations"""
        all_activities = [
            {
                "activity_id": "ACT001",
                "name": "Senso-ji Temple Visit",
                "category": "cultural",
                "duration": "2 hours",
                "price": 0,
                "rating": 4.7,
                "description": "Historic Buddhist temple in Asakusa"
            },
            {
                "activity_id": "ACT002",
                "name": "Sushi Making Workshop",
                "category": "food",
                "duration": "3 hours",
                "price": 85,
                "rating": 4.9,
                "description": "Learn to make authentic sushi with master chef"
            },
            {
                "activity_id": "ACT003",
                "name": "Tokyo Skytree Observatory",
                "category": "sightseeing",
                "duration": "1.5 hours",
                "price": 25,
                "rating": 4.5,
                "description": "Panoramic views from 634m tower"
            },
            {
                "activity_id": "ACT004",
                "name": "Shibuya Crossing Night Tour",
                "category": "entertainment",
                "duration": "2 hours",
                "price": 40,
                "rating": 4.6,
                "description": "Experience the world's busiest intersection"
            }
        ]
        
        # Filter by interests if specified
        if params["interests"]:
            filtered_activities = [
                activity for activity in all_activities
                if activity["category"] in params["interests"]
            ]
            return filtered_activities if filtered_activities else all_activities
        
        return all_activities