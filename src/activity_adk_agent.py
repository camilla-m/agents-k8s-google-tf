"""
Google ADK Activity Agent
Specialized agent for activity and experience recommendations using Vertex AI and Gemini
"""

from src.adk_base_agent import ADKBaseAgent
from vertexai.generative_models import Tool, FunctionDeclaration
from typing import Dict, Any, List

class ActivityADKAgent(ADKBaseAgent):
    """Google ADK Agent for activity and experience recommendations using Gemini + Tools"""
    
    def __init__(self, project_id: str = None):
        super().__init__("activity-adk-agent", "activity_experience_recommendations", project_id)
        
    def _get_system_instruction(self) -> str:
        """System instruction for activity agent"""
        return """You are a specialized travel activity and experience assistant powered by Google ADK.

        Your expertise includes:
        - Local activity and attraction recommendations
        - Cultural experience curation based on interests
        - Restaurant and dining recommendations
        - Entertainment and nightlife suggestions
        - Outdoor activities and adventure planning
        - Museum, gallery, and cultural site information
        - Local events and seasonal activities
        - Budget-friendly to luxury experience options

        Always provide detailed activity descriptions, practical information like hours and prices,
        and personalized recommendations based on user preferences and travel style.
        Use available tools to search for real activity data and current information.
        """
    
    def _define_tools(self) -> List[Tool]:
        """Define activity-related tools for Gemini"""
        return [
            Tool(
                function_declarations=[
                    FunctionDeclaration(
                        name="search_activities",
                        description="Search for activities and attractions in a location",
                        parameters={
                            "type": "object",
                            "properties": {
                                "destination": {
                                    "type": "string",
                                    "description": "City or location name"
                                },
                                "categories": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Activity categories: cultural, food, outdoor, entertainment, shopping, museums, nightlife"
                                },
                                "budget_level": {
                                    "type": "string",
                                    "description": "Budget level: budget, mid-range, luxury",
                                    "default": "mid-range"
                                },
                                "duration": {
                                    "type": "string",
                                    "description": "Activity duration: short (1-2h), medium (3-4h), long (full day)"
                                },
                                "group_size": {
                                    "type": "integer",
                                    "description": "Number of people",
                                    "default": 2
                                }
                            },
                            "required": ["destination"]
                        }
                    ),
                    FunctionDeclaration(
                        name="get_restaurant_recommendations",
                        description="Get restaurant recommendations for a specific cuisine or area",
                        parameters={
                            "type": "object",
                            "properties": {
                                "destination": {
                                    "type": "string",
                                    "description": "City or neighborhood"
                                },
                                "cuisine_type": {
                                    "type": "string", 
                                    "description": "Cuisine type (Japanese, Italian, etc.) or 'local'"
                                },
                                "price_range": {
                                    "type": "string",
                                    "description": "Price range: budget, moderate, upscale, fine-dining"
                                },
                                "dining_style": {
                                    "type": "string",
                                    "description": "Dining style: casual, romantic, family, business"
                                }
                            },
                            "required": ["destination", "cuisine_type"]
                        }
                    ),
                    FunctionDeclaration(
                        name="check_activity_availability",
                        description="Check availability and booking requirements for an activity",
                        parameters={
                            "type": "object",
                            "properties": {
                                "activity_id": {
                                    "type": "string",
                                    "description": "Activity ID from search results"
                                },
                                "date": {
                                    "type": "string",
                                    "description": "Date in YYYY-MM-DD format"
                                },
                                "time": {
                                    "type": "string",
                                    "description": "Preferred time (morning, afternoon, evening)"
                                }
                            },
                            "required": ["activity_id", "date"]
                        }
                    )
                ]
            )
        ]
    
    def _tool_search_activities(self, destination: str, categories: List[str] = None,
                               budget_level: str = "mid-range", duration: str = None,
                               group_size: int = 2) -> Dict[str, Any]:
        """Tool function: Search for activities"""
        self.logger.info(f"ADK Tool: Searching activities in {destination} for categories: {categories}")
        
        # Mock activity data - in production, integrate with activity APIs (GetYourGuide, Viator, etc.)
        all_activities = [
            {
                "activity_id": "ACT_001",
                "name": "Senso-ji Temple & Asakusa Walking Tour",
                "category": "cultural",
                "description": "Explore Tokyo's oldest temple and traditional Asakusa district with a local guide",
                "duration": "3 hours",
                "price": 45,
                "currency": "USD",
                "budget_level": "budget",
                "rating": 4.7,
                "review_count": 1250,
                "location": "Asakusa, Tokyo",
                "highlights": ["Historic Buddhist temple", "Traditional shopping street", "Local food tasting"],
                "includes": ["English-speaking guide", "Temple entrance", "Food samples"],
                "meeting_point": "Asakusa Station Exit 1",
                "availability": ["09:00", "14:00"],
                "booking_required": True
            },
            {
                "activity_id": "ACT_002",
                "name": "Sushi Making Workshop with Master Chef",
                "category": "food",
                "description": "Learn authentic sushi making techniques from a master chef in Tokyo",
                "duration": "2.5 hours", 
                "price": 120,
                "currency": "USD",
                "budget_level": "mid-range",
                "rating": 4.9,
                "review_count": 890,
                "location": "Ginza, Tokyo",
                "highlights": ["Hands-on sushi making", "Fresh fish selection", "Take home recipes"],
                "includes": ["All ingredients", "Chef instruction", "Sake tasting", "Certificate"],
                "meeting_point": "Ginza Cooking Studio",
                "availability": ["10:30", "15:30", "18:00"],
                "booking_required": True
            },
            {
                "activity_id": "ACT_003", 
                "name": "Tokyo Skytree Fast-Track Ticket",
                "category": "sightseeing",
                "description": "Skip-the-line access to Tokyo's tallest tower with panoramic city views",
                "duration": "1.5 hours",
                "price": 28,
                "currency": "USD",
                "budget_level": "budget",
                "rating": 4.5,
                "review_count": 3200,
                "location": "Tokyo Skytree Town",
                "highlights": ["360° city views", "Fast-track entry", "Two observation decks"],
                "includes": ["Admission to 350m deck", "Fast-track access"],
                "meeting_point": "Tokyo Skytree entrance",
                "availability": ["09:00-21:00"],
                "booking_required": False
            },
            {
                "activity_id": "ACT_004",
                "name": "Private Geisha District Evening Tour",
                "category": "cultural",
                "description": "Exclusive evening tour of Gion district with geisha spotting and kaiseki dinner",
                "duration": "4 hours",
                "price": 350,
                "currency": "USD", 
                "budget_level": "luxury",
                "rating": 4.8,
                "review_count": 450,
                "location": "Gion, Kyoto",
                "highlights": ["Private guide", "Geisha spotting", "Traditional kaiseki dinner"],
                "includes": ["Private guide", "Kaiseki dinner", "Tea ceremony", "Transportation"],
                "meeting_point": "Gion Corner",
                "availability": ["17:00"],
                "booking_required": True
            },
            {
                "activity_id": "ACT_005",
                "name": "Shibuya Food & Nightlife Crawl",
                "category": "nightlife",
                "description": "Experience Tokyo's nightlife with food stops and local bars in Shibuya",
                "duration": "4 hours",
                "price": 85,
                "currency": "USD",
                "budget_level": "mid-range", 
                "rating": 4.6,
                "review_count": 720,
                "location": "Shibuya, Tokyo",
                "highlights": ["3 food stops", "2 bars/izakaya", "Local nightlife experience"],
                "includes": ["Food tastings", "2 drinks", "English guide"],
                "meeting_point": "Shibuya Crossing",
                "availability": ["19:00"],
                "booking_required": True
            }
        ]
        
        # Filter by categories if specified
        filtered_activities = all_activities
        if categories:
            filtered_activities = [
                activity for activity in all_activities
                if activity["category"] in [cat.lower() for cat in categories]
            ]
        
        # Filter by budget level
        if budget_level != "all":
            filtered_activities = [
                activity for activity in filtered_activities
                if activity["budget_level"] == budget_level
            ]
        
        # Filter by duration if specified
        if duration:
            duration_mapping = {
                "short": ["1 hour", "1.5 hours", "2 hours"],
                "medium": ["2.5 hours", "3 hours", "3.5 hours"],
                "long": ["4 hours", "5 hours", "6 hours", "full day"]
            }
            if duration in duration_mapping:
                filtered_activities = [
                    if activity["duration"] in duration_mapping[duration]
                ]
        
        return {
            "activities": filtered_activities[:10],  # Limit results
            "search_params": {
                "destination": destination,
                "categories": categories,
                "budget_level": budget_level,
                "duration": duration,
                "group_size": group_size
            },
            "total_results": len(filtered_activities)
        }
    
    def _tool_get_restaurant_recommendations(self, destination: str, cuisine_type: str,
                                           price_range: str = "moderate", 
                                           dining_style: str = "casual") -> Dict[str, Any]:
        """Tool function: Get restaurant recommendations"""
        self.logger.info(f"ADK Tool: Searching {cuisine_type} restaurants in {destination}")
        
        # Mock restaurant data
        mock_restaurants = [
            {
                "restaurant_id": "REST_001",
                "name": "Sukiyabashi Jiro Honten",
                "cuisine": "Japanese",
                "specialty": "Sushi",
                "price_range": "fine-dining",
                "rating": 4.9,
                "michelin_stars": 3,
                "location": "Ginza, Tokyo",
                "average_cost": 400,
                "currency": "USD",
                "dining_style": "fine-dining",
                "description": "World-renowned sushi restaurant by master chef Jiro Ono",
                "highlights": ["Omakase only", "Counter seating", "Michelin 3-star"],
                "reservation_required": True,
                "dress_code": "Smart casual"
            },
            {
                "restaurant_id": "REST_002", 
                "name": "Ichiran Ramen Shibuya",
                "cuisine": "Japanese",
                "specialty": "Ramen",
                "price_range": "budget",
                "rating": 4.2,
                "location": "Shibuya, Tokyo",
                "average_cost": 12,
                "currency": "USD",
                "dining_style": "casual",
                "description": "Famous tonkotsu ramen chain with individual booth seating",
                "highlights": ["24/7 operation", "Individual booths", "Customizable ramen"],
                "reservation_required": False,
                "dress_code": "Casual"
            },
            {
                "restaurant_id": "REST_003",
                "name": "Kikunoi Honten",
                "cuisine": "Japanese", 
                "specialty": "Kaiseki",
                "price_range": "fine-dining",
                "rating": 4.8,
                "michelin_stars": 3,
                "location": "Higashiyama, Kyoto",
                "average_cost": 350,
                "currency": "USD",
                "dining_style": "fine-dining",
                "description": "Traditional kaiseki restaurant in historic Kyoto setting",
                "highlights": ["Seasonal kaiseki", "Garden views", "400+ year history"],
                "reservation_required": True,
                "dress_code": "Formal"
            }
        ]
        
        # Filter by cuisine and price range
        filtered_restaurants = [
            r for r in mock_restaurants
            if (cuisine_type.lower() == "local" or cuisine_type.lower() in r["cuisine"].lower())
            and (price_range == "all" or r["price_range"] == price_range)
            and (dining_style == "all" or r["dining_style"] == dining_style)
        ]
        
        return {
            "restaurants": filtered_restaurants,
            "search_params": {
                "destination": destination,
                "cuisine_type": cuisine_type,
                "price_range": price_range,
                "dining_style": dining_style
            },
            "total_results": len(filtered_restaurants)
        }
    
    def _tool_check_activity_availability(self, activity_id: str, date: str, 
                                        time: str = None) -> Dict[str, Any]:
        """Tool function: Check activity availability"""
        # Mock availability data
        return {
            "activity_id": activity_id,
            "date": date,
            "available": True,
            "available_times": ["09:00", "14:00", "17:00"],
            "spots_remaining": 8,
            "booking_deadline": "24 hours in advance",
            "cancellation_policy": "Free cancellation up to 48 hours before"
        }