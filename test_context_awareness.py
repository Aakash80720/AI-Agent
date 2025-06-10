#!/usr/bin/env python3
"""
Test script to verify context awareness functionality of the SQL Agent
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from ai_agent_service.sqlagent import SQLAgent, Chat

def test_context_awareness():
    """Test context awareness features"""
    print("🧠 Testing Context Awareness Features")
    print("=" * 50)
    
    # Initialize the chat system
    chat = Chat()
    thread_id = "test_context_001"
    
    # Test 1: Insert a record and check context
    print("\n1️⃣ Test: Insert Employee Record")
    response1 = chat.run(thread_id, "Insert a new employee named John Doe in Engineering department with salary 75000")
    print("Response:", response1.get("execution_result", "No result"))
    
    # Check context after insert
    agent = chat.agent
    context = agent.conversation_context
    print(f"Last operation: {context['last_operation']}")
    print(f"Last table: {context['last_table']}")
    print(f"Last values: {context['last_values']}")
    
    # Test 2: Use contextual references
    print("\n2️⃣ Test: Contextual Query (referring to previous insert)")
    response2 = chat.run(thread_id, "Show me that record I just added")
    print("Response:", response2.get("execution_result", "No result"))
    
    # Test 3: Department-based context
    print("\n3️⃣ Test: Department Context")
    response3 = chat.run(thread_id, "Show all employees in the same department")
    print("Response:", response3.get("execution_result", "No result"))
    
    # Test 4: Get context suggestions
    print("\n4️⃣ Test: Context Suggestions")
    suggestions = agent.get_context_suggestions("add another employee")
    print("Suggestions:", suggestions)
    
    # Test 5: Check operation history
    print("\n5️⃣ Test: Operation History")
    print(f"Total operations: {len(context['operation_history'])}")
    for i, op in enumerate(context['operation_history'][-3:], 1):
        print(f"  {i}. {op['operation']} on {op['table']} at {op['timestamp'][:19]}")
    
    # Test 6: User patterns
    print("\n6️⃣ Test: User Patterns")
    patterns = context['user_patterns']
    print(f"Frequent operations: {patterns['frequent_operations']}")
    print(f"Preferred departments: {patterns['preferred_departments']}")
    print(f"Table usage: {context['table_usage_count']}")
    
    print("\n✅ Context Awareness Test Completed!")

if __name__ == "__main__":
    test_context_awareness()
