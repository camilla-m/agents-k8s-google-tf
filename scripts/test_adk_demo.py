#!/usr/bin/env python3
"""
Google ADK Travel System - Test Script
Comprehensive testing for all ADK agents and coordinator
"""

import requests
import json
import time
import sys
import os
import subprocess
from typing import Dict, Any

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")

def get_base_url():
    """Get base URL - try LoadBalancer first, then localhost"""
    try:
        result = subprocess.run([
            'kubectl', 'get', 'service', 'travel-adk-coordinator', 
            '-n', 'adk-travel', 
            '-o', 'jsonpath={.status.loadBalancer.ingress[0].ip}'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            ip = result.stdout.strip()
            print_success(f"Found LoadBalancer IP: {ip}")
            return f"http://{ip}"
    except Exception as e:
        print_warning(f"Could not get LoadBalancer IP: {e}")
    
    print_info("Using localhost - ensure port-forward is running:")
    print_info("kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel")
    return "http://localhost:8080"

def test_health_check(base_url: str) -> bool:
    """Test the health endpoint"""
    print_header("Testing ADK Health Endpoint")
    
    try:
        response = requests.get(f"{base_url}/health", timeout=15)
        
        if response.status_code == 200:
            health_data = response.json()
            print_success(f"Health check passed: {health_data.get('status', 'unknown')}")
            
            # Display service info
            print_info(f"Service: {health_data.get('service', 'unknown')}")
            print_info(f"Project: {health_data.get('project_id', 'unknown')}")
            print_info(f"ADK Version: {health_data.get('adk_version', 'unknown')}")
            
            # Check individual agents
            agents = health_data.get('agents', {})
            for agent_name, agent_info in agents.items():
                status = agent_info.get('status', 'unknown')
                specialization = agent_info.get('specialization', 'unknown')
                conversations = agent_info.get('active_conversations', 0)
                
                if status == 'healthy':
                    print_success(f"{agent_name.title()}: {status} - {specialization} ({conversations} active)")
                else:
                    print_error(f"{agent_name.title()}: {status}")
            
            return True
        else:
            print_error(f"Health check failed: HTTP {response.status_code}")
            print_error(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Connection failed. Ensure the service is running and accessible.")
        print_info("Try: kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel")
        return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def test_individual_agents(base_url: str) -> bool:
    """Test individual ADK agent conversations"""
    print_header("Testing Individual ADK Agent Conversations")
    
    agent_tests = {
        "flight": {
            "message": "I need to find flights from San Francisco to Tokyo for next month. What are my best options for a business trip?",
            "expected_tools": ["search_flights", "get_airport_info"]
        },
        "hotel": {
            "message": "Can you recommend luxury hotels in Tokyo with spa facilities? My budget is around $400 per night for 3 nights.",
            "expected_tools": ["search_hotels", "get_hotel_details"]
        },
        "activity": {
            "message": "I'm interested in traditional Japanese culture and amazing food experiences in Tokyo. What unique activities would you recommend?",
            "expected_tools": ["search_activities", "get_restaurant_recommendations"]
        }
    }
    
    all_passed = True
    
    for agent_type, test_data in agent_tests.items():
        print(f"\n🤖 Testing {agent_type.title()} ADK Agent...")
        print_info(f"Query: {test_data['message'][:80]}...")
        
        try:
            payload = {"message": test_data['message']}
            
            start_time = time.time()
            response = requests.post(
                f"{base_url}/agent/{agent_type}/chat", 
                json=payload, 
                timeout=30
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print_success(f"{agent_type.title()} agent responded ({duration:.1f}s)")
                
                # Check response content
                ai_response = result.get('response', '')
                if ai_response:
                    print_info(f"Response: {ai_response[:150]}...")
                else:
                    print_warning("No AI response received")
                
                # Check for function calls (ADK tools)
                function_calls = result.get('function_calls', [])
                if function_calls:
                    tool_names = [fc.get('name') for fc in function_calls]
                    print_success(f"Tools used: {tool_names}")
                    
                    # Verify expected tools were used
                    expected_tools = test_data['expected_tools']
                    if any(tool in tool_names for tool in expected_tools):
                        print_success("Expected ADK tools were utilized")
                    else:
                        print_warning(f"Expected tools {expected_tools}, got {tool_names}")
                else:
                    print_warning("No function calls detected")
                
                conversation_id = result.get('conversation_id')
                if conversation_id:
                    print_info(f"Conversation ID: {conversation_id}")
                
            else:
                print_error(f"{agent_type.title()} agent failed: HTTP {response.status_code}")
                print_error(response.text)
                all_passed = False
                
        except requests.exceptions.Timeout:
            print_error(f"{agent_type.title()} agent timed out after 30s")
            all_passed = False
        except Exception as e:
            print_error(f"{agent_type.title()} agent error: {e}")
            all_passed = False
    
    return all_passed

def test_multi_agent_coordination(base_url: str) -> bool:
    """Test multi-agent ADK coordination"""
    print_header("Testing Multi-Agent ADK Coordination")
    
    coordination_message = (
        "Hi! I'm planning a comprehensive 4-day trip to Tokyo. I need flights from San Francisco, "
        "a nice hotel in Shibuya or Shinjuku area, and recommendations for cultural activities "
        "and the best sushi experiences. My total budget is $3000. Can you help coordinate everything?"
    )
    
    print_info(f"Complex Query: {coordination_message[:120]}...")
    
    try:
        payload = {"message": coordination_message}
        
        start_time = time.time()
        response = requests.post(f"{base_url}/chat", json=payload, timeout=45)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Multi-agent coordination successful ({duration:.1f}s)")
            
            if result.get('multi_agent_response', False):
                print_success("Multiple ADK agents coordinated successfully:")
                
                agent_responses = result.get('agent_responses', {})
                for agent_name, agent_response in agent_responses.items():
                    if isinstance(agent_response, dict):
                        if 'response' in agent_response:
                            response_length = len(agent_response.get('response', ''))
                            print_info(f"  • {agent_name}: {response_length} characters")
                            
                            # Show function calls from each agent
                            function_calls = agent_response.get('function_calls', [])
                            if function_calls:
                                tools = [fc.get('name') for fc in function_calls]
                                print_info(f"    🛠️ Tools: {tools}")
                        elif 'error' in agent_response:
                            print_warning(f"  • {agent_name}: Error occurred")
                
                summary = result.get('summary', 'No summary')
                if len(summary) > 50:
                    print_success("Coordinator generated comprehensive summary")
                    print_info(f"Summary: {summary[:200]}...")
                else:
                    print_warning("Summary too short or missing")
                    
            else:
                response_text = result.get('response', '')
                if response_text:
                    print_info(f"Single Agent Response: {response_text[:200]}...")
                else:
                    print_warning("No response content received")
                    
            return True
            
        else:
            print_error(f"Multi-agent coordination failed: HTTP {response.status_code}")
            print_error(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print_error("Multi-agent coordination timed out (45s)")
        return False
    except Exception as e:
        print_error(f"Multi-agent coordination error: {e}")
        return False

def test_comprehensive_planning(base_url: str) -> bool:
    """Test comprehensive ADK trip planning"""
    print_header("Testing Comprehensive ADK Trip Planning")
    
    trip_data = {
        "destination": "Tokyo",
        "days": 4,
        "budget": 3000,
        "interests": ["cultural", "food", "technology"],
        "travel_style": "mid-range"
    }
    
    print_info(f"Planning: {trip_data['days']} days in {trip_data['destination']}")
    print_info(f"Budget: ${trip_data['budget']}")
    print_info(f"Interests: {', '.join(trip_data['interests'])}")
    print_info(f"Style: {trip_data['travel_style']}")
    
    try:
        start_time = time.time()
        response = requests.post(f"{base_url}/plan", json=trip_data, timeout=60)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            plan = response.json()
            print_success(f"Comprehensive plan generated ({duration:.1f}s)")
            
            # Validate plan structure
            required_fields = ['plan_id', 'destination', 'generated_by', 'agent_recommendations']
            missing_fields = [field for field in required_fields if field not in plan]
            
            if missing_fields:
                print_warning(f"Plan missing fields: {missing_fields}")
            else:
                print_success("Plan structure is complete")
            
            print_info(f"Plan ID: {plan.get('plan_id', 'N/A')}")
            print_info(f"Generated by: {plan.get('generated_by', 'N/A')}")
            
            # Check agent recommendations
            agent_recs = plan.get('agent_recommendations', {})
            if agent_recs:
                print_success(f"Agent recommendations received from {len(agent_recs)} agents:")
                
                for agent_type, recommendation in agent_recs.items():
                    if isinstance(recommendation, dict):
                        if 'response' in recommendation:
                            response_length = len(recommendation['response'])
                            print_info(f"  • {agent_type.title()}: {response_length} characters")
                        elif 'error' in recommendation:
                            print_warning(f"  • {agent_type.title()}: Error - {recommendation['error']}")
                    else:
                        print_warning(f"  • {agent_type.title()}: Invalid format")
            else:
                print_warning("No agent recommendations in plan")
            
            # Check summary and next steps
            summary = plan.get('coordinator_summary', '')
            if summary and len(summary) > 100:
                print_success("Comprehensive coordinator summary generated")
                print_info(f"Summary: {summary[:300]}...")
            else:
                print_warning("Summary missing or too short")
            
            next_steps = plan.get('next_steps', [])
            if next_steps and len(next_steps) > 2:
                print_success(f"Next steps provided: {len(next_steps)} recommendations")
                for i, step in enumerate(next_steps[:3], 1):
                    print_info(f"  {i}. {step}")
            else:
                print_warning("Next steps missing or incomplete")
            
            return True
            
        else:
            print_error(f"Trip planning failed: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print_error(f"Error details: {error_data}")
            except:
                print_error(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print_error("Trip planning timed out (60s)")
        return False
    except Exception as e:
        print_error(f"Trip planning error: {e}")
        return False

def test_conversation_continuity(base_url: str) -> bool:
    """Test conversation continuity across multiple turns"""
    print_header("Testing ADK Conversation Continuity")
    
    try:
        # Start conversation
        print_info("Starting conversation with flight agent...")
        initial_message = "I'm planning a trip from SFO to Tokyo"
        response1 = requests.post(
            f"{base_url}/agent/flight/chat",
            json={"message": initial_message},
            timeout=30
        )
        
        if response1.status_code != 200:
            print_error("Failed to start conversation")
            return False
        
        result1 = response1.json()
        conversation_id = result1.get('conversation_id')
        
        if not conversation_id:
            print_error("No conversation ID received")
            return False
        
        print_success(f"Conversation started: {conversation_id}")
        
        # Continue conversation
        print_info("Continuing conversation...")
        followup_message = "What about business class options?"
        response2 = requests.post(
            f"{base_url}/agent/flight/chat",
            json={
                "message": followup_message,
                "conversation_id": conversation_id
            },
            timeout=30
        )
        
        if response2.status_code == 200:
            result2 = response2.json()
            returned_conv_id = result2.get('conversation_id')
            
            if returned_conv_id == conversation_id:
                print_success("Conversation continuity maintained")
                
                # Check if response references previous context
                response_text = result2.get('response', '').lower()
                if any(word in response_text for word in ['business', 'class', 'previous', 'earlier']):
                    print_success("Agent maintained conversation context")
                else:
                    print_warning("Context retention unclear")
                
                return True
            else:
                print_error("Conversation ID mismatch")
                return False
        else:
            print_error("Failed to continue conversation")
            return False
            
    except Exception as e:
        print_error(f"Conversation continuity test failed: {e}")
        return False

def show_demo_commands():
    """Display useful commands for live demo"""
    print_header("Live Demo Commands")
    
    demo_commands = [
        ("Check cluster status", "kubectl get pods -n adk-travel -o wide"),
        ("View service endpoints", "kubectl get services -n adk-travel"),
        ("Port forward for testing", "kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel"),
        ("Scale coordinator", "kubectl scale deployment travel-adk-coordinator --replicas=3 -n adk-travel"),
        ("View logs", "kubectl logs -f deployment/travel-adk-coordinator -n adk-travel"),
        ("Check metrics", "kubectl port-forward service/travel-adk-coordinator 8090:8090 -n adk-travel"),
        ("Test health endpoint", "curl -s http://localhost:8080/health | jq"),
        ("Test flight agent", 'curl -X POST http://localhost:8080/agent/flight/chat -H "Content-Type: application/json" -d \'{"message": "Find flights to Tokyo"}\''),
        ("Test coordination", 'curl -X POST http://localhost:8080/chat -H "Content-Type: application/json" -d \'{"message": "Plan complete Tokyo trip"}\''),
        ("Comprehensive planning", 'curl -X POST http://localhost:8080/plan -H "Content-Type: application/json" -d \'{"destination": "Tokyo", "days": 4, "budget": 3000}\'')
    ]
    
    for description, command in demo_commands:
        print(f"\n{Colors.CYAN}{Colors.BOLD}# {description}{Colors.END}")
        print(f"{Colors.YELLOW}{command}{Colors.END}")

def run_performance_test(base_url: str) -> Dict[str, float]:
    """Run basic performance tests"""
    print_header("Performance Testing")
    
    results = {}
    
    # Test health endpoint performance
    print_info("Testing health endpoint performance...")
    health_times = []
    for i in range(5):
        start = time.time()
        try:
            response = requests.get(f"{base_url}/health", timeout=10)
            if response.status_code == 200:
                health_times.append(time.time() - start)
        except:
            pass
    
    if health_times:
        avg_health = sum(health_times) / len(health_times)
        results['health_avg_ms'] = avg_health * 1000
        print_success(f"Health endpoint: {avg_health*1000:.1f}ms average")
    
    # Test agent response times
    test_message = "Quick test message"
    for agent in ['flight', 'hotel', 'activity']:
        print_info(f"Testing {agent} agent performance...")
        start = time.time()
        try:
            response = requests.post(
                f"{base_url}/agent/{agent}/chat",
                json={"message": test_message},
                timeout=15
            )
            if response.status_code == 200:
                duration = time.time() - start
                results[f'{agent}_response_ms'] = duration * 1000
                print_success(f"{agent.title()} agent: {duration*1000:.1f}ms")
        except:
            print_warning(f"{agent.title()} agent: timeout or error")
    
    return results

def main():
    """Main test function"""
    print_header("🤖 Google ADK Travel System - Comprehensive Test Suite")
    
    base_url = get_base_url()
    print_info(f"Testing against: {base_url}")
    
    # Track test results
    test_results = {}
    
    # Run all tests
    tests = [
        ("Health Check", test_health_check),
        ("Individual Agents", test_individual_agents), 
        ("Multi-Agent Coordination", test_multi_agent_coordination),
        ("Comprehensive Planning", test_comprehensive_planning),
        ("Conversation Continuity", test_conversation_continuity)
    ]
    
    for test_name, test_func in tests:
        try:
            test_results[test_name] = test_func(base_url)
        except Exception as e:
            print_error(f"Test {test_name} crashed: {e}")
            test_results[test_name] = False
    
    # Performance testing
    try:
        perf_results = run_performance_test(base_url)
    except Exception as e:
        print_warning(f"Performance tests failed: {e}")
        perf_results = {}
    
    # Final results summary
    print_header("🎯 Test Results Summary")
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, passed in test_results.items():
        status = "PASS" if passed else "FAIL"
        color = Colors.GREEN if passed else Colors.RED
        print(f"{color}{status:4} {Colors.END} {test_name}")
    
    print(f"\n{Colors.BOLD}Results: {passed_tests}/{total_tests} tests passed{Colors.END}")
    
    if perf_results:
        print(f"\n{Colors.CYAN}Performance Metrics:{Colors.END}")
        for metric, value in perf_results.items():
            print(f"  {metric}: {value:.1f}ms")
    
    # Final status
    if passed_tests == total_tests:
        print_header("🎉 All Tests Passed! ADK System Ready for Demo")
        show_demo_commands()
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Your Google ADK Travel System is ready for the 15-minute presentation!{Colors.END}")
        return 0
    else:
        print_header("⚠️ Some Tests Failed")
        print_error(f"{total_tests - passed_tests} test(s) failed. Check the logs above.")
        print_info("Common issues:")
        print_info("- Ensure kubectl port-forward is running")
        print_info("- Check that all pods are in Running state")
        print_info("- Verify ADK credentials are properly configured")
        return 1

if __name__ == "__main__":
    sys.exit(main())