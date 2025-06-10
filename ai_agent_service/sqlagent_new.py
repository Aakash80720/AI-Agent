import functools
from datetime import datetime
import json
import re
import pandas as pd
from typing import Annotated, Optional, TypedDict, Dict, List, Any, Union
from decimal import Decimal
import logging

from langchain_ollama import ChatOllama
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, add_messages

from langchain_core.messages.tool import ToolCall
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain.memory import ConversationBufferMemory
from langchain.chains.llm import LLMChain
from pydantic import BaseModel, Field, validator
from sqlalchemy import MetaData, Table, inspect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Employee(BaseModel):
    """Employee model with validation"""
    id: Optional[int] = Field(None, description="Auto-generated employee ID")
    name: str = Field(..., description="Employee full name", min_length=1, max_length=100)
    department: Optional[str] = Field(None, description="Department name", max_length=50)
    salary: Optional[float] = Field(None, description="Employee salary", ge=0)
    hire_date: Optional[str] = Field(None, description="Hire date in YYYY-MM-DD format")
    
    @validator('hire_date')
    def validate_hire_date(cls, v):
        if v is not None and v.strip():
            try:
                # Validate date format
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError('hire_date must be in YYYY-MM-DD format')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('name is required and cannot be empty')
        return v.strip()

class Project(BaseModel):
    """Project model with validation"""
    id: Optional[int] = Field(None, description="Auto-generated project ID")
    name: str = Field(..., description="Project name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Project description", max_length=500)
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")
    budget: Optional[float] = Field(None, description="Project budget", ge=0)
    department: Optional[str] = Field(None, description="Department name", max_length=50)
    
    @validator('start_date', 'end_date')
    def validate_dates(cls, v):
        if v is not None and v.strip():
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('name is required and cannot be empty')
        return v.strip()

class State(TypedDict):
    """Enhanced state for context-aware processing"""
    messages: Annotated[list, add_messages]
    user_intent: str
    table: str
    query_type: str
    partial_values: Dict[str, Any]
    missing_fields: List[str]
    generated_query: str
    final_query: str
    execution_result: str
    summary: str
    conversation_context: Dict[str, Any]
    validation_errors: List[str]
    operation_count: int

class SQLAgent:
    """Enterprise-level SQL Agent with dynamic validation and context awareness"""
    
    # Table name normalization mapping
    TABLE_ALIASES = {
        'employees': 'employee',
        'emp': 'employee',
        'staff': 'employee',
        'workers': 'employee',
        'projects': 'project',
        'proj': 'project',
        'tasks': 'project'
    }
    
    @staticmethod
    @functools.lru_cache(maxsize=1)
    def get_llm():
        """Initialize local LLM with optimized settings"""
        llm = ChatOllama(
            model="devstral", 
            temperature=0.1,  # Lower temperature for more consistent SQL generation
            num_ctx=4096,     # Increased context window
            verbose=False, 
            keep_alive=1,
            top_p=0.9,
            top_k=40
        )
        return llm
    
    @staticmethod
    @functools.lru_cache(maxsize=1)
    def get_sql_database():
        """Initialize database connection with proper configuration"""
        try:
            db = SQLDatabase.from_uri("sqlite:///../test.db")
            return db
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def __init__(self):
        self.llm = self.get_llm()
        self.db = self.get_sql_database()
        self.operation_count = {}  # Track operations to prevent duplicates
        
        # Get actual table schema dynamically
        self.table_schemas = self._get_table_schemas()
        logger.info(f"Loaded table schemas: {list(self.table_schemas.keys())}")
        
        # Enhanced system prompt for better table name resolution
        self.system_prompt = f"""
You are an expert SQL assistant with access to a SQLite database containing the following EXACT tables:
- employee (columns: id, name, department, salary, hire_date)
- project (columns: id, name, description, start_date, end_date, budget, department)

CRITICAL RULES:
1. Use EXACT table names: 'employee' (NOT employees, staff, workers) and 'project' (NOT projects)
2. Always include id field for INSERT operations (it's auto-incremented)
3. For text values, use single quotes
4. For dates, use 'YYYY-MM-DD' format
5. Return ONLY the SQL query without explanations or formatting
6. Never use plural forms of table names

Current date: {datetime.now().strftime('%Y-%m-%d')}
"""
        
        # Enhanced prompt template with strict table name enforcement
        self.DB_structure_prompt = PromptTemplate.from_template(
            template=(
                f"{self.system_prompt}\n\n"
                "Database Schema:\n{{table_info}}\n\n"
                "Available Tables: {{table_names}}\n\n"
                "IMPORTANT: Use ONLY these exact table names: employee, project\n"
                "Question: {{input}}\n"
                "SQL Query (plain text only):"
            )
        )
        
        self.generated_query_chain = create_sql_query_chain(
            llm=self.llm,
            db=self.db,
            prompt=self.DB_structure_prompt
        )
        
        # Dynamic model mapping
        self.model_map = {
            "employee": Employee,
            "project": Project
        }
        
        # Initialize conversation context
        self.conversation_context = {
            "last_operation": None,
            "last_table": None,
            "user_preferences": {},
            "operation_history": []
        }

    def _get_table_schemas(self) -> Dict[str, Dict]:
        """Dynamically get table schemas from database"""
        schemas = {}
        try:
            # Get table names
            tables = self.db.get_usable_table_names()
            
            for table_name in tables:
                # Get column information
                inspector = inspect(self.db._engine)
                columns = inspector.get_columns(table_name)
                schemas[table_name] = {
                    'columns': [col['name'] for col in columns],
                    'types': {col['name']: str(col['type']) for col in columns}
                }
        except Exception as e:
            logger.error(f"Failed to get table schemas: {e}")
            # Fallback to known schemas
            schemas = {
                'employee': {
                    'columns': ['id', 'name', 'department', 'salary', 'hire_date'],
                    'types': {'id': 'INTEGER', 'name': 'TEXT', 'department': 'TEXT', 'salary': 'REAL', 'hire_date': 'TEXT'}
                },
                'project': {
                    'columns': ['id', 'name', 'description', 'start_date', 'end_date', 'budget', 'department'],
                    'types': {'id': 'INTEGER', 'name': 'TEXT', 'description': 'TEXT', 'start_date': 'TEXT', 'end_date': 'TEXT', 'budget': 'REAL', 'department': 'TEXT'}
                }
            }
        return schemas

    def normalize_table_name(self, table_name: str) -> str:
        """Normalize table names to prevent plural/alias issues"""
        if not table_name:
            return ""
        
        table_lower = table_name.lower().strip()
        
        # Direct mapping from aliases
        if table_lower in self.TABLE_ALIASES:
            return self.TABLE_ALIASES[table_lower]
        
        # Check if it's already a valid table name
        if table_lower in self.table_schemas:
            return table_lower
        
        # Fallback: check if it's a substring match
        for valid_table in self.table_schemas.keys():
            if table_lower in valid_table or valid_table in table_lower:
                return valid_table
        
        # Default fallback
        return table_name

    def enhance_query_for_table_names(self, query: str) -> str:
        """Pre-process query to fix common table name issues"""
        # Replace common table name variations
        replacements = {
            r'\bemployees\b': 'employee',
            r'\bprojects\b': 'project',
            r'\bemp\b': 'employee',
            r'\bstaff\b': 'employee',
            r'\bworkers\b': 'employee'
        }
        
        enhanced_query = query
        for pattern, replacement in replacements.items():
            enhanced_query = re.sub(pattern, replacement, enhanced_query, flags=re.IGNORECASE)
        
        return enhanced_query

    def generate_query(self, prompt: str) -> str:
        """Generate SQL query with enhanced table name handling"""
        try:
            # Pre-process prompt for better table name resolution
            enhanced_prompt = f"""
Based on the user request: "{prompt}"

Use ONLY these exact table names:
- employee (for any employee/staff/worker related queries)
- project (for any project/task related queries)

Generate the SQL query:
"""
            
            result = self.generated_query_chain.invoke({"question": enhanced_prompt})
            result = str(result).strip()
            
            # Clean up result
            if result.startswith("```"):
                result = result.lstrip("`").replace("sql", "", 1).strip()
                result = result.rstrip("`").strip()
            
            # Post-process to fix table names
            result = self.enhance_query_for_table_names(result)
            
            logger.info(f"Generated query: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            return f"-- Error generating query: {str(e)}"

    def execute_query(self, query: str) -> Union[str, pd.DataFrame]:
        """Execute SQL query with proper error handling and result formatting"""
        try:
            # Validate query before execution
            if not query or query.strip().startswith('--'):
                return "Invalid query provided"
            
            # Execute query
            result = self.db.run(query)
            
            # For SELECT queries, return as DataFrame
            if query.strip().upper().startswith('SELECT'):
                try:
                    # Convert to DataFrame for better handling
                    import io
                    if isinstance(result, str) and result:
                        # Try to parse as table data
                        lines = result.strip().split('\n')
                        if len(lines) > 1:
                            # Create DataFrame from string result
                            data = []
                            headers = None
                            for line in lines:
                                if '|' in line:
                                    row = [cell.strip() for cell in line.split('|')]
                                    if headers is None:
                                        headers = row
                                    else:
                                        data.append(row)
                            
                            if headers and data:
                                df = pd.DataFrame(data, columns=headers)
                                return df
                    
                    # Fallback: execute with pandas
                    df = pd.read_sql_query(query, self.db._engine)
                    return df
                    
                except Exception as e:
                    logger.warning(f"DataFrame conversion failed: {e}")
                    return result
            else:
                # For non-SELECT queries, return success message with result
                return f"Query executed successfully. Result: {result}"
                
        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Enhanced query parsing to determine intent and extract components"""
        query_upper = query.upper().strip()
        
        intent_info = {
            "operation": "unknown",
            "table": None,
            "columns": [],
            "values": {},
            "conditions": []
        }
        
        # Determine operation type
        if query_upper.startswith('SELECT'):
            intent_info["operation"] = "select"
        elif query_upper.startswith('INSERT'):
            intent_info["operation"] = "insert"
        elif query_upper.startswith('UPDATE'):
            intent_info["operation"] = "update"
        elif query_upper.startswith('DELETE'):
            intent_info["operation"] = "delete"
        
        # Extract table name with normalization
        table_patterns = [
            r'FROM\s+(\w+)',
            r'INTO\s+(\w+)',
            r'UPDATE\s+(\w+)',
            r'DELETE\s+FROM\s+(\w+)'
        ]
        
        for pattern in table_patterns:
            match = re.search(pattern, query_upper)
            if match:
                raw_table = match.group(1).lower()
                intent_info["table"] = self.normalize_table_name(raw_table)
                break
        
        return intent_info

    def parse_insert_or_update_query(self, query: str) -> Optional[tuple]:
        """Enhanced parsing for INSERT and UPDATE queries with better error handling"""
        try:
            query = query.strip()
            
            # Parse INSERT queries
            insert_match = re.search(r'INSERT\s+INTO\s+(\w+)', query, re.IGNORECASE)
            if insert_match:
                table = self.normalize_table_name(insert_match.group(1))
                
                # Extract columns and values
                col_match = re.search(r'\(([^)]+)\)\s+VALUES', query, re.IGNORECASE)
                val_match = re.search(r'VALUES\s*\(([^)]+)\)', query, re.IGNORECASE)
                
                if col_match and val_match:
                    columns = [c.strip().strip("'\"") for c in col_match.group(1).split(',')]
                    values_str = val_match.group(1)
                    
                    # Safely parse values
                    values = []
                    current_val = ""
                    in_quotes = False
                    quote_char = None
                    
                    for char in values_str:
                        if char in ["'", '"'] and not in_quotes:
                            in_quotes = True
                            quote_char = char
                        elif char == quote_char and in_quotes:
                            in_quotes = False
                            quote_char = None
                        elif char == ',' and not in_quotes:
                            values.append(self._parse_value(current_val.strip()))
                            current_val = ""
                            continue
                        current_val += char
                    
                    # Add the last value
                    if current_val.strip():
                        values.append(self._parse_value(current_val.strip()))
                    
                    # Filter out id field for auto-increment
                    filtered_data = {}
                    for col, val in zip(columns, values):
                        if col.lower() != 'id':  # Skip auto-increment ID
                            filtered_data[col] = val
                    
                    return table, "insert", filtered_data
            
            # Parse UPDATE queries
            update_match = re.search(r'UPDATE\s+(\w+)', query, re.IGNORECASE)
            if update_match:
                table = self.normalize_table_name(update_match.group(1))
                
                # Extract SET clause
                set_match = re.search(r'SET\s+(.+?)(?:\s+WHERE|$)', query, re.IGNORECASE | re.DOTALL)
                if set_match:
                    set_clause = set_match.group(1)
                    assignments = []
                    
                    # Split assignments carefully
                    current_assignment = ""
                    in_quotes = False
                    quote_char = None
                    
                    for char in set_clause:
                        if char in ["'", '"'] and not in_quotes:
                            in_quotes = True
                            quote_char = char
                        elif char == quote_char and in_quotes:
                            in_quotes = False
                            quote_char = None
                        elif char == ',' and not in_quotes:
                            assignments.append(current_assignment.strip())
                            current_assignment = ""
                            continue
                        current_assignment += char
                    
                    if current_assignment.strip():
                        assignments.append(current_assignment.strip())
                    
                    # Parse key-value pairs
                    data = {}
                    for assignment in assignments:
                        if '=' in assignment:
                            key, val = assignment.split('=', 1)
                            key = key.strip()
                            val = self._parse_value(val.strip())
                            if key.lower() != 'id':  # Skip ID updates
                                data[key] = val
                    
                    return table, "update", data
                    
        except Exception as e:
            logger.error(f"Query parsing failed: {e}")
            return None
        
        return None

    def _parse_value(self, value_str: str) -> Any:
        """Safely parse a value string to appropriate Python type"""
        value_str = value_str.strip()
        
        # Remove quotes
        if ((value_str.startswith("'") and value_str.endswith("'")) or 
            (value_str.startswith('"') and value_str.endswith('"'))):
            return value_str[1:-1]
        
        # Try to convert to number
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            return value_str

    def validate_fields(self, values: Dict[str, Any], model: BaseModel) -> tuple:
        """Enhanced field validation with detailed error reporting"""
        missing_fields = []
        validation_errors = []
        
        try:
            # Create instance to trigger validation
            instance = model(**values)
            return [], instance, []
            
        except Exception as e:
            if hasattr(e, 'errors'):
                for error in e.errors():
                    field_name = error['loc'][0]
                    error_type = error['type']
                    
                    if error_type == 'value_error.missing':
                        missing_fields.append(field_name)
                    else:
                        validation_errors.append(f"{field_name}: {error['msg']}")
            else:
                validation_errors.append(str(e))
            
            return missing_fields, None, validation_errors

    def generate_final_sql(self, data: Dict[str, Any], table: str, query_type: str = "insert", where_clause: str = None) -> str:
        """Generate final SQL with proper formatting and validation"""
        try:
            # Ensure proper table name
            table = self.normalize_table_name(table)
            
            if query_type.lower() == "insert":
                columns = ", ".join(data.keys())
                values = []
                for v in data.values():
                    if isinstance(v, str):
                        values.append(f"'{v.replace(chr(39), chr(39)+chr(39))}'")  # Escape single quotes
                    elif v is None:
                        values.append("NULL")
                    else:
                        values.append(str(v))
                
                values_str = ", ".join(values)
                return f"INSERT INTO {table} ({columns}) VALUES ({values_str});"
            
            elif query_type.lower() == "update":
                set_clauses = []
                for col, val in data.items():
                    if isinstance(val, str):
                        set_clauses.append(f"{col} = '{val.replace(chr(39), chr(39)+chr(39))}'")
                    elif val is None:
                        set_clauses.append(f"{col} = NULL")
                    else:
                        set_clauses.append(f"{col} = {val}")
                
                set_clause = ", ".join(set_clauses)
                
                if not where_clause:
                    raise ValueError("WHERE clause required for safe UPDATE operation")
                
                return f"UPDATE {table} SET {set_clause} WHERE {where_clause};"
            
            elif query_type.lower() == "select":
                where_clause = where_clause or "1=1"
                return f"SELECT * FROM {table} WHERE {where_clause};"
            
            elif query_type.lower() == "delete":
                if not where_clause:
                    raise ValueError("WHERE clause required for safe DELETE operation")
                return f"DELETE FROM {table} WHERE {where_clause};"
            
            else:
                raise ValueError(f"Unsupported query type: {query_type}")
                
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise

    def generate_summary(self, operation: str, table: str, result: Any, query: str) -> str:
        """Generate AI-powered summary of the operation"""
        try:
            if isinstance(result, pd.DataFrame):
                summary_prompt = f"""
As an AI SQL Assistant, provide a brief, professional summary of this database operation:

Operation: {operation.upper()}
Table: {table}
Query: {query}
Results: {len(result)} rows returned

Data preview:
{result.head().to_string() if not result.empty else 'No data returned'}

Provide a 2-3 sentence summary focusing on business insights and data patterns.
"""
            else:
                summary_prompt = f"""
As an AI SQL Assistant, provide a brief summary of this database operation:

Operation: {operation.upper()}
Table: {table}
Query: {query}
Result: {result}

Provide a 1-2 sentence summary of what was accomplished.
"""
            
            # Generate summary using LLM
            summary_chain = self.llm | StrOutputParser()
            summary = summary_chain.invoke(summary_prompt)
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return f"Successfully executed {operation} operation on {table} table."


class Chat:
    """Enhanced context-aware chat system with improved state management"""
    
    def __init__(self, state: State = None):
        self.llm = SQLAgent.get_llm()
        self.agent = SQLAgent()
        self.memory = MemorySaver()
        self.graph = StateGraph(State)
        
        # Enhanced node system
        self.graph.add_node("analyze_intent", self.analyze_intent_node)
        self.graph.add_node("parse_and_validate", self.parse_and_validate_node)
        self.graph.add_node("ask_missing_field", self.ask_for_missing_field_node)
        self.graph.add_node("update_context", self.update_context_with_user_input_node)
        self.graph.add_node("generate_and_execute", self.generate_and_execute_final_query_node)
        self.graph.add_node("generate_summary", self.generate_summary_node)

        # Set entry point
        self.graph.set_entry_point("analyze_intent")

        # Enhanced conditional edges
        self.graph.add_conditional_edges(
            "analyze_intent",
            lambda state: self._route_after_intent(state),
            {
                "parse_validate": "parse_and_validate",
                "direct_execute": "generate_and_execute"
            }
        )

        self.graph.add_conditional_edges(
            "parse_and_validate",
            lambda state: "missing_fields" in state and len(state.get("missing_fields", [])) > 0,
            {
                True: "ask_missing_field",
                False: "generate_and_execute"
            }
        )

        self.graph.add_edge("ask_missing_field", "update_context")
        self.graph.add_edge("update_context", "parse_and_validate")
        self.graph.add_edge("generate_and_execute", "generate_summary")

        self.graph.set_finish_point("generate_summary")
        self.runner = self.graph.compile(checkpointer=self.memory)

    def _route_after_intent(self, state: State) -> str:
        """Route based on query intent analysis"""
        query_type = state.get("query_type", "")
        if query_type in ["insert", "update"]:
            return "parse_validate"
        else:
            return "direct_execute"

    def analyze_intent_node(self, state: State) -> Dict[str, Any]:
        """Analyze user intent and query type"""
        user_message = state["messages"][-1].content
        
        # Generate initial query to understand intent
        query = self.agent.generate_query(user_message)
        intent_info = self.agent.parse_query_intent(query)
        
        return {
            "user_intent": user_message,
            "generated_query": query,
            "query_type": intent_info["operation"],
            "table": intent_info["table"],
            "operation_count": state.get("operation_count", 0) + 1
        }

    def ask_for_missing_field_node(self, state: State) -> Dict[str, str]:
        """Ask user for missing field values"""
        missing_fields = state.get("missing_fields", [])
        if not missing_fields:
            return {"message": "All required fields have been provided."}
        
        next_field = missing_fields[0]
        field_desc = self._get_field_description(state.get("table"), next_field)
        
        return {"message": f"Please provide a value for '{next_field}': {field_desc}"}

    def _get_field_description(self, table: str, field: str) -> str:
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

    def parse_and_validate_node(self, state: State) -> Dict[str, Any]:
        """Enhanced parsing and validation with duplicate prevention"""
        query = state.get("generated_query", "")
        parsed = self.agent.parse_insert_or_update_query(query)
        
        if parsed:
            table, query_type, values = parsed
            model = self.agent.model_map.get(table.lower())
            
            if not model:
                return {"validation_errors": [f"No model found for table: {table}"]}
            
            # Check for potential duplicates on INSERT
            if query_type == "insert":
                duplicate_check = self._check_for_duplicates(table, values)
                if duplicate_check:
                    return {"validation_errors": [duplicate_check]}
            
            missing, instance, validation_errors = self.agent.validate_fields(values, model)
            
            return {
                "table": table,
                "query_type": query_type,
                "partial_values": values,
                "missing_fields": missing,
                "validation_errors": validation_errors
            }
        
        return {"validation_errors": ["Unable to parse the query properly"]}

    def _check_for_duplicates(self, table: str, values: Dict[str, Any]) -> Optional[str]:
        """Check for potential duplicate records"""
        try:
            # Check if a similar record already exists
            if "name" in values:
                check_query = f"SELECT COUNT(*) as count FROM {table} WHERE name = '{values['name']}'"
                result = self.agent.execute_query(check_query)
                
                if isinstance(result, str) and "1" in result:
                    return f"A record with name '{values['name']}' already exists. Please verify this is not a duplicate."
                    
        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")
        
        return None

    def update_context_with_user_input_node(self, state: State) -> Dict[str, Any]:
        """Update context with user-provided field values"""
        user_response = state["messages"][-1].content.strip()
        missing_fields = state.get("missing_fields", [])
        
        if not missing_fields:
            return state
        
        field_name = missing_fields[0]
        updated_values = state.get("partial_values", {}).copy()
        updated_values[field_name] = user_response
        
        # Re-validate with updated values
        table = state.get("table")
        model = self.agent.model_map.get(table)
        
        if model:
            new_missing, instance, validation_errors = self.agent.validate_fields(updated_values, model)
            
            return {
                "partial_values": updated_values,
                "missing_fields": new_missing,
                "validation_errors": validation_errors
            }
        
        return {"partial_values": updated_values}

    def generate_and_execute_final_query_node(self, state: State) -> Dict[str, Any]:
        """Generate and execute the final query with enhanced error handling"""
        try:
            query_type = state.get("query_type", "select")
            
            if query_type.lower() in ["insert", "update"]:
                table = state.get("table")
                data = state.get("partial_values", {})
                
                if not table or not data:
                    return {"execution_result": "Missing required data for query execution"}
                
                final_query = self.agent.generate_final_sql(data, table, query_type)
            else:
                final_query = state.get("generated_query", "")
            
            # Execute the query
            execution_result = self.agent.execute_query(final_query)
            
            return {
                "final_query": final_query,
                "execution_result": execution_result
            }
            
        except Exception as e:
            error_msg = f"Query execution failed: {str(e)}"
            logger.error(error_msg)
            return {"execution_result": error_msg}

    def generate_summary_node(self, state: State) -> Dict[str, str]:
        """Generate AI-powered summary of the operation"""
        try:
            operation = state.get("query_type", "unknown")
            table = state.get("table", "unknown")
            result = state.get("execution_result", "")
            query = state.get("final_query", "")
            
            summary = self.agent.generate_summary(operation, table, result, query)
            
            return {"summary": summary}
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {"summary": "Operation completed successfully."}

    def run(self, thread_id: str, user_input: str) -> Dict[str, Any]:
        """Run the chat system with enhanced context management"""
        try:
            logger.info(f"Processing user input: {user_input}")
            
            result = self.runner.invoke(
                {
                    "messages": [{"role": "user", "content": user_input}],
                    "conversation_context": {},
                    "operation_count": 0
                },
                {
                    "configurable": {
                        "thread_id": thread_id,
                    }
                }
            )
            
            # Enhanced result processing
            if isinstance(result, dict):
                # Serialize complex objects
                serialized_result = {}
                for key, value in result.items():
                    if isinstance(value, pd.DataFrame):
                        serialized_result[key] = value
                    elif hasattr(value, 'dict'):
                        serialized_result[key] = value.dict()
                    else:
                        serialized_result[key] = value
                
                return serialized_result
            
            return result
            
        except Exception as e:
            logger.error(f"Chat execution failed: {e}")
            return {
                "execution_result": f"An error occurred: {str(e)}",
                "summary": "Sorry, I encountered an error while processing your request."
            }


if __name__ == "__main__":
    # Example usage
    chat = Chat()
    response = chat.run("user_001", "Show me all employees")
    print(json.dumps(response, indent=2, default=str))
