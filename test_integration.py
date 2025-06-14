"""
Test script to verify SQL Agent and Chat UI integration
"""

from ai_agent_service.sqlagent import Chat
import json

def serialize_result(result):
    """Helper function to serialize complex objects for display"""
    if isinstance(result, dict):
        serialized = {}
        for key, value in result.items():
            try:
                # Try to convert to JSON serializable format
                json.dumps(value)
                serialized[key] = value
            except (TypeError, ValueError):
                # If not serializable, convert to string representation
                serialized[key] = str(value)
        return serialized
    return result

def test_conversation_flow():
    """Test the conversation flow with missing fields"""
    chat = Chat()
    
    print("=== Testing SQL Agent Conversation Flow ===\n")
    
    # Test 1: Complete query (should work without asking for missing fields)
    print("Test 1: Complete SELECT query")
    print("Input: 'Show all employees with salary greater than 50000'")
    try:
        result1 = chat.run("test_thread_1", "Show all employees with salary greater than 50000")
        result1_clean = serialize_result(result1)
        print(f"Result: {json.dumps(result1_clean, indent=2)}")
    except Exception as e:
        print(f"Error in Test 1: {e}")
    print("-" * 50)
    
    # Test 2: Incomplete INSERT query (should ask for missing fields)
    print("\nTest 2: Incomplete INSERT query")
    print("Input: 'Insert a new employee with name John Doe and salary 70000'")
    try:
        result2 = chat.run("test_thread_2", "Insert a new employee with name John Doe and salary 70000")
        result2_clean = serialize_result(result2)
        print(f"Result: {json.dumps(result2_clean, indent=2)}")
        
        # If waiting for input, continue the conversation
        if result2.get("type") == "waiting_for_input":
            print(f"\nSystem is asking for: {result2.get('missing_field')}")
            print("Providing missing information: 'Engineering'")
            
            result3 = chat.continue_conversation("test_thread_2", "Engineering", result2.get("state", {}))
            result3_clean = serialize_result(result3)
            print(f"Continuation Result: {json.dumps(result3_clean, indent=2)}")
            
            # Check if more fields are needed
            if result3.get("type") == "waiting_for_input":
                print(f"\nSystem is asking for: {result3.get('missing_field')}")
                print("Providing missing information: '2024-01-15'")
                
                result4 = chat.continue_conversation("test_thread_2", "2024-01-15", result3.get("state", {}))
                result4_clean = serialize_result(result4)
                print(f"Final Result: {json.dumps(result4_clean, indent=2)}")
    except Exception as e:
        print(f"Error in Test 2: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_conversation_flow()
