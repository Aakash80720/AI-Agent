#!/usr/bin/env python3
"""
Demonstration script showcasing the Context-Aware SQL Agent features
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from ai_agent_service.sqlagent import SQLAgent, Chat

def demonstrate_context_awareness():
    """Demonstrate key context awareness features"""
    print("🎯 Context-Aware SQL Agent Demonstration")
    print("=" * 60)
    
    # Initialize the chat system
    chat = Chat()
    thread_id = "demo_001"
    
    print("\n🚀 **FEATURE 1: Smart Query Generation**")
    print("-" * 40)
    response1 = chat.run(thread_id, "Add a new employee named Sarah Wilson in Marketing with salary 68000")
    print(f"User: Add a new employee named Sarah Wilson in Marketing with salary 68000")
    print(f"Result: {response1.get('execution_result', 'No result')}")
    
    print("\n🧠 **FEATURE 2: Contextual References**")
    print("-" * 40)
    response2 = chat.run(thread_id, "Show me that record")
    print(f"User: Show me that record")
    print(f"Result: {response2.get('execution_result', 'No result')}")
    
    print("\n🔄 **FEATURE 3: Pattern Learning**")
    print("-" * 40)
    response3 = chat.run(thread_id, "Show other employees in the same department")
    print(f"User: Show other employees in the same department")
    print(f"Result: {response3.get('execution_result', 'No result')}")
    
    print("\n💡 **FEATURE 4: Intelligent Suggestions**")
    print("-" * 40)
    agent = chat.agent
    suggestions = agent.get_context_suggestions("add another employee")
    print(f"Query: 'add another employee'")
    print(f"Suggestions: {suggestions}")
    
    print("\n📊 **FEATURE 5: Context Analytics**")
    print("-" * 40)
    context = agent.conversation_context
    print(f"Operations performed: {len(context['operation_history'])}")
    print(f"Most used table: {max(context['table_usage_count'], key=context['table_usage_count'].get)}")
    print(f"User patterns:")
    print(f"  - Frequent operations: {context['user_patterns']['frequent_operations']}")
    print(f"  - Preferred departments: {context['user_patterns']['preferred_departments']}")
    print(f"  - Table usage: {context['table_usage_count']}")
    
    print("\n✨ **FEATURE 6: Smart Follow-up Suggestions**")
    print("-" * 40)
    if context['last_operation'] == 'select':
        print("💡 Since you just viewed data, you might want to:")
        print("   • Add a similar record")
        print("   • Update existing data")
        print("   • Export the results")
    elif context['last_operation'] == 'insert':
        print("💡 Since you just added data, you might want to:")
        print("   • View the record you added")
        print("   • Add another similar record")
        print("   • Check related data")
    
    print(f"\n🎉 **Context Awareness Demo Completed!**")
    print(f"The SQL Agent learned from {len(context['operation_history'])} interactions")
    print(f"and can now provide personalized assistance based on your patterns.")

if __name__ == "__main__":
    demonstrate_context_awareness()
