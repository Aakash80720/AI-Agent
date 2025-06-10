#!/usr/bin/env python3
"""
Debug script to test field validation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent_service.sqlagent import SQLAgent, Employee
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_validation():
    """Debug the validation logic"""
    print("=" * 60)
    print("Debug Field Validation")
    print("=" * 60)
    
    # Test data with NULL values (as parsed from SQL)
    test_values = {
        'name': 'Aakash', 
        'department': None, 
        'salary': None, 
        'hire_date': None
    }
    
    print(f"Test Values: {test_values}")
    
    # Test direct model validation
    try:
        instance = Employee(**test_values)
        print("✅ Direct model validation passed")
        print(f"Instance: {instance}")
    except Exception as e:
        print("❌ Direct model validation failed:")
        print(f"Error: {e}")
        if hasattr(e, 'errors'):
            for error in e.errors():
                print(f"  - {error}")
    
    print("\n" + "-" * 40)
    
    # Test agent validation
    agent = SQLAgent()
    missing, instance, validation_errors = agent.validate_fields(test_values, Employee)
    
    print(f"Agent validation results:")
    print(f"  Missing fields: {missing}")
    print(f"  Instance: {instance}")
    print(f"  Validation errors: {validation_errors}")
    
    print("\n" + "-" * 40)
    
    # Test with only required fields
    required_values = {
        'name': 'Aakash',
        'department': 'Engineering', 
        'salary': 50000
    }
    
    print(f"Required Values Test: {required_values}")
    
    try:
        instance = Employee(**required_values)
        print("✅ Required fields model validation passed")
        print(f"Instance: {instance}")
    except Exception as e:
        print("❌ Required fields model validation failed:")
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_validation()
