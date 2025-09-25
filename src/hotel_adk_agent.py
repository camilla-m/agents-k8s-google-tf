"""
Google ADK Hotel Agent
Specialized agent for hotel search and booking using Vertex AI and Gemini
"""

from src.adk_base_agent import ADKBaseAgent
from vertexai.generative_models import Tool, FunctionDeclaration
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

class HotelADKAgent(ADKBaseAgent):
    """Google ADK Agent for hotel search and booking using Gemini + Tools"""
    
    def __init__(self, project_id: str = None):
        super().__init__("hotel-adk-agent", "hotel_accommodation_assistance", project_id)
        
    def _get_system_instruction(self) -> str:
        """System instruction for hotel agent"""
        return """You are a specialized hotel booking assistant powered by Google ADK and Vertex AI.

        Your expertise includes:
        - Hotel search and availability checking across multiple platforms
        - Price comparison and value analysis
        - Room type recommendations based on guest needs and preferences
        - Location analysis and neighborhood insights for travelers
        - Amenity matching and special accommodation requests
        - Booking assistance, modifications, and cancellation policies
        - Local area information and transportation access
        
        Always provide detailed hotel information including:
        - Amenities and facilities available
        - Location benefits and nearby attractions
        - Honest assessment based on guest reviews
        - Clear pricing information with any additional fees
        - Booking terms and cancellation policies
        
        Use your available tools to search for real hotel data and current pricing.
        Help users make informed decisions based on their budget, preferences, and travel style.
        Be proactive in suggesting alternatives if their initial requirements are too restrictive.
        """
    
    def _define_tools(self) -> List[Tool]:
        """Define hotel-related tools for Gemini"""
        return [
            Tool(
                function_declarations=[
                    FunctionDeclaration(
                        name="search_hotels",
                        description="Search for hotels in a specific location with filters",
                        parameters={
                            "type": "object",
                            "properties": {
                                "destination": {
                                    "type": "string",
                                    "description": "City, neighborhood, or location name (e.g. 'Tokyo', 'Manhattan NYC', 'Shibuya Tokyo')"
                                },
                                "check_in": {
                                    "type": "string", 
                                    "description": "Check-in date in YYYY-MM-DD format"
                                },
                                "check_out": {
                                    "type": "string",
                                    "description": "Check-out date in YYYY-MM-DD format"
                                },
                                "guests": {
                                    "type": "integer",
                                    "description": "Number of guests",
                                    "default": 2
                                },
                                "rooms": {
                                    "type": "integer", 
                                    "description": "Number of rooms needed",
                                    "default": 1
                                },
                                "budget_max": {
                                    "type": "number",
                                    "description": "Maximum price per night in USD"
                                },
                                "budget_min": {
                                    "type": "number",
                                    "description": "Minimum price per night in USD (for quality filtering)"
                                },
                                "star_rating": {
                                    "type": "integer",
                                    "description": "Minimum star rating (1-5)"
                                },
                                "amenities": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Desired amenities: pool, gym, spa, wifi, restaurant, bar, parking, pet-friendly, business-center"
                                },
                                "hotel_type": {
                                    "type": "string",
                                    "description": "Hotel type preference: luxury, business, boutique, budget, resort, traditional"
                                }
                            },
                            "required": ["destination", "check_in", "check_out"]
                        }
                    ),
                    FunctionDeclaration(
                        name="get_hotel_details",
                        description="Get comprehensive information about a specific hotel",
                        parameters={
                            "type": "object",
                            "properties": {
                                "hotel_id": {
                                    "type": "string",
                                    "description": "Hotel ID from search results"
                                }
                            },
                            "required": ["hotel_id"]
                        }
                    ),
                    FunctionDeclaration(
                        name="check_availability",
                        description="Check detailed room availability and pricing for specific dates",
                        parameters={
                            "type": "object",
                            "properties": {
                                "hotel_id": {
                                    "type": "string",
                                    "description": "Hotel ID"
                                },
                                "check_in": {
                                    "type": "string",
                                    "description": "Check-in date YYYY-MM-DD"
                                },
                                "check_out": {
                                    "type": "string",
                                    "description": "Check-out date YYYY-MM-DD"
                                },
                                "rooms": {
                                    "type": "integer",
                                    "description": "Number of rooms",
                                    "default": 1
                                },
                                "guests": {
                                    "type": "integer",
                                    "description": "Number of guests",
                                    "default": 2
                                }
                            },
                            "required": ["hotel_id", "check_in", "check_out"]
                        }
                    ),
                    FunctionDeclaration(
                        name="get_area_info",
                        description="Get information about a hotel's location and nearby attractions",
                        parameters={
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "Location or neighborhood name"
                                },
                                "interests": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Types of nearby attractions: restaurants, shopping, museums, nightlife, business, transportation"
                                }
                            },
                            "required": ["location"]
                        }
                    )
                ]
            )
        ]
    
    def _tool_search_hotels(self, destination: str, check_in: str, check_out: str,
                           guests: int = 2, rooms: int = 1, budget_max: float = None,
                           budget_min: float = None, star_rating: int = None,
                           amenities: List[str] = None, hotel_type: str = None) -> Dict[str, Any]:
        """Tool function: Search for hotels with comprehensive filtering"""
        self.logger.info(f"ADK Tool: Searching hotels in {destination} for {check_in} to {check_out}")
        
        # Calculate number of nights
        nights = self._calculate_nights(check_in, check_out)
        
        # Mock hotel data - in production, integrate with hotel APIs (Booking.com, Expedia, etc.)
        all_hotels = [
            {
                "hotel_id": "HTL_001",
                "name": "Park Hyatt Tokyo",
                "brand": "Hyatt",
                "category": "luxury",
                "star_rating": 5,
                "guest_rating": 4.8,
                "review_count": 2847,
                "location": {
                    "address": "3-7-1-2 Nishi-Shinjuku, Shinjuku City, Tokyo 163-1055",
                    "district": "Shinjuku",
                    "coordinates": {"lat": 35.6885, "lng": 139.6917},
                    "distance_to_center": "2.1 km",
                    "nearest_station": "Shinjuku Station (5 min walk)",
                    "airport_distance": "60 min to Narita"
                },
                "price_per_night": 450,
                "currency": "USD",
                "total_price": 450 * nights,
                "amenities": ["WiFi", "Indoor Pool", "Spa", "Fitness Center", "Restaurant", "Bar", "Concierge", "Room Service", "Valet Parking"],
                "room_types": ["Deluxe King", "Deluxe Twin", "Park Suite", "Presidential Suite"],
                "images": [
                    "https://example.com/park-hyatt-exterior.jpg",
                    "https://example.com/park-hyatt-room.jpg",
                    "https://example.com/park-hyatt-view.jpg"
                ],
                "highlights": ["Panoramic city views", "Michelin-starred dining", "Premium location in Shinjuku"],
                "cancellation": "Free cancellation until 48h before check-in",
                "booking_conditions": "Prepayment required",
                "special_offers": ["Spa package available", "Extended stay discounts"]
            },
            {
                "hotel_id": "HTL_002", 
                "name": "Shibuya Excel Hotel Tokyu",
                "brand": "Tokyu Hotels",
                "category": "business",
                "star_rating": 4,
                "guest_rating": 4.2,
                "review_count": 1563,
                "location": {
                    "address": "1-12-2 Dogenzaka, Shibuya City, Tokyo 150-0043",
                    "district": "Shibuya", 
                    "coordinates": {"lat": 35.6598, "lng": 139.7006},
                    "distance_to_center": "1.8 km",
                    "nearest_station": "Shibuya Station (3 min walk)",
                    "airport_distance": "45 min to Haneda"
                },
                "price_per_night": 180,
                "currency": "USD",
                "total_price": 180 * nights,
                "amenities": ["WiFi", "Restaurant", "Business Center", "Laundry", "24h Front Desk", "Currency Exchange"],
                "room_types": ["Standard Single", "Superior Double", "Executive Twin"],
                "images": [
                    "https://example.com/excel-hotel-exterior.jpg",
                    "https://example.com/excel-hotel-room.jpg"
                ],
                "highlights": ["Prime Shibuya location", "Business traveler focused", "Direct station access"],
                "cancellation": "Free cancellation until 24h before check-in",
                "booking_conditions": "Pay at hotel",
                "special_offers": ["Business package with meeting room access"]
            },
            {
                "hotel_id": "HTL_003",
                "name": "The Prince Sakura Tower Tokyo",
                "brand": "Prince Hotels",
                "category": "luxury",
                "star_rating": 5,
                "guest_rating": 4.6,
                "review_count": 892,
                "location": {
                    "address": "3-13-1 Takanawa, Minato City, Tokyo 108-8612",
                    "district": "Shinagawa/Takanawa",
                    "coordinates": {"lat": 35.6384, "lng": 139.7388},
                    "distance_to_center": "4.2 km",
                    "nearest_station": "Shinagawa Station (5 min walk)",
                    "airport_distance": "30 min to Haneda"
                },
                "price_per_night": 320,
                "currency": "USD",
                "total_price": 320 * nights,
                "amenities": ["WiFi", "Indoor Pool", "Spa", "Multiple Restaurants", "Bar", "Fitness Center", "Garden", "Business Center"],
                "room_types": ["Deluxe Room", "Executive Floor", "Tower Suite"],
                "images": [
                    "https://example.com/prince-sakura-exterior.jpg",
                    "https://example.com/prince-sakura-room.jpg",
                    "https://example.com/prince-sakura-garden.jpg"
                ],
                "highlights": ["Traditional Japanese garden", "Multiple dining options", "Convenient to train stations"],
                "cancellation": "Free cancellation until 72h before check-in",
                "booking_conditions": "Flexible payment options",
                "special_offers": ["Garden view upgrade available", "Seasonal dining packages"]
            },
            {
                "hotel_id": "HTL_004",
                "name": "Capsule Hotel Anshin Oyado",
                "brand": "Independent",
                "category": "budget",
                "star_rating": 2,
                "guest_rating": 3.9,
                "review_count": 567,
                "location": {
                    "address": "3-17-5 Shimbashi, Minato City, Tokyo 105-0004",
                    "district": "Shimbashi",
                    "coordinates": {"lat": 35.6657, "lng": 139.7564},
                    "distance_to_center": "3.2 km",
                    "nearest_station": "Shimbashi Station (2 min walk)",
                    "airport_distance": "35 min to Haneda"
                },
                "price_per_night": 45,
                "currency": "USD", 
                "total_price": 45 * nights,
                "amenities": ["WiFi", "Shared Bath", "Locker", "Vending Machines", "Laundry"],
                "room_types": ["Standard Capsule", "Women-only Capsule"],
                "images": [
                    "https://example.com/capsule-hotel-pods.jpg",
                    "https://example.com/capsule-hotel-lounge.jpg"
                ],
                "highlights": ["Authentic Japanese capsule experience", "Budget-friendly", "Great location"],
                "cancellation": "No free cancellation",
                "booking_conditions": "Payment in advance",
                "special_offers": ["Extended stay discounts for 3+ nights"]
            }
        ]
        
        # Apply filters
        filtered_hotels = all_hotels.copy()
        
        # Filter by budget
        if budget_max:
            filtered_hotels = [h for h in filtered_hotels if h["price_per_night"] <= budget_max]
        if budget_min:
            filtered_hotels = [h for h in filtered_hotels if h["price_per_night"] >= budget_min]
        
        # Filter by star rating
        if star_rating:
            filtered_hotels = [h for h in filtered_hotels if h["star_rating"] >= star_rating]
        
        # Filter by hotel type
        if hotel_type:
            filtered_hotels = [h for h in filtered_hotels if h["category"] == hotel_type]
        
        # Filter by amenities
        if amenities:
            filtered_hotels = [
                hotel for hotel in filtered_hotels
                if any(amenity.lower() in [a.lower() for a in hotel["amenities"]] for amenity in amenities)
            ]
        
        # Sort by guest rating (highest first)
        filtered_hotels.sort(key=lambda x: x["guest_rating"], reverse=True)
        
        return {
            "hotels": filtered_hotels,
            "search_params": {
                "destination": destination,
                "check_in": check_in,
                "check_out": check_out,
                "nights": nights,
                "guests": guests,
                "rooms": rooms,
                "budget_max": budget_max,
                "budget_min": budget_min,
                "star_rating": star_rating,
                "amenities": amenities,
                "hotel_type": hotel_type
            },
            "total_results": len(filtered_hotels),
            "search_timestamp": datetime.now().isoformat()
        }
    
    def _tool_get_hotel_details(self, hotel_id: str) -> Dict[str, Any]:
        """Tool function: Get comprehensive hotel information"""
        self.logger.info(f"ADK Tool: Getting details for hotel {hotel_id}")
        
        # Mock detailed hotel data - in production, fetch from hotel APIs
        hotel_details = {
            "HTL_001": {
                "detailed_description": "Park Hyatt Tokyo stands as an architectural masterpiece in the heart of Shinjuku, offering unparalleled luxury with panoramic views of Tokyo. The hotel seamlessly blends contemporary design with traditional Japanese aesthetics.",
                "detailed_amenities": {
                    "room_features": ["Floor-to-ceiling windows", "Marble bathroom", "Rain shower", "Premium toiletries", "Mini bar", "Safe", "Air conditioning", "Blackout curtains"],
                    "hotel_facilities": ["24-hour front desk", "Multilingual staff", "Currency exchange", "Luggage storage", "Babysitting services", "Laundry/dry cleaning"],
                    "dining": ["New York Grill (52nd floor)", "Girandole (French cuisine)", "Kozasa (Japanese)", "Peak Bar", "24-hour room service"],
                    "wellness": ["Club on the Park Spa", "Indoor swimming pool", "Fitness center", "Massage treatments", "Sauna"]
                },
                "room_details": {
                    "Deluxe King": {"size": "45 sqm", "bed": "King bed", "view": "City view", "max_occupancy": 2},
                    "Deluxe Twin": {"size": "45 sqm", "bed": "Twin beds", "view": "City view", "max_occupancy": 2},
                    "Park Suite": {"size": "80 sqm", "bed": "King bed", "view": "Premium city view", "max_occupancy": 3},
                    "Presidential Suite": {"size": "290 sqm", "bed": "King bed", "view": "360° city view", "max_occupancy": 4}
                },
                "policies": {
                    "check_in": "15:00",
                    "check_out": "12:00",
                    "late_checkout": "Available until 18:00 for additional fee",
                    "pets": "Not allowed",
                    "smoking": "Non-smoking hotel",
                    "children": "Children welcome, cribs available",
                    "extra_beds": "Available for additional fee"
                },
                "reviews_summary": {
                    "total_reviews": 2847,
                    "rating_breakdown": {"5_star": 68, "4_star": 23, "3_star": 7, "2_star": 1, "1_star": 1},
                    "top_mentions": ["Excellent service", "Amazing views", "Great location", "Outstanding dining", "Luxurious rooms"],
                    "recent_highlights": ["Staff went above and beyond", "Best views in Tokyo", "Perfect for special occasions"]
                },
                "nearby_attractions": [
                    {"name": "Tokyo Metropolitan Government Building", "distance": "5 min walk", "type": "landmark"},
                    {"name": "Shinjuku Park", "distance": "10 min walk", "type": "park"},
                    {"name": "Robot Restaurant", "distance": "8 min walk", "type": "entertainment"},
                    {"name": "Golden Gai", "distance": "12 min walk", "type": "nightlife"}
                ]
            },
            "HTL_002": {
                "detailed_description": "Shibuya Excel Hotel Tokyu offers prime access to Tokyo's most vibrant district. Perfect for business and leisure travelers who want to be at the center of Tokyo's energy.",
                "detailed_amenities": {
                    "room_features": ["City views", "Work desk", "High-speed internet", "Air conditioning", "Minibar", "Safe"],
                    "hotel_facilities": ["Business center", "Meeting rooms", "Currency exchange", "Luggage storage", "Laundry service"],
                    "dining": ["Estação Restaurant", "Sky Lounge", "Café & Deli"],
                    "wellness": ["Fitness facilities"]
                },
                "room_details": {
                    "Standard Single": {"size": "18 sqm", "bed": "Single bed", "view": "City view", "max_occupancy": 1},
                    "Superior Double": {"size": "24 sqm", "bed": "Double bed", "view": "Shibuya view", "max_occupancy": 2},
                    "Executive Twin": {"size": "28 sqm", "bed": "Twin beds", "view": "Premium Shibuya view", "max_occupancy": 2}
                },
                "policies": {
                    "check_in": "14:00",
                    "check_out": "11:00",
                    "pets": "Not allowed",
                    "smoking": "Smoking rooms available"
                },
                "reviews_summary": {
                    "total_reviews": 1563,
                    "rating_breakdown": {"5_star": 45, "4_star": 35, "3_star": 15, "2_star": 4, "1_star": 1},
                    "top_mentions": ["Perfect location", "Good value", "Clean rooms", "Helpful staff"]
                }
            }
        }
        
        return hotel_details.get(hotel_id, {"error": "Hotel details not found"})
    
    def _tool_check_availability(self, hotel_id: str, check_in: str, check_out: str, 
                                rooms: int = 1, guests: int = 2) -> Dict[str, Any]:
        """Tool function: Check detailed room availability and pricing"""
        self.logger.info(f"ADK Tool: Checking availability for {hotel_id} from {check_in} to {check_out}")
        
        nights = self._calculate_nights(check_in, check_out)
        
        # Mock availability data - in production, check real inventory
        availability_data = {
            "HTL_001": {
                "available": True,
                "room_types": [
                    {
                        "type": "Deluxe King",
                        "available_rooms": 3,
                        "price_per_night": 450,
                        "total_price": 450 * nights,
                        "includes": ["Breakfast", "WiFi", "Gym access"],
                        "cancellation": "Free until 48h before"
                    },
                    {
                        "type": "Deluxe Twin", 
                        "available_rooms": 2,
                        "price_per_night": 450,
                        "total_price": 450 * nights,
                        "includes": ["Breakfast", "WiFi", "Gym access"],
                        "cancellation": "Free until 48h before"
                    },
                    {
                        "type": "Park Suite",
                        "available_rooms": 1,
                        "price_per_night": 850,
                        "total_price": 850 * nights,
                        "includes": ["Breakfast", "WiFi", "Gym access", "Executive lounge", "Late checkout"],
                        "cancellation": "Free until 72h before"
                    }
                ]
            },
            "HTL_002": {
                "available": True,
                "room_types": [
                    {
                        "type": "Standard Single",
                        "available_rooms": 5,
                        "price_per_night": 140,
                        "total_price": 140 * nights,
                        "includes": ["WiFi"],
                        "cancellation": "Free until 24h before"
                    },
                    {
                        "type": "Superior Double",
                        "available_rooms": 8,
                        "price_per_night": 180,
                        "total_price": 180 * nights,
                        "includes": ["WiFi", "City view"],
                        "cancellation": "Free until 24h before"
                    }
                ]
            }
        }
        
        base_data = availability_data.get(hotel_id, {"available": False, "reason": "Hotel not found"})
        
        return {
            **base_data,
            "hotel_id": hotel_id,
            "check_in": check_in,
            "check_out": check_out,
            "nights": nights,
            "rooms_requested": rooms,
            "guests": guests,
            "search_date": datetime.now().isoformat()
        }
    
    def _tool_get_area_info(self, location: str, interests: List[str] = None) -> Dict[str, Any]:
        """Tool function: Get area information and nearby attractions"""
        self.logger.info(f"ADK Tool: Getting area info for {location}")
        
        # Mock area data - in production, integrate with local APIs
        area_data = {
            "shinjuku": {
                "description": "Tokyo's bustling business district and entertainment hub with skyscrapers, shopping, and nightlife",
                "transportation": {
                    "major_stations": ["Shinjuku Station (JR, Metro, Private lines)", "Shinjuku-sanchome Station"],
                    "airport_access": "60 min to Narita, 45 min to Haneda",
                    "subway_lines": ["JR Yamanote Line", "Marunouchi Line", "Shinjuku Line"]
                },
                "attractions": {
                    "shopping": ["Takashimaya Times Square", "Lumine", "Don Quijote", "Department stores"],
                    "dining": ["Golden Gai (400+ tiny bars)", "Kabukicho restaurants", "Memory Lane (Omoide Yokocho)"],
                    "entertainment": ["Robot Restaurant", "Karaoke boxes", "Pachinko parlors"],
                    "culture": ["Tokyo Metropolitan Government Building observatory", "Hanazono Shrine"]
                },
                "safety": "Very safe area, well-lit at night, heavy police presence",
                "best_for": ["Business travelers", "Nightlife enthusiasts", "Shopping lovers", "First-time visitors"]
            },
            "shibuya": {
                "description": "Youth culture center famous for the world's busiest pedestrian crossing and trendy shopping",
                "transportation": {
                    "major_stations": ["Shibuya Station (JR, Metro lines)"],
                    "airport_access": "45 min to Haneda, 75 min to Narita",
                    "subway_lines": ["JR Yamanote Line", "Ginza Line", "Hanzomon Line"]
                },
                "attractions": {
                    "shopping": ["Shibuya 109", "Center Gai", "Shibuya Sky", "Hachiko Square"],
                    "dining": ["Shibuya food shows", "Themed cafes", "International cuisine"],
                    "entertainment": ["Clubs and bars", "Karaoke", "Gaming centers"],
                    "culture": ["Hachiko Statue", "Meiji Shrine (15 min walk)", "Yoyogi Park"]
                },
                "safety": "Safe but very crowded, especially evenings and weekends",
                "best_for": ["Young travelers", "Pop culture fans", "Shopping enthusiasts", "Nightlife"]
            }
        }
        
        location_key = location.lower().replace(" ", "").replace("tokyo", "")
        area_info = area_data.get(location_key, {
            "description": f"Information for {location} area",
            "note": "Detailed information not available for this specific location"
        })
        
        # Filter by interests if provided
        if interests and "attractions" in area_info:
            filtered_attractions = {}
            for interest in interests:
                if interest in area_info["attractions"]:
                    filtered_attractions[interest] = area_info["attractions"][interest]
            area_info["filtered_attractions"] = filtered_attractions
        
        return {
            "location": location,
            "area_info": area_info,
            "interests_filter": interests
        }
    
    def _calculate_nights(self, check_in: str, check_out: str) -> int:
        """Calculate number of nights between dates"""
        try:
            in_date = datetime.strptime(check_in, "%Y-%m-%d")
            out_date = datetime.strptime(check_out, "%Y-%m-%d")
            nights = (out_date - in_date).days
            return max(1, nights)  # Minimum 1 night
        except ValueError:
            self.logger.warning(f"Invalid date format: {check_in} or {check_out}")
            return 1