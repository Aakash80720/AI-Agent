#!/usr/bin/env python3
"""
Test script to demonstrate the chain of questions for missing fields
This script simulates the complete chain of questions until all required fields are provided
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent_service.sqlagent import SQLAgent, Employee
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_missing_fields_chain():
    """Test the complete missing fields chain workflow"""
    print("=" * 80)
    print("Testing Missing Fields Chain Workflow")
    print("=" * 80)
    
    agent = SQLAgent()
    
    # Step 1: Start with incomplete user input
    user_input = "Add Employee his name Aakash"
    print(f"\n🔹 Step 1: User Input: {user_input}")
    print("-" * 50)
    
    # Generate query
    query = agent.generate_query(user_input)
    print(f"Generated Query: {query}")
    
    # Parse the query
    parsed = agent.parse_insert_or_update_query(query)
    if parsed:
        table, query_type, values = parsed
        print(f"Parsed - Table: {table}, Type: {query_type}, Values: {values}")
        
        # Step 2: Validate and detect missing fields
        model = agent.model_map.get(table.lower())
        if model:
            missing, instance, validation_errors = agent.validate_fields(values, model)
            print(f"\n🔹 Step 2: Validation Results:")
            print(f"  Missing fields: {missing}")
            print(f"  Instance: {instance}")
            print(f"  Validation errors: {validation_errors}")
            
            if missing:
                # Step 3: Ask for first missing field
                current_values = values.copy()
                remaining_fields = missing.copy()
                
                while remaining_fields:
                    next_field = remaining_fields[0]
                    print(f"\n🔹 Step 3.{len(missing) - len(remaining_fields) + 1}: Asking for missing field '{next_field}'")
                    
                    # Get field description
                    field_desc = get_field_description(table, next_field)
                    question = f"Please provide a value for '{next_field}': {field_desc}"
                    print(f"❓ SYSTEM: {question}")
                    
                    # Simulate user response
                    if next_field == "department":
                        user_response = "Engineering"
                    elif next_field == "salary":
                        user_response = "75000"
                    else:
                        user_response = "Default Value"
                    
                    print(f"👤 USER: {user_response}")
                    
                    # Update values with user response
                    current_values[next_field] = user_response
                    remaining_fields.pop(0)
                    
                    # Re-validate with updated values
                    new_missing, new_instance, new_validation_errors = agent.validate_fields(current_values, model)
                    print(f"  Updated values: {current_values}")
                    print(f"  Remaining missing fields: {new_missing}")
                    
                    if new_validation_errors:
                        print(f"  Validation errors: {new_validation_errors}")
                    
                    # Update remaining fields list
                    remaining_fields = new_missing.copy()
                
                # Step 4: All fields provided, generate final query
                print(f"\n🔹 Step 4: All required fields provided!")
                print(f"Final values: {current_values}")
                
                try:
                    final_instance = model(**current_values)
                    print(f"✅ Validation successful: {final_instance}")
                    
                    # Generate final SQL
                    final_query = agent.generate_final_sql(current_values, table, query_type)
                    print(f"Final SQL Query: {final_query}")
                    
                    print(f"\n🎉 SUCCESS: Chain of questions completed successfully!")
                    print(f"📋 Summary:")
                    print(f"   - Started with: {values}")
                    print(f"   - Asked for: {missing}")
                    print(f"   - Final values: {current_values}")
                    print(f"   - Ready to execute: {final_query}")
                    
                except Exception as e:
                    print(f"❌ Final validation failed: {e}")
            else:
                print("✅ No missing fields detected")
        else:
            print(f"❌ No model found for table: {table}")
    else:
        print("❌ Failed to parse query")

def get_field_description(table: str, field: str) -> str:
    """Get user-friendly field descriptions"""
    descriptions = {
        "employee": {
            "name": "Full name of the employee",
            "department": "Department name (e.g., Engineering, Sales, HR)",
            "salary": "Annual salary amount (numbers only)",
            "hire_date": "Hire date in YYYY-MM-DD format"
        },
        "project": {
            "name": "Project name",
            "description": "Brief project description",
            "start_date": "Start date in YYYY-MM-DD format",
            "end_date": "End date in YYYY-MM-DD format",
            "budget": "Project budget amount (numbers only)",
            "department": "Department responsible for the project"
        }
    }
    
    return descriptions.get(table, {}).get(field, f"Value for {field}")

def test_different_scenarios():
    """Test different scenarios with missing fields"""
    print("\n" + "=" * 80)
    print("Testing Different Missing Field Scenarios")
    print("=" * 80)
    
    scenarios = [
        {
            "input": "Add employee named John",
            "expected_missing": ["department", "salary"]
        },
        {
            "input": "Insert employee John with salary 60000",
            "expected_missing": ["department"]
        },
        {
            "input": "Add employee John department Engineering",
            "expected_missing": ["salary"]
        }
    ]
    
    agent = SQLAgent()
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🔹 Scenario {i}: {scenario['input']}")
        print("-" * 50)
        
        # Generate and parse query
        query = agent.generate_query(scenario['input'])
        parsed = agent.parse_insert_or_update_query(query)
        
        if parsed:
            table, query_type, values = parsed
            model = agent.model_map.get(table.lower())
            
            if model:
                missing, instance, validation_errors = agent.validate_fields(values, model)
                print(f"Expected missing: {scenario['expected_missing']}")
                print(f"Actual missing: {missing}")
                
                if set(missing) == set(scenario['expected_missing']):
                    print("✅ Missing fields detection is correct!")
                else:
                    print("❌ Missing fields detection is incorrect!")
            else:
                print("❌ No model found")
        else:
            print("❌ Failed to parse query")
    current_values = values.copy()
    question_count = 0
    
    while missing and question_count < 10:  # Safety limit
        question_count += 1
        next_field = missing[0]
        
        # Ask for the missing field
        print(f"\n🤖 Question {question_count}: Please provide a value for '{next_field}'")
        
        # Simulate user response
        if next_field == "department":
            user_response = "Engineering"
        elif next_field == "salary":
            user_response = "75000"
        else:
            user_response = "test_value"
        
        print(f"👤 User Response: {user_response}")
        
        # Update values
        current_values[next_field] = user_response
        print(f"Updated Values: {current_values}")
        
        # Re-validate
        missing, instance, validation_errors = agent.validate_fields(current_values, model)
        print(f"Re-validation - Missing: {missing}, Errors: {validation_errors}")
        
        if not missing:
            print(f"\n✅ All required fields collected!")
            break
    
    # Generate final query
    if not missing:
        final_query = agent.generate_final_sql(current_values, table, query_type)
        print(f"\n🎯 Final Query: {final_query}")
        
        # Execute the query (in a real scenario)
        print(f"🚀 Ready to execute: {final_query}")
        print(f"📋 Complete Employee Data: {instance}")
    else:
        print(f"❌ Still missing fields after {question_count} questions: {missing}")

def test_validation_sequence():
    """Test the validation sequence with different scenarios"""
    print("\n" + "=" * 60)
    print("Testing Validation Sequence")
    print("=" * 60)
    
    agent = SQLAgent()
    
    test_cases = [
        {
            "name": "Only name provided",
            "values": {"name": "John"},
            "expected_missing": ["department", "salary"]
        },
        {
            "name": "Name and department provided", 
            "values": {"name": "John", "department": "Engineering"},
            "expected_missing": ["salary"]
        },
        {
            "name": "All required fields provided",
            "values": {"name": "John", "department": "Engineering", "salary": 50000},
            "expected_missing": []
        },
        {
            "name": "With NULL values",
            "values": {"name": "John", "department": None, "salary": None},
            "expected_missing": ["department", "salary"]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        values = test_case["values"]
        expected_missing = test_case["expected_missing"]
        
        missing, instance, validation_errors = agent.validate_fields(values, Employee)
        
        print(f"Values: {values}")
        print(f"Missing: {missing}")
        print(f"Expected: {expected_missing}")
        
        if missing == expected_missing:
            print("✅ PASS")
        else:
            print("❌ FAIL")

if __name__ == "__main__":
    test_missing_fields_chain()
    test_validation_sequence()
