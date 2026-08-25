"""
Tool functions for the Travel ADK agents.

Plain Python functions with type hints + docstrings - google-adk's FunctionTool
introspects the signature and docstring to build the tool schema automatically, so
there is no hand-written FunctionDeclaration to keep in sync (that duplication used to
cause real bugs: the old flight search tool declared a "class" property that didn't
match the Python parameter name "travel_class", since "class" can't be a Python
keyword argument - every call that specified a travel class crashed).

All data here is mocked (no external travel APIs) - see USE_MOCK_DATA in
k8s/configmap.yaml. In production, replace the bodies with real API calls
(Amadeus/Sabre for flights, Booking.com/Expedia for hotels, GetYourGuide/Viator for
activities) but keep the signatures/docstrings, since those are the tool contract.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("adk.tools")


def _calculate_nights(check_in: str, check_out: str) -> int:
    try:
        in_date = datetime.strptime(check_in, "%Y-%m-%d")
        out_date = datetime.strptime(check_out, "%Y-%m-%d")
        return max(1, (out_date - in_date).days)
    except ValueError:
        logger.warning(f"Invalid date format: {check_in} or {check_out}")
        return 1


# --------------------------------------------------------------------------- #
# Flight tools
# --------------------------------------------------------------------------- #

def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    passengers: int = 1,
    travel_class: str = "economy",
) -> Dict[str, Any]:
    """Search for flights between two locations.

    Args:
        origin: Origin airport code (e.g. SFO, LAX).
        destination: Destination airport code (e.g. NRT, LHR).
        departure_date: Departure date in YYYY-MM-DD format.
        return_date: Return date in YYYY-MM-DD format, if round trip.
        passengers: Number of passengers.
        travel_class: Travel class - economy, business, or first.

    Returns:
        A dict with the matching flights and the search parameters used.
    """
    logger.info(f"Searching flights {origin} -> {destination} on {departure_date}")

    mock_flights = [
        {
            "flight_id": "AA123", "airline": "American Airlines", "flight_number": "AA 123",
            "origin": origin, "destination": destination, "departure_time": "08:30",
            "arrival_time": "22:45", "duration": "14h 15m", "stops": 1, "stop_cities": ["DFW"],
            "price": 850, "currency": "USD", "class": travel_class, "available_seats": 12,
            "aircraft": "Boeing 787-9",
        },
        {
            "flight_id": "UA456", "airline": "United Airlines", "flight_number": "UA 456",
            "origin": origin, "destination": destination, "departure_time": "14:20",
            "arrival_time": "05:30+1", "duration": "13h 10m", "stops": 0, "stop_cities": [],
            "price": 1120, "currency": "USD", "class": travel_class, "available_seats": 8,
            "aircraft": "Boeing 777-300ER",
        },
        {
            "flight_id": "DL789", "airline": "Delta Air Lines", "flight_number": "DL 789",
            "origin": origin, "destination": destination, "departure_time": "23:55",
            "arrival_time": "17:20+1", "duration": "15h 25m", "stops": 1, "stop_cities": ["SEA"],
            "price": 780, "currency": "USD", "class": travel_class, "available_seats": 20,
            "aircraft": "Airbus A350-900",
        },
    ]

    return {
        "flights": mock_flights,
        "search_params": {
            "origin": origin, "destination": destination, "departure_date": departure_date,
            "return_date": return_date, "passengers": passengers, "class": travel_class,
        },
        "total_results": len(mock_flights),
    }


def get_airport_info(airport_code: str) -> Dict[str, Any]:
    """Get information about an airport.

    Args:
        airport_code: 3-letter airport code (e.g. SFO).

    Returns:
        A dict with the airport's name, city, country, timezone, terminals and airlines.
    """
    airport_data = {
        "SFO": {"name": "San Francisco International Airport", "city": "San Francisco",
                "country": "United States", "timezone": "America/Los_Angeles", "terminals": 4,
                "airlines": ["United", "Delta", "American", "Alaska"]},
        "NRT": {"name": "Narita International Airport", "city": "Tokyo", "country": "Japan",
                "timezone": "Asia/Tokyo", "terminals": 3, "airlines": ["ANA", "JAL", "United", "Delta"]},
        "LHR": {"name": "London Heathrow Airport", "city": "London", "country": "United Kingdom",
                "timezone": "Europe/London", "terminals": 5,
                "airlines": ["British Airways", "Virgin Atlantic", "American"]},
    }
    return airport_data.get(airport_code.upper(), {
        "name": f"Airport {airport_code.upper()}", "city": "Unknown", "country": "Unknown",
        "timezone": "Unknown", "error": "Airport information not available",
    })


def check_flight_status(flight_number: str, date: str) -> Dict[str, Any]:
    """Check the status of a specific flight.

    Args:
        flight_number: Flight number (e.g. AA123, UA456).
        date: Flight date in YYYY-MM-DD format.

    Returns:
        A dict with the flight's status, gate, terminal and any delay.
    """
    return {
        "flight_number": flight_number.upper(), "date": date, "status": "On Time",
        "departure_time": "14:30", "arrival_time": "22:45", "gate": "A12", "terminal": "2",
        "delay_minutes": 0, "aircraft": "Boeing 787-9",
    }


# --------------------------------------------------------------------------- #
# Hotel tools
# --------------------------------------------------------------------------- #

_ALL_HOTELS = [
    {"hotel_id": "HTL_001", "name": "Park Hyatt Tokyo", "brand": "Hyatt", "category": "luxury",
     "star_rating": 5, "guest_rating": 4.8, "review_count": 2847,
     "location": {"district": "Shinjuku", "nearest_station": "Shinjuku Station (5 min walk)"},
     "price_per_night": 450, "currency": "USD",
     "amenities": ["WiFi", "Indoor Pool", "Spa", "Fitness Center", "Restaurant", "Bar",
                   "Concierge", "Room Service", "Valet Parking"],
     "room_types": ["Deluxe King", "Deluxe Twin", "Park Suite", "Presidential Suite"],
     "cancellation": "Free cancellation until 48h before check-in"},
    {"hotel_id": "HTL_002", "name": "Shibuya Excel Hotel Tokyu", "brand": "Tokyu Hotels",
     "category": "business", "star_rating": 4, "guest_rating": 4.2, "review_count": 1563,
     "location": {"district": "Shibuya", "nearest_station": "Shibuya Station (3 min walk)"},
     "price_per_night": 180, "currency": "USD",
     "amenities": ["WiFi", "Restaurant", "Business Center", "Laundry", "24h Front Desk"],
     "room_types": ["Standard Single", "Superior Double", "Executive Twin"],
     "cancellation": "Free cancellation until 24h before check-in"},
    {"hotel_id": "HTL_003", "name": "The Prince Sakura Tower Tokyo", "brand": "Prince Hotels",
     "category": "luxury", "star_rating": 5, "guest_rating": 4.6, "review_count": 892,
     "location": {"district": "Shinagawa/Takanawa", "nearest_station": "Shinagawa Station (5 min walk)"},
     "price_per_night": 320, "currency": "USD",
     "amenities": ["WiFi", "Indoor Pool", "Spa", "Multiple Restaurants", "Bar", "Fitness Center"],
     "room_types": ["Deluxe Room", "Executive Floor", "Tower Suite"],
     "cancellation": "Free cancellation until 72h before check-in"},
    {"hotel_id": "HTL_004", "name": "Capsule Hotel Anshin Oyado", "brand": "Independent",
     "category": "budget", "star_rating": 2, "guest_rating": 3.9, "review_count": 567,
     "location": {"district": "Shimbashi", "nearest_station": "Shimbashi Station (2 min walk)"},
     "price_per_night": 45, "currency": "USD",
     "amenities": ["WiFi", "Shared Bath", "Locker", "Vending Machines", "Laundry"],
     "room_types": ["Standard Capsule", "Women-only Capsule"],
     "cancellation": "No free cancellation"},
]


def search_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    guests: int = 2,
    rooms: int = 1,
    budget_max: Optional[float] = None,
    budget_min: Optional[float] = None,
    star_rating: Optional[int] = None,
    amenities: Optional[List[str]] = None,
    hotel_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Search for hotels in a specific location with filters.

    Args:
        destination: City, neighborhood, or location name.
        check_in: Check-in date in YYYY-MM-DD format.
        check_out: Check-out date in YYYY-MM-DD format.
        guests: Number of guests.
        rooms: Number of rooms needed.
        budget_max: Maximum price per night in USD.
        budget_min: Minimum price per night in USD, for quality filtering.
        star_rating: Minimum star rating (1-5).
        amenities: Desired amenities, e.g. pool, gym, spa, wifi, restaurant, bar, parking.
        hotel_type: Hotel type preference - luxury, business, boutique, budget, resort.

    Returns:
        A dict with the matching hotels (sorted by guest rating) and search parameters.
    """
    logger.info(f"Searching hotels in {destination} for {check_in} to {check_out}")
    nights = _calculate_nights(check_in, check_out)

    hotels = [{**h, "total_price": h["price_per_night"] * nights} for h in _ALL_HOTELS]

    if budget_max:
        hotels = [h for h in hotels if h["price_per_night"] <= budget_max]
    if budget_min:
        hotels = [h for h in hotels if h["price_per_night"] >= budget_min]
    if star_rating:
        hotels = [h for h in hotels if h["star_rating"] >= star_rating]
    if hotel_type:
        hotels = [h for h in hotels if h["category"] == hotel_type]
    if amenities:
        hotels = [h for h in hotels
                  if any(a.lower() in [x.lower() for x in h["amenities"]] for a in amenities)]

    hotels.sort(key=lambda h: h["guest_rating"], reverse=True)

    return {
        "hotels": hotels,
        "search_params": {
            "destination": destination, "check_in": check_in, "check_out": check_out,
            "nights": nights, "guests": guests, "rooms": rooms,
        },
        "total_results": len(hotels),
    }


def get_hotel_details(hotel_id: str) -> Dict[str, Any]:
    """Get comprehensive information about a specific hotel.

    Args:
        hotel_id: Hotel ID from search results (e.g. HTL_001).

    Returns:
        A dict with detailed amenities, room types, policies and reviews for the hotel.
    """
    logger.info(f"Getting details for hotel {hotel_id}")
    details = {
        "HTL_001": {
            "detailed_description": "Park Hyatt Tokyo stands as an architectural masterpiece in "
                                     "the heart of Shinjuku, offering unparalleled luxury with "
                                     "panoramic views of Tokyo.",
            "policies": {"check_in": "15:00", "check_out": "12:00", "pets": "Not allowed"},
            "nearby_attractions": [
                {"name": "Tokyo Metropolitan Government Building", "distance": "5 min walk"},
                {"name": "Shinjuku Park", "distance": "10 min walk"},
            ],
        },
        "HTL_002": {
            "detailed_description": "Shibuya Excel Hotel Tokyu offers prime access to Tokyo's "
                                     "most vibrant district.",
            "policies": {"check_in": "14:00", "check_out": "11:00", "pets": "Not allowed"},
            "nearby_attractions": [{"name": "Shibuya Crossing", "distance": "3 min walk"}],
        },
    }
    return details.get(hotel_id, {"error": "Hotel details not found"})


def check_availability(
    hotel_id: str, check_in: str, check_out: str, rooms: int = 1, guests: int = 2
) -> Dict[str, Any]:
    """Check detailed room availability and pricing for specific dates.

    Args:
        hotel_id: Hotel ID.
        check_in: Check-in date YYYY-MM-DD.
        check_out: Check-out date YYYY-MM-DD.
        rooms: Number of rooms.
        guests: Number of guests.

    Returns:
        A dict with available room types, pricing and cancellation terms.
    """
    logger.info(f"Checking availability for {hotel_id} from {check_in} to {check_out}")
    nights = _calculate_nights(check_in, check_out)

    availability = {
        "HTL_001": {"available": True, "room_types": [
            {"type": "Deluxe King", "available_rooms": 3, "price_per_night": 450,
             "total_price": 450 * nights, "cancellation": "Free until 48h before"},
        ]},
        "HTL_002": {"available": True, "room_types": [
            {"type": "Standard Single", "available_rooms": 5, "price_per_night": 140,
             "total_price": 140 * nights, "cancellation": "Free until 24h before"},
        ]},
    }
    base = availability.get(hotel_id, {"available": False, "reason": "Hotel not found"})
    return {**base, "hotel_id": hotel_id, "check_in": check_in, "check_out": check_out, "nights": nights}


def get_area_info(location: str, interests: Optional[List[str]] = None) -> Dict[str, Any]:
    """Get information about a hotel's location and nearby attractions.

    Args:
        location: Location or neighborhood name.
        interests: Types of nearby attractions to highlight, e.g. restaurants, shopping, museums.

    Returns:
        A dict describing the area, transportation, attractions and who it's best for.
    """
    logger.info(f"Getting area info for {location}")
    area_data = {
        "shinjuku": {
            "description": "Tokyo's bustling business district and entertainment hub.",
            "attractions": {"shopping": ["Takashimaya Times Square", "Don Quijote"],
                             "dining": ["Golden Gai", "Memory Lane"]},
            "best_for": ["Business travelers", "Nightlife enthusiasts", "First-time visitors"],
        },
        "shibuya": {
            "description": "Youth culture center famous for the world's busiest pedestrian crossing.",
            "attractions": {"shopping": ["Shibuya 109", "Shibuya Sky"],
                             "dining": ["Themed cafes", "International cuisine"]},
            "best_for": ["Young travelers", "Shopping enthusiasts", "Nightlife"],
        },
    }
    key = location.lower().replace(" ", "").replace("tokyo", "")
    info = area_data.get(key, {"description": f"Information for {location} area",
                                "note": "Detailed information not available for this specific location"})
    return {"location": location, "area_info": info, "interests_filter": interests}


# --------------------------------------------------------------------------- #
# Activity tools
# --------------------------------------------------------------------------- #

_ALL_ACTIVITIES = [
    {"activity_id": "ACT_001", "name": "Senso-ji Temple & Asakusa Walking Tour", "category": "cultural",
     "description": "Explore Tokyo's oldest temple and traditional Asakusa district with a local guide.",
     "duration": "3 hours", "price": 45, "currency": "USD", "budget_level": "budget", "rating": 4.7,
     "location": "Asakusa, Tokyo", "booking_required": True},
    {"activity_id": "ACT_002", "name": "Sushi Making Workshop with Master Chef", "category": "food",
     "description": "Learn authentic sushi making techniques from a master chef in Tokyo.",
     "duration": "2.5 hours", "price": 120, "currency": "USD", "budget_level": "mid-range", "rating": 4.9,
     "location": "Ginza, Tokyo", "booking_required": True},
    {"activity_id": "ACT_003", "name": "Tokyo Skytree Fast-Track Ticket", "category": "sightseeing",
     "description": "Skip-the-line access to Tokyo's tallest tower with panoramic city views.",
     "duration": "1.5 hours", "price": 28, "currency": "USD", "budget_level": "budget", "rating": 4.5,
     "location": "Tokyo Skytree Town", "booking_required": False},
    {"activity_id": "ACT_004", "name": "Private Geisha District Evening Tour", "category": "cultural",
     "description": "Exclusive evening tour of Gion district with geisha spotting and kaiseki dinner.",
     "duration": "4 hours", "price": 350, "currency": "USD", "budget_level": "luxury", "rating": 4.8,
     "location": "Gion, Kyoto", "booking_required": True},
    {"activity_id": "ACT_005", "name": "Shibuya Food & Nightlife Crawl", "category": "nightlife",
     "description": "Experience Tokyo's nightlife with food stops and local bars in Shibuya.",
     "duration": "4 hours", "price": 85, "currency": "USD", "budget_level": "mid-range", "rating": 4.6,
     "location": "Shibuya, Tokyo", "booking_required": True},
]


def search_activities(
    destination: str,
    categories: Optional[List[str]] = None,
    budget_level: str = "mid-range",
    duration: Optional[str] = None,
    group_size: int = 2,
) -> Dict[str, Any]:
    """Search for activities and attractions in a location.

    Args:
        destination: City or location name.
        categories: Activity categories, e.g. cultural, food, outdoor, entertainment, museums.
        budget_level: Budget level - budget, mid-range, luxury, or "all".
        duration: Activity duration - short (1-2h), medium (3-4h), long (full day).
        group_size: Number of people.

    Returns:
        A dict with the matching activities and search parameters.
    """
    logger.info(f"Searching activities in {destination} for categories: {categories}")
    activities = _ALL_ACTIVITIES
    if categories:
        wanted = [c.lower() for c in categories]
        activities = [a for a in activities if a["category"] in wanted]
    if budget_level != "all":
        activities = [a for a in activities if a["budget_level"] == budget_level]

    return {
        "activities": activities[:10],
        "search_params": {"destination": destination, "categories": categories,
                           "budget_level": budget_level, "duration": duration, "group_size": group_size},
        "total_results": len(activities),
    }


def get_restaurant_recommendations(
    destination: str, cuisine_type: str, price_range: str = "moderate", dining_style: str = "casual"
) -> Dict[str, Any]:
    """Get restaurant recommendations for a specific cuisine or area.

    Args:
        destination: City or neighborhood.
        cuisine_type: Cuisine type (e.g. Japanese, Italian) or "local".
        price_range: Price range - budget, moderate, upscale, fine-dining, or "all".
        dining_style: Dining style - casual, romantic, family, business, or "all".

    Returns:
        A dict with matching restaurants and search parameters.
    """
    logger.info(f"Searching {cuisine_type} restaurants in {destination}")
    restaurants = [
        {"restaurant_id": "REST_001", "name": "Sukiyabashi Jiro Honten", "cuisine": "Japanese",
         "specialty": "Sushi", "price_range": "fine-dining", "rating": 4.9, "michelin_stars": 3,
         "location": "Ginza, Tokyo", "average_cost": 400, "dining_style": "fine-dining"},
        {"restaurant_id": "REST_002", "name": "Ichiran Ramen Shibuya", "cuisine": "Japanese",
         "specialty": "Ramen", "price_range": "budget", "rating": 4.2, "location": "Shibuya, Tokyo",
         "average_cost": 12, "dining_style": "casual"},
        {"restaurant_id": "REST_003", "name": "Kikunoi Honten", "cuisine": "Japanese",
         "specialty": "Kaiseki", "price_range": "fine-dining", "rating": 4.8, "michelin_stars": 3,
         "location": "Higashiyama, Kyoto", "average_cost": 350, "dining_style": "fine-dining"},
    ]
    filtered = [
        r for r in restaurants
        if (cuisine_type.lower() == "local" or cuisine_type.lower() in r["cuisine"].lower())
        and (price_range == "all" or r["price_range"] == price_range)
        and (dining_style == "all" or r["dining_style"] == dining_style)
    ]
    return {
        "restaurants": filtered,
        "search_params": {"destination": destination, "cuisine_type": cuisine_type,
                           "price_range": price_range, "dining_style": dining_style},
        "total_results": len(filtered),
    }


def check_activity_availability(activity_id: str, date: str, time: Optional[str] = None) -> Dict[str, Any]:
    """Check availability and booking requirements for an activity.

    Args:
        activity_id: Activity ID from search results.
        date: Date in YYYY-MM-DD format.
        time: Preferred time - morning, afternoon, or evening.

    Returns:
        A dict with available time slots, remaining spots and cancellation policy.
    """
    return {
        "activity_id": activity_id, "date": date, "available": True,
        "available_times": ["09:00", "14:00", "17:00"], "spots_remaining": 8,
        "booking_deadline": "24 hours in advance",
        "cancellation_policy": "Free cancellation up to 48 hours before",
    }
