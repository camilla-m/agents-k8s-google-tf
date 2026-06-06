"""
Google ADK Flight Agent
Specialized agent for flight search and booking using Vertex AI and Gemini
"""

from src.adk_base_agent import ADKBaseAgent
from vertexai.generative_models import Tool, FunctionDeclaration
import requests
import json
from typing import Dict, Any, List, Optional

class FlightADKAgent(ADKBaseAgent):
    """Google ADK Agent specialized for flight search and booking using Gemini + Tools"""
    
    def __init__(self, project_id: str = None):
        super().__init__("flight-adk-agent", "flight_search_booking_assistance", project_id)
        
    def _get_system_instruction(self) -> str:
        """System instruction for flight agent"""
        return """You are a specialized flight booking assistant powered by Google ADK.
        
        Your expertise includes:
        - Flight search across multiple airlines
        - Price comparison and recommendations
        - Travel date optimization
        - Route planning and connections
        - Booking assistance and modifications
        
        Always be helpful, accurate, and provide detailed flight information.
        Use the available tools to search for real flight data when users make requests.
        Format prices clearly and explain any restrictions or fees.
        """
    
    def _define_tools(self) -> List[Tool]:
        """Define flight-related tools for Gemini"""
        return [
            Tool(
                function_declarations=[
                    FunctionDeclaration(
                        name="search_flights",
                        description="Search for flights between two locations",
                        parameters={
                            "type": "object",
                            "properties": {
                                "origin": {
                                    "type": "string",
                                    "description": "Origin airport code (e.g. SFO, LAX)"
                                },
                                "destination": {
                                    "type": "string", 
                                    "description": "Destination airport code (e.g. NRT, LHR)"
                                },
                                "departure_date": {
                                    "type": "string",
                                    "description": "Departure date in YYYY-MM-DD format"
                                },
                                "return_date": {
                                    "type": "string",
                                    "description": "Return date in YYYY-MM-DD format (optional)"
                                },
                                "passengers": {
                                    "type": "integer",
                                    "description": "Number of passengers",
                                    "default": 1
                                },
                                "class": {
                                    "type": "string",
                                    "description": "Travel class: economy, business, first",
                                    "default": "economy"
                                }
                            },
                            "required": ["origin", "destination", "departure_date"]
                        }
                    ),
                    FunctionDeclaration(
                        name="get_airport_info",
                        description="Get information about an airport",
                        parameters={
                            "type": "object",
                            "properties": {
                                "airport_code": {
                                    "type": "string",
                                    "description": "3-letter airport code (e.g. SFO)"
                                }
                            },
                            "required": ["airport_code"]
                        }
                    ),
                    FunctionDeclaration(
                        name="check_flight_status",
                        description="Check the status of a specific flight",
                        parameters={
                            "type": "object", 
                            "properties": {
                                "flight_number": {
                                    "type": "string",
                                    "description": "Flight number (e.g. AA123, UA456)"
                                },
                                "date": {
                                    "type": "string",
                                    "description": "Flight date in YYYY-MM-DD format"
                                }
                            },
                            "required": ["flight_number", "date"]
                        }
                    )
                ]
            )
        ]
    
    def _tool_search_flights(self, origin: str, destination: str, departure_date: str, 
                           return_date: str = None, passengers: int = 1, 
                           travel_class: str = "economy") -> Dict[str, Any]:
        """Tool function: Search for flights"""
        self.logger.info(f"ADK Tool: Searching flights {origin} → {destination} on {departure_date}")
        
        # In production, integrate with real flight APIs (Amadeus, Sabre, etc.)
        # For demo, return realistic mock data
        mock_flights = [
            {
                "flight_id": "AA123",
                "airline": "American Airlines",
                "flight_number": "AA 123",
                "origin": origin,
                "destination": destination,
                "departure_time": "08:30",
                "arrival_time": "22:45",
                "duration": "14h 15m",
                "stops": 1,
                "stop_cities": ["DFW"],
                "price": 850,
                "currency": "USD",
                "class": travel_class,
                "available_seats": 12,
                "aircraft": "Boeing 787-9"
            },
            {
                "flight_id": "UA456", 
                "airline": "United Airlines",
                "flight_number": "UA 456",
                "origin": origin,
                "destination": destination,
                "departure_time": "14:20",
                "arrival_time": "05:30+1",
                "duration": "13h 10m",
                "stops": 0,
                "stop_cities": [],
                "price": 1120,
                "currency": "USD",
                "class": travel_class,
                "available_seats": 8,
                "aircraft": "Boeing 777-300ER"
            },
            {
                "flight_id": "DL789",
                "airline": "Delta Air Lines", 
                "flight_number": "DL 789",
                "origin": origin,
                "destination": destination,
                "departure_time": "23:55",
                "arrival_time": "17:20+1",
                "duration": "15h 25m",
                "stops": 1,
                "stop_cities": ["SEA"],
                "price": 780,
                "currency": "USD",
                "class": travel_class,
                "available_seats": 20,
                "aircraft": "Airbus A350-900"
            }
        ]
        
        return {
            "flights": mock_flights,
            "search_params": {
                "origin": origin,
                "destination": destination, 
                "departure_date": departure_date,
                "return_date": return_date,
                "passengers": passengers,
                "class": travel_class
            },
            "total_results": len(mock_flights)
        }
    
    def _tool_get_airport_info(self, airport_code: str) -> Dict[str, Any]:
        """Tool function: Get airport information"""
        # Mock airport data - in production, use real airport APIs
        airport_data = {
            "SFO": {
                "name": "San Francisco International Airport",
                "city": "San Francisco",
                "country": "United States", 
                "timezone": "America/Los_Angeles",
                "terminals": 4,
                "airlines": ["United", "Delta", "American", "Alaska"]
            },
            "NRT": {
                "name": "Narita International Airport",
                "city": "Tokyo",
                "country": "Japan",
                "timezone": "Asia/Tokyo", 
                "terminals": 3,
                "airlines": ["ANA", "JAL", "United", "Delta"]
            },
            "LHR": {
                "name": "London Heathrow Airport",
                "city": "London",
                "country": "United Kingdom",
                "timezone": "Europe/London",
                "terminals": 5,
                "airlines": ["British Airways", "Virgin Atlantic", "American"]
            }
        }
        
        return airport_data.get(airport_code.upper(), {
            "name": f"Airport {airport_code.upper()}",
            "city": "Unknown",
            "country": "Unknown",
            "timezone": "Unknown",
            "error": "Airport information not available"
        })
    
    def _tool_check_flight_status(self, flight_number: str, date: str) -> Dict[str, Any]:
        """Tool function: Check flight status"""
        # Mock flight status - in production, use real flight tracking APIs
        return {
            "flight_number": flight_number.upper(),
            "date": date,
            "status": "On Time",
            "departure_time": "14:30",
            "arrival_time": "22:45", 
            "gate": "A12",
            "terminal": "2",
            "delay_minutes": 0,
            "aircraft": "Boeing 787-9"
        }