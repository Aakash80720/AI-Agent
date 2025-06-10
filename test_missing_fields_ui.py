#!/usr/bin/env python3
"""
Test script to verify the missing fields functionality works correctly
between the backend Chat class and the frontend UI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent_service.sqlagent import Chat
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_missing_fields_workflow():
    """Test the complete missing fields workflow"""
    print("🧪 Testing Missing Fields Workflow")
    print("=" * 50)
    
    # Initialize chat
    chat = Chat()
    thread_id = "test_missing_fields"
    
    print("\n1️⃣ Testing incomplete employee insert (missing department)...")
    
    # Step 1: Send incomplete insert request
    user_input_1 = "Insert a new employee with name 'John Doe' and salary 70000"
    print(f"👤 User: {user_input_1}")
    
    response_1 = chat.run(thread_id, user_input_1)
    print(f"🤖 Bot Response: {response_1}")
    
    # Check if the response is asking for missing fields
    if isinstance(response_1, dict):
        if "message" in response_1 and "Please provide" in response_1["message"]:
            print("✅ PASS: Bot correctly detected missing field and asked for it")
            missing_field_request = response_1["message"]
            print(f"📝 Missing field request: {missing_field_request}")
            
            # Step 2: Provide the missing field value
            user_input_2 = "Engineering"  # Providing the department value
            print(f"\n2️⃣ Providing missing field value...")
            print(f"👤 User: {user_input_2}")
            
            response_2 = chat.run(thread_id, user_input_2)
            print(f"🤖 Bot Response: {response_2}")
            
            # Check if the insertion was completed
            if isinstance(response_2, dict):
                if "execution_result" in response_2 and "successfully" in str(response_2["execution_result"]).lower():
                    print("✅ PASS: Bot successfully completed the insertion after receiving missing field")
                    return True
                elif "final_query" in response_2:
                    print(f"📊 Generated SQL: {response_2['final_query']}")
                    print("✅ PASS: Bot generated final SQL query")
                    return True
                else:
                    print(f"❌ FAIL: Unexpected response format: {response_2}")
                    return False
            else:
                print(f"❌ FAIL: Expected dict response, got: {type(response_2)}")
                return False
        else:
            print(f"❌ FAIL: Bot did not ask for missing field. Response: {response_1}")
            return False
    else:
        print(f"❌ FAIL: Expected dict response, got: {type(response_1)}")
        return False

def test_complete_workflow():
    """Test a complete workflow with multiple missing fields"""
    print("\n🧪 Testing Complete Workflow with Multiple Missing Fields")
    print("=" * 60)
    
    chat = Chat()
    thread_id = "test_complete_workflow"
    
    print("\n1️⃣ Testing insert with only name (missing department and salary)...")
    
    user_input = "Add employee Jane Smith"
    print(f"👤 User: {user_input}")
    
    response = chat.run(thread_id, user_input)
    print(f"🤖 Bot Response: {response}")
    
    if isinstance(response, dict) and "message" in response and "Please provide" in response["message"]:
        print("✅ PASS: Bot correctly detected missing fields")
        return True
    else:
        print(f"❌ FAIL: Bot did not detect missing fields properly")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Missing Fields UI Tests")
    print("=" * 50)
    
    # Test 1: Basic missing field workflow
    test1_result = test_missing_fields_workflow()
    
    # Test 2: Complete workflow
    test2_result = test_complete_workflow()
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    print(f"Test 1 (Missing Field Workflow): {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"Test 2 (Complete Workflow): {'✅ PASS' if test2_result else '❌ FAIL'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed! Missing fields functionality is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
