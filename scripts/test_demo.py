#!/usr/bin/env python3

import requests
import json
import time

def test_travel_system():
    '''Test script for the ADK Travel System demo'''
    
    # Update this with your LoadBalancer IP or use port-forward
    BASE_URL = "http://localhost:8080"  # kubectl port-forward service/travel-coordinator 8080:80
    
    print("🧪 Testing ADK Travel System")
    print(f"Base URL: {BASE_URL}")
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"✅ Health check: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # Test individual agents
    print("\n2. Testing individual agents...")
    
    agents = ["flight", "hotel", "activity"]
    for agent in agents:
        try:
            test_query = {
                "query": f"Find {agent} options for Tokyo",
                "context": {"destination": "Tokyo", "days": 3}
            }
            response = requests.post(f"{BASE_URL}/agent/{agent}", 
                                   json=test_query, timeout=15)
            print(f"✅ {agent.title()} agent: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Found {len(result.get('results', []))} results")
        except Exception as e:
            print(f"❌ {agent.title()} agent failed: {e}")
    
    # Test comprehensive trip planning
    print("\n3. Testing comprehensive trip planning...")
    try:
        trip_request = {
            "query": "Plan a 3-day trip to Tokyo",
            "destination": "Tokyo",
            "days": 3,
            "budget": 2000
        }
        
        print("Sending request...")
        response = requests.post(f"{BASE_URL}/plan", 
                               json=trip_request, timeout=30)
        
        if response.status_code == 200:
            plan = response.json()
            print("✅ Trip planning successful!")
            print(f"   Trip ID: {plan.get('trip_id')}")
            print(f"   Summary: {plan.get('summary')}")
            print(f"   Estimated cost: ${plan.get('total_estimated_cost')}")
            
            # Show results summary
            flights = plan.get('flights', {}).get('results', [])
            hotels = plan.get('hotels', {}).get('results', [])
            activities = plan.get('activities', {}).get('results', [])
            
            print(f"   Flights found: {len(flights)}")
            print(f"   Hotels found: {len(hotels)}")
            print(f"   Activities found: {len(activities)}")
            
        else:
            print(f"❌ Trip planning failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Trip planning failed: {e}")
    
    print("\n🎉 Demo test complete!")

if __name__ == "__main__":
    test_travel_system()