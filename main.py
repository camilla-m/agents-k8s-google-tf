#!/usr/bin/env python3
"""
Google ADK Travel System - Main Entry Point (real google-adk implementation)

Serves the travel_coordinator agent (see agents/travel_coordinator/) two ways at once:

1. The native ADK dev console at /dev-ui - google-adk's own browser UI for chatting
   with the agents, inspecting sessions, and tracing tool/sub-agent calls. This is
   what `get_fast_api_app(..., web=True)` mounts for free; it's the real "platform to
   test the agents together" (the previous version of this project had none - it was
   REST-only, curl/Postman or nothing).
2. A small set of REST routes (/health, /ready, /chat, /agent/<type>/chat, /plan,
   /stats) kept for backward compatibility with scripts/test_adk_demo.py, ui/index.html,
   and the Kubernetes probes in k8s/coordinator-deployment.yaml - built on top of the
   same agents via google.adk.runners.Runner.
"""

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from prometheus_client import make_asgi_app

AGENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents")
sys.path.insert(0, AGENTS_DIR)

USER_ID = "api"  # single logical user - conversation_id (the ADK session id) is what
                  # actually separates one chat from another for our REST compat layer


def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "adk-coordinator", "message": "%(message)s", "module": "%(name)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


def validate_environment() -> bool:
    logger = logging.getLogger(__name__)
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        logger.error("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
        return False
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
    # Tell google-genai to talk to Vertex AI (Workload Identity / ADC) instead of the
    # Gemini Developer API (which would need GOOGLE_API_KEY, which we don't set).
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    logger.info(f"GOOGLE_CLOUD_PROJECT: {os.environ['GOOGLE_CLOUD_PROJECT']}")
    logger.info(f"GOOGLE_CLOUD_LOCATION: {os.environ['GOOGLE_CLOUD_LOCATION']}")
    return True


setup_logging()
_logger = logging.getLogger(__name__)
if not validate_environment():
    _logger.error("Environment validation failed")
    sys.exit(1)

# Import agents only after env vars are set, and only once - get_fast_api_app below
# does its own discovery/import of agents_dir, and our compat routes import the same
# module objects directly so both share one set of Agent instances.
from travel_coordinator.agent import activity_agent, flight_agent, hotel_agent, root_agent  # noqa: E402

SPECIALISTS: Dict[str, Any] = {"flight": flight_agent, "hotel": hotel_agent, "activity": activity_agent}

PORT = int(os.getenv("PORT", 8080))

app: FastAPI = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    allow_origins=["*"],  # lab/demo system, no auth, mock data only - see travel_adk_coordinator's old CORS note
    web=True,             # mounts the ADK dev console at /dev-ui
    host="0.0.0.0",
    port=PORT,
)

# Prometheus metrics (was a separate HTTP server on METRICS_PORT before; mounting it
# on this same ASGI app is simpler and avoids running two servers in one container).
app.mount("/metrics", make_asgi_app())

# get_fast_api_app() already registers its own bare-bones GET /health (just
# {"status": "ok"}, no per-agent detail). Drop it so our richer @app.get("/health")
# below - registered after this point - is the one Starlette actually matches,
# instead of silently losing to the earlier route with the same path.
app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/health"]

# --------------------------------------------------------------------------------- #
# Compat layer: REST endpoints kept from the previous Flask API, now backed by Runner
# --------------------------------------------------------------------------------- #

_session_service = InMemorySessionService()
_runners: Dict[str, Runner] = {
    "flight": Runner(app_name="flight", agent=flight_agent, session_service=_session_service),
    "hotel": Runner(app_name="hotel", agent=hotel_agent, session_service=_session_service),
    "activity": Runner(app_name="activity", agent=activity_agent, session_service=_session_service),
    "coordinator": Runner(app_name="coordinator", agent=root_agent, session_service=_session_service),
}


async def _get_or_create_session(app_name: str, session_id: Optional[str]):
    if session_id:
        existing = await _session_service.get_session(app_name=app_name, user_id=USER_ID, session_id=session_id)
        if existing:
            return existing
        return await _session_service.create_session(app_name=app_name, user_id=USER_ID, session_id=session_id)
    return await _session_service.create_session(app_name=app_name, user_id=USER_ID)


async def _run_turn(app_name: str, session_id: Optional[str], message: str):
    """Run one turn against a Runner and return (session_id, final_text, tool_calls).

    tool_calls is a list of {"name", "args", "result"} - args come back from
    google-genai as a plain dict already (unlike the older vertexai SDK, which handed
    back proto-plus MapComposite/RepeatedComposite objects that broke json.dumps on
    any array-typed argument), so no extra sanitizing is needed here.
    """
    runner = _runners[app_name]
    session = await _get_or_create_session(app_name, session_id)
    content = types.Content(role="user", parts=[types.Part(text=message)])

    final_text = ""
    calls: List[Dict[str, Any]] = []
    results: List[Any] = []
    async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=content):
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            if part.function_call:
                calls.append({"name": part.function_call.name, "args": dict(part.function_call.args or {})})
            if part.function_response:
                results.append(part.function_response.response)
            if part.text and event.is_final_response():
                final_text = part.text

    tool_calls = [
        {**call, "result": results[i] if i < len(results) else None}
        for i, call in enumerate(calls)
    ]
    return session.id, final_text, tool_calls


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "travel-adk-coordinator",
        "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "agents": {name: {"status": "healthy", "model": agent.model} for name, agent in SPECIALISTS.items()},
        "timestamp": time.time(),
    }


@app.get("/ready")
async def ready():
    # Cheap, no model calls - safe for a Kubernetes readiness probe hit every few
    # seconds (the equivalent /health check used to make a real Gemini call on every
    # hit in the old Flask version, which caused liveness probe timeouts and
    # CrashLoopBackOff - see git history).
    return {"status": "ready", "active_agents": list(SPECIALISTS.keys())}


@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    message = (data.get("message") or "").strip()
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)

    session_id, final_text, tool_calls = await _run_turn("coordinator", data.get("conversation_id"), message)

    agent_responses = {}
    for call in tool_calls:
        result = call.get("result")
        text = result.get("result") if isinstance(result, dict) and "result" in result else result
        agent_responses[call["name"]] = {"agent": call["name"], "response": text, "function_calls": []}

    return {
        "conversation_id": session_id,
        "coordinator": "travel-adk-coordinator",
        "multi_agent_response": len(agent_responses) > 0,
        "agent_responses": agent_responses,
        "summary": final_text,
        "response": final_text,
        "timestamp": time.time(),
    }


@app.post("/agent/{agent_type}/chat")
async def agent_chat(agent_type: str, request: Request):
    if agent_type not in SPECIALISTS:
        return JSONResponse(
            {"error": f"Unknown agent type: {agent_type}", "available_agents": list(SPECIALISTS)},
            status_code=400,
        )
    data = await request.json()
    message = (data.get("message") or "").strip()
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)

    session_id, final_text, tool_calls = await _run_turn(agent_type, data.get("conversation_id"), message)
    return {
        "conversation_id": session_id,
        "agent": f"{agent_type}_agent",
        "response": final_text,
        "function_calls": tool_calls,
        "timestamp": time.time(),
    }


@app.post("/plan")
async def plan(request: Request):
    import asyncio

    data = await request.json()
    destination = (data.get("destination") or "").strip()
    days = int(data.get("days", 3))
    budget = float(data.get("budget", 2000))
    interests = data.get("interests", [])
    travel_style = data.get("travel_style", "balanced")

    if not destination:
        return JSONResponse({"error": "Destination is required"}, status_code=400)
    if days < 1 or days > 30:
        return JSONResponse({"error": "Days must be between 1 and 30"}, status_code=400)
    if budget < 100:
        return JSONResponse({"error": "Budget must be at least $100"}, status_code=400)

    flight_budget = int(budget * 0.4)
    hotel_budget = int(budget * 0.35)
    activity_budget = int(budget * 0.25)
    hotel_per_night = hotel_budget // max(days - 1, 1)
    interest_context = f" with focus on {', '.join(interests)} experiences" if interests else ""
    style_context = {
        "budget": "budget-conscious and value-focused", "mid-range": "balanced comfort and value",
        "luxury": "premium and high-end", "business": "business travel optimized",
        "adventure": "adventure and unique experiences focused",
    }.get(travel_style, "balanced")

    queries = {
        "flight": (f"Find the best flight options to {destination} for a {days}-day trip. "
                   f"Budget around ${flight_budget}, {style_context} options preferred{interest_context}."),
        "hotel": (f"Find {travel_style} accommodation in {destination} for {days - 1} nights. "
                  f"Budget around ${hotel_per_night} per night{interest_context}."),
        "activity": (f"Recommend a {days}-day itinerary for {destination}{interest_context}. "
                     f"Activity budget around ${activity_budget}, {style_context} preferences."),
    }

    async def run_one(name: str):
        try:
            _, text, tool_calls = await _run_turn(name, None, queries[name])
            return name, {"response": text, "function_calls": tool_calls}
        except Exception as e:  # noqa: BLE001 - surfaced to the caller per-agent, not fatal
            _logger.error(f"Plan query failed for {name}: {e}")
            return name, {"error": str(e)}

    results = dict(await asyncio.gather(*(run_one(n) for n in ("flight", "hotel", "activity"))))

    successful = [n for n, r in results.items() if "response" in r]
    plan_id = f"plan_{int(time.time())}"

    return {
        "plan_id": plan_id,
        "destination": destination,
        "duration_days": days,
        "budget_usd": budget,
        "travel_style": travel_style,
        "interests": interests,
        "generated_by": "Google ADK Travel Coordinator",
        "agent_recommendations": results,
        "coordinator_summary": (
            f"Complete {days}-day travel plan for {destination} generated using Google ADK agents "
            f"with Vertex AI and Gemini. Includes recommendations from {len(successful)}/3 specialist agents."
        ),
        "budget_breakdown": {
            "total_budget": budget, "currency": "USD",
            "allocation": {
                "flights": {"allocated": flight_budget, "percentage": 40},
                "accommodation": {"allocated": hotel_budget, "percentage": 35},
                "activities": {"allocated": activity_budget, "percentage": 25},
            },
        },
        "next_steps": [
            "Review and compare flight options, considering timing and connections",
            "Confirm hotel availability for your exact dates and book reservation",
            "Research and book time-sensitive activities and restaurant reservations",
            f"Check visa and passport requirements for {destination}",
            "Review travel insurance options for international travel",
            "Notify banks of travel plans to avoid card issues",
        ],
        "plan_quality": {
            "completeness_percentage": round(len(successful) / 3 * 100, 1),
            "successful_components": len(successful),
            "total_components": 3,
            "overall_rating": "Excellent" if len(successful) == 3 else "Good" if len(successful) == 2 else "Fair",
        },
        "generated_at": time.time(),
    }


@app.get("/stats")
async def stats():
    agents_stats = {}
    for name in ("flight", "hotel", "activity", "coordinator"):
        sessions = await _session_service.list_sessions(app_name=name, user_id=USER_ID)
        agents_stats[name] = {"active_conversations": len(sessions.sessions)}
    return {"coordinator": {"project_id": os.getenv("GOOGLE_CLOUD_PROJECT")}, "agents": agents_stats}


if __name__ == "__main__":
    import uvicorn

    _logger.info("🚀 Starting Google ADK Travel Coordinator")
    _logger.info(f"📍 Port: {PORT}")
    _logger.info("🖥️  Dev console: /dev-ui  |  💚 Health: /health  |  💬 Chat: /chat")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
