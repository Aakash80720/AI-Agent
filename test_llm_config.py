#!/usr/bin/env python3
"""
Quick test to check LLM response format and temperature settings
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent_service.sqlagent import SQLAgent

def test_llm_response():
    """Test LLM response format and consistency"""
    print("=" * 60)
    print("🔧 TESTING LLM CONFIGURATION AND RESPONSE FORMAT")
    print("=" * 60)
    
    agent = SQLAgent()
    
    # Test simple query
    user_input = "show me all employees"
    print(f"\n👤 User Input: {user_input}")
    
    # Generate query
    query = agent.generate_query(user_input)
    print(f"🤖 Generated SQL: {query}")
    
    # Execute query
    result = agent.execute_query(query)
    print(f"📊 Query Result:")
    print(result)
    
    # Test the specific problematic case you mentioned
    print("\n" + "=" * 60)
    print("🔍 TESTING SPECIFIC CASE: SELECT id, name FROM employee")
    print("=" * 60)
    
    test_query = 'SELECT "id", "name" FROM employee'
    print(f"🔧 Executing: {test_query}")
    
    result = agent.execute_query(test_query)
    print(f"📊 Result type: {type(result)}")
    print(f"📊 Result content:")
    print(result)
    
    if hasattr(result, 'to_string'):
        print(f"📊 DataFrame string representation:")
        print(result.to_string())

if __name__ == "__main__":
    test_llm_response()
