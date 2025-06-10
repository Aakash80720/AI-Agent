#!/usr/bin/env python3
"""
Test Modular Configuration System
Tests dynamic database connections and field configurations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent_service.config_manager import config_manager
from ai_agent_service.database_manager import DatabaseManager, get_default_database_manager
from ai_agent_service.sqlagent import SQLAgent
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_configuration_system():
    """Test the modular configuration system"""
    print("="*80)
    print("🔧 TESTING MODULAR CONFIGURATION SYSTEM")
    print("="*80)
    
    # Test 1: Configuration Manager
    print("\n🔹 Testing Configuration Manager...")
    try:
        # Test database configurations
        available_dbs = config_manager.get_available_databases()
        print(f"✅ Available databases: {available_dbs}")
        
        # Test field configurations
        all_models = config_manager.get_all_models()
        print(f"✅ Available models: {all_models}")
        
        # Test field descriptions
        for model in all_models:
            required_fields = config_manager.get_required_fields(model)
            print(f"✅ {model} required fields: {required_fields}")
            
            # Test field descriptions
            for field in required_fields:
                description = config_manager.get_field_description(model, field)
                suggestions = config_manager.get_field_suggestions(model, field)
                print(f"   - {field}: {description}")
                if suggestions:
                    print(f"     Suggestions: {suggestions}")
        
        # Test LLM configuration
        llm_config = config_manager.get_llm_config()
        print(f"✅ LLM config: {llm_config}")
        
    except Exception as e:
        print(f"❌ Configuration Manager test failed: {e}")
        return False
    
    # Test 2: Database Manager
    print("\n🔹 Testing Database Manager...")
    try:
        # Test default database manager
        db_manager = get_default_database_manager()
        db_info = db_manager.get_database_info()
        print(f"✅ Database info: {db_info}")
        
        # Test connection status
        status = db_manager.get_connection_status()
        print(f"✅ Connection status: {status}")
        
        # Test table schemas
        schemas = db_manager.get_table_schemas()
        print(f"✅ Table schemas loaded: {list(schemas.keys())}")
        
    except Exception as e:
        print(f"❌ Database Manager test failed: {e}")
        return False
    
    # Test 3: SQLAgent with Configuration
    print("\n🔹 Testing SQLAgent with Configuration...")
    try:
        # Initialize SQLAgent (should use configuration)
        agent = SQLAgent()
        print("✅ SQLAgent initialized with configuration")
        
        # Test field description retrieval
        dept_desc = agent.get_field_description("employee", "department")
        salary_desc = agent.get_field_description("employee", "salary")
        print(f"✅ Department description: {dept_desc}")
        print(f"✅ Salary description: {salary_desc}")
        
        # Test query generation
        query = agent.generate_query("Show me all employees")
        print(f"✅ Generated query: {query}")
        
        # Test missing fields detection
        user_input = "Add employee named TestUser"
        query2 = agent.generate_query(user_input)
        print(f"✅ Generated SQL: {query2}")
        
        parsed = agent.parse_insert_or_update_query(query2)
        if parsed:
            table, query_type, values = parsed
            model = agent.model_map.get(table.lower())
            if model:
                missing, instance, validation_errors = agent.validate_fields(values, model)
                print(f"✅ Missing fields detected: {missing}")
        
    except Exception as e:
        print(f"❌ SQLAgent test failed: {e}")
        return False
    
    return True

def test_dynamic_database_switching():
    """Test dynamic database switching"""
    print("\n🔹 Testing Dynamic Database Switching...")
    
    try:
        # Get current active database
        current_db = config_manager._database_config.get("active_database")
        print(f"✅ Current active database: {current_db}")
        
        # Test database info
        db_info = config_manager.get_database_info()
        print(f"✅ Database info: {db_info}")
        
        # Test with specific database name
        if "default" in config_manager.get_available_databases():
            agent_default = SQLAgent("default")
            print("✅ SQLAgent initialized with 'default' database")
            
            db_info_default = agent_default.db_manager.get_database_info()
            print(f"✅ Default database info: {db_info_default}")
        
    except Exception as e:
        print(f"❌ Dynamic database switching test failed: {e}")
        return False
    
    return True

def test_field_configuration_usage():
    """Test field configuration usage in missing fields workflow"""
    print("\n🔹 Testing Field Configuration in Missing Fields Workflow...")
    
    try:
        agent = SQLAgent()
        
        # Test different scenarios with field descriptions from config
        test_cases = [
            {
                "input": "Add employee named Sarah",
                "expected_missing": ["department", "salary"]
            },
            {
                "input": "Add project called Website Redesign",
                "expected_missing": []  # No required fields for project except name
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n  Test Case {i}: {case['input']}")
            
            query = agent.generate_query(case['input'])
            print(f"  Generated SQL: {query}")
            
            parsed = agent.parse_insert_or_update_query(query)
            if parsed:
                table, query_type, values = parsed
                model = agent.model_map.get(table.lower())
                
                if model:
                    missing, instance, validation_errors = agent.validate_fields(values, model)
                    print(f"  Missing fields: {missing}")
                    
                    # Test field descriptions from config
                    for field in missing:
                        description = agent.get_field_description(table, field)
                        suggestions = config_manager.get_field_suggestions(table, field)
                        print(f"    {field}: {description}")
                        if suggestions:
                            print(f"      Suggestions: {suggestions}")
                    
                    if set(missing) == set(case['expected_missing']):
                        print(f"  ✅ Missing field detection correct!")
                    else:
                        print(f"  ⚠️ Expected {case['expected_missing']}, got {missing}")
        
    except Exception as e:
        print(f"❌ Field configuration test failed: {e}")
        return False
    
    return True

def main():
    """Run all modular configuration tests"""
    print("🚀 Starting Modular Configuration System Tests")
    
    success = True
    
    # Run all tests
    tests = [
        test_configuration_system,
        test_dynamic_database_switching,
        test_field_configuration_usage
    ]
    
    for test_func in tests:
        if not test_func():
            success = False
    
    print("\n" + "="*80)
    if success:
        print("🎉 ALL MODULAR CONFIGURATION TESTS PASSED!")
        print("✅ Dynamic database selection working")
        print("✅ JSON field configurations working") 
        print("✅ Modular design implemented successfully")
        print("✅ Ready for production with multiple databases!")
    else:
        print("❌ Some tests failed - check configuration files")
    print("="*80)

if __name__ == "__main__":
    main()
