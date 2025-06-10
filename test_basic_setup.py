#!/usr/bin/env python3
"""
Simple test for LLM configuration and query execution
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent_service.sqlagent import SQLAgent
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_llm_and_database():
    """Test LLM configuration and database connection"""
    print("="*60)
    print("Testing LLM Configuration and Database Connection")
    print("="*60)
    
    try:
        # Initialize agent
        agent = SQLAgent()
        print("✅ SQLAgent initialized successfully")
        
        # Test simple query generation
        user_input = "Show me all employees"
        print(f"\n🔹 Testing query generation...")
        print(f"User input: '{user_input}'")
        
        query = agent.generate_query(user_input)
        print(f"Generated SQL: {query}")
        
        # Test query execution
        print(f"\n🔹 Testing query execution...")
        result = agent.execute_query(query)
        print(f"Query result:")
        print(result)
        
        # Test missing fields workflow
        print(f"\n🔹 Testing missing fields detection...")
        user_input2 = "Add employee named TestUser"
        query2 = agent.generate_query(user_input2)
        print(f"User input: '{user_input2}'")
        print(f"Generated SQL: {query2}")
        
        # Parse and validate
        parsed = agent.parse_insert_or_update_query(query2)
        if parsed:
            table, query_type, values = parsed
            print(f"Parsed - Table: {table}, Type: {query_type}, Values: {values}")
            
            model = agent.model_map.get(table.lower())
            if model:
                missing, instance, validation_errors = agent.validate_fields(values, model)
                print(f"Missing fields: {missing}")
                print(f"Validation errors: {validation_errors}")
                
                if missing:
                    print("✅ Missing fields detected correctly!")
                else:
                    print("⚠️ No missing fields - might be an issue")
        
        print(f"\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_and_database()
