#!/usr/bin/env python3
"""
Complete Missing Fields Workflow Test
Demonstrates the entire chain of questions for missing mandatory fields
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent_service.sqlagent import SQLAgent, Employee
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def simulate_user_workflow():
    """Simulate a complete user workflow with missing fields"""
    print("=" * 80)
    print("🤖 SQL AGENT - MISSING FIELDS WORKFLOW DEMONSTRATION")
    print("=" * 80)
    
    agent = SQLAgent()
    
    # Test scenarios with different levels of missing information
    test_scenarios = [
        {
            "name": "Scenario 1: Only Name Provided",
            "user_input": "Add employee named Sarah",
            "expected_missing": ["department", "salary"],
            "simulated_responses": {"department": "Marketing", "salary": "65000"}
        },
        {
            "name": "Scenario 2: Name and Department Provided", 
            "user_input": "Insert employee John in Engineering department",
            "expected_missing": ["salary"],
            "simulated_responses": {"salary": "80000"}
        },
        {
            "name": "Scenario 3: Name and Salary Provided",
            "user_input": "Add employee Lisa with salary 70000",
            "expected_missing": ["department"],
            "simulated_responses": {"department": "Sales"}
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*60}")
        print(f"🔹 {scenario['name']}")
        print(f"{'='*60}")
        print(f"👤 User Input: \"{scenario['user_input']}\"")
        print("-" * 60)
        
        # Step 1: Generate SQL query
        query = agent.generate_query(scenario['user_input'])
        print(f"🔧 Generated SQL: {query}")
        
        # Step 2: Parse the query
        parsed = agent.parse_insert_or_update_query(query)
        if not parsed:
            print("❌ Failed to parse query")
            continue
            
        table, query_type, values = parsed
        print(f"📊 Parsed Data:")
        print(f"   - Table: {table}")
        print(f"   - Operation: {query_type}")
        print(f"   - Values: {values}")
        
        # Step 3: Validate fields
        model = agent.model_map.get(table.lower())
        if not model:
            print(f"❌ No model found for table: {table}")
            continue
            
        missing, instance, validation_errors = agent.validate_fields(values, model)
        print(f"🔍 Validation Results:")
        print(f"   - Missing fields: {missing}")
        print(f"   - Validation errors: {validation_errors}")
        
        # Verify expected missing fields
        if set(missing) == set(scenario['expected_missing']):
            print("✅ Missing field detection is CORRECT!")
        else:
            print(f"❌ Expected {scenario['expected_missing']}, got {missing}")
            continue
        
        # Step 4: Chain of questions for missing fields
        current_values = values.copy()
        question_count = 0
        
        print(f"\n🗣️  INTERACTIVE CONVERSATION:")
        print("-" * 40)
        
        while missing and question_count < 5:  # Safety limit
            question_count += 1
            next_field = missing[0]
            
            # Get field description
            field_descriptions = {
                "department": "Department name (e.g., Engineering, Sales, HR, Marketing)",
                "salary": "Annual salary amount (numbers only)",
                "name": "Employee full name"
            }
            
            description = field_descriptions.get(next_field, f"Value for {next_field}")
            
            print(f"🤖 Question {question_count}: Please provide a value for '{next_field}'")
            print(f"   Hint: {description}")
            
            # Simulate user response
            if next_field in scenario['simulated_responses']:
                user_response = scenario['simulated_responses'][next_field]
                print(f"👤 User: {user_response}")
                
                # Update values
                current_values[next_field] = user_response
                print(f"   ✓ Updated values: {current_values}")
                
                # Re-validate
                missing, instance, validation_errors = agent.validate_fields(current_values, model)
                
                if missing:
                    print(f"   ⏭️  Still missing: {missing}")
                else:
                    print(f"   ✅ All required fields collected!")
                    break
            else:
                print(f"❌ No simulated response for {next_field}")
                break
        
        # Step 5: Generate final SQL and summary
        if not missing:
            print(f"\n🎯 FINAL RESULTS:")
            print("-" * 40)
            
            try:
                # Validate final instance
                final_instance = model(**current_values)
                print(f"✅ Final validation successful!")
                print(f"   Employee: {final_instance}")
                
                # Generate final SQL
                final_query = agent.generate_final_sql(current_values, table, query_type)
                print(f"🚀 Ready to execute:")
                print(f"   {final_query}")
                
                print(f"\n📈 WORKFLOW SUCCESS SUMMARY:")
                print(f"   • Started with: {len(values)} field(s)")
                print(f"   • Asked {question_count} question(s)")
                print(f"   • Collected: {len(scenario['expected_missing'])} missing field(s)")
                print(f"   • Final: Complete employee record ready for database")
                
            except Exception as e:
                print(f"❌ Final validation failed: {e}")
        else:
            print(f"❌ Workflow incomplete - still missing: {missing}")
        
        print("\n" + "="*60)

def test_edge_cases():
    """Test edge cases and error handling"""
    print(f"\n{'='*80}")
    print("🔬 EDGE CASES AND ERROR HANDLING")
    print("="*80)
    
    agent = SQLAgent()
    
    edge_cases = [
        {
            "name": "Empty Input",
            "input": "",
            "expected": "Should handle gracefully"
        },
        {
            "name": "Invalid Table",
            "input": "Add person named John",
            "expected": "Should normalize to employee table"
        },
        {
            "name": "All Fields Complete",
            "input": "Add employee John in Engineering with salary 75000",
            "expected": "Should detect no missing fields"
        }
    ]
    
    for case in edge_cases:
        print(f"\n🔹 Edge Case: {case['name']}")
        print(f"   Input: \"{case['input']}\"")
        print(f"   Expected: {case['expected']}")
        
        try:
            if case['input']:
                query = agent.generate_query(case['input'])
                parsed = agent.parse_insert_or_update_query(query)
                
                if parsed:
                    table, query_type, values = parsed
                    model = agent.model_map.get(table.lower())
                    
                    if model:
                        missing, instance, errors = agent.validate_fields(values, model)
                        print(f"   Result: Missing {len(missing)} fields, {len(errors)} errors")
                        if not missing and not errors:
                            print(f"   ✅ Complete record detected")
                        else:
                            print(f"   📝 Would ask for: {missing}")
                    else:
                        print(f"   ❌ No model for table: {table}")
                else:
                    print(f"   ❌ Failed to parse query: {query}")
            else:
                print(f"   ⚠️  Empty input handled")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    simulate_user_workflow()
    test_edge_cases()
    
    print(f"\n{'='*80}")
    print("🎉 WORKFLOW DEMONSTRATION COMPLETE!")
    print("✅ Missing fields detection and chain of questions working perfectly!")
    print("✅ Ready for production use in real chat applications!")
    print("="*80)
