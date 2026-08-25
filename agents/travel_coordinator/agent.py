"""
Google ADK Travel Agents - real google-adk implementation.

Three specialist LlmAgents (flight, hotel, activity), each with its own tools, plus a
root coordinator agent that has the specialists mounted as AgentTools so its LLM can
call one, several, or all of them in the same turn and synthesize a combined answer -
this is the closest real-ADK equivalent of the original hand-rolled coordinator, which
fanned a request out to whichever specialists were relevant and merged their replies.

`root_agent` is the name google-adk's agent loader looks for in this package (see
agents/travel_coordinator/__init__.py) - it's what `adk web` / `adk run` and
get_fast_api_app(agents_dir=...) discover and run.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from . import tools

# Vertex AI Gemini model. gemini-1.5-pro/gemini-pro are retired - keep this in sync
# with whatever Gemini model family is currently supported for your project/region.
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


flight_agent = LlmAgent(
    name="flight_agent",
    model=MODEL_NAME,
    description="Searches flights, airport info, and flight status.",
    instruction="""You are a specialized flight booking assistant.

Your expertise includes flight search across airlines, price comparison, travel date
optimization, route planning and connections, and booking assistance.

Always be helpful and accurate. Use your tools to search for flight data when users
make requests. Format prices clearly and explain any restrictions or fees.""",
    tools=[tools.search_flights, tools.get_airport_info, tools.check_flight_status],
)

hotel_agent = LlmAgent(
    name="hotel_agent",
    model=MODEL_NAME,
    description="Searches hotels, availability, pricing and neighborhood info.",
    instruction="""You are a specialized hotel booking assistant.

Your expertise includes hotel search and availability, price comparison, room type
recommendations, location analysis, amenity matching, and booking/cancellation
policies.

Always provide amenities, location benefits, pricing, and booking terms. Use your
tools to search for hotel data. Be proactive suggesting alternatives if the user's
initial requirements are too restrictive.""",
    tools=[tools.search_hotels, tools.get_hotel_details, tools.check_availability, tools.get_area_info],
)

activity_agent = LlmAgent(
    name="activity_agent",
    model=MODEL_NAME,
    description="Recommends activities, restaurants and local experiences.",
    instruction="""You are a specialized travel activity and dining assistant.

Your expertise includes local activity and attraction recommendations, cultural
experience curation, restaurant recommendations, entertainment, and outdoor
activities.

Always give practical details like hours and prices, and personalize recommendations
to the traveler's interests and style. Use your tools to search for activity and
restaurant data.""",
    tools=[tools.search_activities, tools.get_restaurant_recommendations, tools.check_activity_availability],
)

root_agent = LlmAgent(
    name="travel_coordinator",
    model=MODEL_NAME,
    description="Coordinates flight, hotel and activity specialists for trip planning.",
    instruction="""You are the Travel Coordinator, orchestrating three specialist agents:
flight_agent, hotel_agent, and activity_agent.

- If the user asks about only one topic (e.g. just flights), call only that specialist.
- For broader trip-planning requests (e.g. "plan a trip to X", "help me with my vacation"),
  call every specialist that's relevant to the request in the same turn, then combine
  their answers into one clear, well-organized response covering each area.
- Never make up flight, hotel or activity details yourself - always delegate to the
  matching specialist tool, which has the real (mocked) search data.""",
    tools=[
        AgentTool(agent=flight_agent),
        AgentTool(agent=hotel_agent),
        AgentTool(agent=activity_agent),
    ],
)
