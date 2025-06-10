#!/usr/bin/env python3
"""
Test script to debug and fix the missing fields workflow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent_service.sqlagent import Chat, SQLAgent
import logging

# Set up logging to see detailed information
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_missing_fields_workflow():
    """Test the missing fields detection and asking workflow"""
    print("=" * 60)
    print("Testing Missing Fields Workflow")
    print("=" * 60)
    
    # Initialize the chat system
    chat = Chat()
    
    # Test case: Insert employee with only name provided
    user_input = "Add Employee his name Aakash"
    thread_id = "test_missing_fields"
    
    print(f"\nUser Input: {user_input}")
    print("-" * 40)
    
    try:
        # Run the first query
        result = chat.run(thread_id, user_input)
        
        print("Result:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        # Check if the system is asking for missing fields
        if "message" in result and "Please provide a value for" in str(result["message"]):
            print("\n✅ SUCCESS: System is asking for missing field!")
            
            # Test providing the missing field
            if "department" in str(result["message"]):
                print("\nProviding department...")
                dept_result = chat.run(thread_id, "Engineering")
                print("Department result:")
                for key, value in dept_result.items():
                    print(f"  {key}: {value}")
                    
                if "Please provide a value for" in str(dept_result.get("message", "")):
                    print("✅ System is asking for next missing field!")
                else:
                    print("❌ System should be asking for next missing field")
                    
        else:
            print("❌ ISSUE: System is not asking for missing fields!")
            print("This is the issue we need to fix.")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def analyze_conditional_routing():
    """Analyze the conditional routing logic"""
    print("\n" + "=" * 60)
    print("Analyzing Conditional Routing Logic")
    print("=" * 60)
    
    # Test the conditional function directly
    def test_condition(state):
        missing_fields = state.get("missing_fields", [])
        has_missing = "missing_fields" in state and len(missing_fields) > 0
        return has_missing
    
    # Test cases
    test_states = [
        {"missing_fields": ["department", "salary"]},  # Should return True
        {"missing_fields": []},                        # Should return False  
        {},                                            # Should return False
        {"missing_fields": ["department"]},            # Should return True
    ]
    
    for i, state in enumerate(test_states):
        result = test_condition(state)
        print(f"Test {i+1}: {state} -> {result}")

def test_agent_parsing():
    """Test the agent's parsing capabilities"""
    print("\n" + "=" * 60)
    print("Testing Agent Parsing")
    print("=" * 60)
    
    agent = SQLAgent()
    
    # Test query generation
    user_input = "Add Employee his name Aakash"
    query = agent.generate_query(user_input)
    print(f"Generated Query: {query}")
    
    # Test query parsing
    parsed = agent.parse_insert_or_update_query(query)
    if parsed:
        table, query_type, values = parsed
        print(f"Parsed - Table: {table}, Type: {query_type}, Values: {values}")
        
        # Test field validation
        model = agent.model_map.get(table.lower())
        if model:
            missing, instance, validation_errors = agent.validate_fields(values, model)
            print(f"Missing fields: {missing}")
            print(f"Validation errors: {validation_errors}")
        else:
            print(f"No model found for table: {table}")
    else:
        print("Failed to parse query")

if __name__ == "__main__":
    test_missing_fields_workflow()
    analyze_conditional_routing()
    test_agent_parsing()
