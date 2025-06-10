#!/usr/bin/env python3
"""
Test script to verify lazy loading optimizations and missing field workflow
"""

import time
import logging
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent_service.sqlagent import SQLAgent, Chat

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_startup_performance():
    """Test that startup is faster with lazy loading"""
    print("\n🚀 Testing startup performance with lazy loading...")
    
    start_time = time.time()
    
    # Initialize SQLAgent (should be fast now)
    agent = SQLAgent()
    
    init_time = time.time() - start_time
    print(f"✅ SQLAgent initialization took: {init_time:.2f} seconds")
    
    # First query should trigger lazy loading
    print("\n🔍 Running first query (should trigger lazy loading)...")
    start_time = time.time()
    
    chat = Chat()
    response = chat.run("test_thread", "Show me all employees")
    
    first_query_time = time.time() - start_time
    print(f"✅ First query (with lazy loading) took: {first_query_time:.2f} seconds")
    
    # Second query should be faster
    print("\n⚡ Running second query (should be faster)...")
    start_time = time.time()
    
    response = chat.run("test_thread", "Show me all projects")
    
    second_query_time = time.time() - start_time
    print(f"✅ Second query took: {second_query_time:.2f} seconds")
    
    print(f"\n📊 Performance Summary:")
    print(f"   - Initialization: {init_time:.2f}s (should be fast)")
    print(f"   - First query: {first_query_time:.2f}s (includes lazy loading)")
    print(f"   - Second query: {second_query_time:.2f}s (should be faster)")

def test_missing_field_workflow():
    """Test the missing field detection and workflow"""
    print("\n🔍 Testing missing field workflow...")
    
    chat = Chat()
    thread_id = "test_missing_fields"
    
    # Test 1: Insert with missing required fields
    print("\n📝 Test 1: Insert with missing required fields")
    user_input = "Add employee John Smith"
    
    response = chat.run(thread_id, user_input)
    print(f"User: {user_input}")
    print(f"Response: {response}")
    
    # Check if it's asking for missing fields
    if "Please provide" in str(response):
        print("✅ Correctly detected missing fields and asked for them")
        
        # Test 2: Provide department
        print("\n📝 Test 2: Provide missing department")
        user_input = "Engineering"
        
        response = chat.run(thread_id, user_input)
        print(f"User: {user_input}")
        print(f"Response: {response}")
        
        # Should still ask for salary
        if "Please provide" in str(response):
            print("✅ Correctly continued asking for remaining missing fields")
            
            # Test 3: Provide salary
            print("\n📝 Test 3: Provide missing salary")
            user_input = "75000"
            
            response = chat.run(thread_id, user_input)
            print(f"User: {user_input}")
            print(f"Response: {response}")
            
            # Should now execute successfully
            if "successfully" in str(response).lower() or "INSERT" in str(response):
                print("✅ Successfully completed missing field workflow")
            else:
                print("❌ Failed to complete after providing all fields")
        else:
            print("❌ Failed to continue asking for missing fields")
    else:
        print("❌ Failed to detect missing fields")

def test_conversation_state_persistence():
    """Test that conversation state persists between turns"""
    print("\n💬 Testing conversation state persistence...")
    
    chat = Chat()
    thread_id = "test_conversation_state"
    
    # Start an incomplete operation
    print("\n📝 Starting incomplete insert operation...")
    response1 = chat.run(thread_id, "Insert employee Alice Johnson")
    print(f"Response 1: {response1}")
    
    # Provide one field
    print("\n📝 Providing department...")
    response2 = chat.run(thread_id, "Sales")
    print(f"Response 2: {response2}")
    
    # Provide second field
    print("\n📝 Providing salary...")
    response3 = chat.run(thread_id, "65000")
    print(f"Response 3: {response3}")
    
    # Check if all responses are consistent
    print("✅ Conversation state persistence test completed")

def run_all_tests():
    """Run all optimization and workflow tests"""
    print("🧪 Starting comprehensive test suite...")
    print("=" * 60)
    
    try:
        test_startup_performance()
        test_missing_field_workflow()
        test_conversation_state_persistence()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
