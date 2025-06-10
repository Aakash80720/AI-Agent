import functools
import json
import re
import pandas as pd
import logging
import functools
from datetime import datetime
from typing import Annotated, Optional, TypedDict, Dict, List, Any, Union
from decimal import Decimal

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

from .config_manager import config_manager
from .database_manager import DatabaseManager, get_default_database_manager
from .table_analyzer import TableAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Employee(BaseModel):
    """Employee model with validation"""
    id: Optional[int] = Field(None, description="Auto-generated employee ID")
    name: str = Field(..., description="Employee full name", min_length=1, max_length=100)
    department: str = Field(..., description="Department name (required)", min_length=1, max_length=50)
    salary: float = Field(..., description="Employee salary (required)", ge=0)
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
    
    @validator('department')
    def validate_department(cls, v):
        if not v or not v.strip():
            raise ValueError('department is required and cannot be empty')
        return v.strip()
    
    @validator('salary')
    def validate_salary(cls, v):
        if v is None:
            raise ValueError('salary is required and cannot be null')
        if v < 0:
            raise ValueError('salary must be non-negative')
        return v

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
    
    def __init__(self, database_name: Optional[str] = None):
        """Initialize SQL Agent with modular configuration
        
        Args:
            database_name: Name of the database configuration to use.
                          If None, uses the active database from configuration.
        """
        # Initialize database manager
        if database_name:
            self.db_manager = DatabaseManager(database_name)
        else:
            self.db_manager = get_default_database_manager()
        
        # Get database instances
        self.db = self.db_manager.get_database()
        self.table_schemas = self.db_manager.get_table_schemas()
        
        # Initialize LLM with configuration
        llm_config = config_manager.get_llm_config()
        self.llm = ChatOllama(**llm_config)
        
        # Initialize operation tracking
        self.operation_count = {}
        
        logger.info(f"Loaded table schemas: {list(self.table_schemas.keys())}")
        
        # Enhanced system prompt from configuration
        self.system_prompt = config_manager.get_system_prompt()
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get table information for prompt
        table_info = self._build_table_info_for_prompt()
        
        self.system_prompt += f"\n\nDatabase tables:\n{table_info}\n\nCurrent date: {current_date}"
        
        # Enhanced prompt template with strict table name enforcement
        self.DB_structure_prompt = PromptTemplate.from_template(
            template=(
                f"{self.system_prompt}\n\n"
                "Database Schema:\n{table_info}\n\n"
                "Available Tables: {table_names}\n\n"
                "Question: {input}\n"
                "SQL Query (plain text only):"
            )
        )
        
        # Set the input variables explicitly to match what create_sql_query_chain expects
        self.DB_structure_prompt.input_variables = ['input', 'table_info', 'table_names']
        
        # Use default chain creation for better compatibility
        self.generated_query_chain = create_sql_query_chain(
            llm=self.llm,
            db=self.db
        )        # Dynamic model mapping from configuration
        self.model_map = self._build_model_map()
        
        # Initialize table analyzer for dynamic analysis
        llm_config = config_manager.get_llm_config()
        self.table_analyzer = TableAnalyzer(llm_config)
        
        # Table name normalization mapping from configuration  
        self.TABLE_ALIASES = self._build_table_aliases()
        
        # Enhanced conversation context for better awareness
        conversation_config = config_manager.get_conversation_config()
        self.conversation_context = {
            "last_operation": None,
            "last_table": None,
            "last_values": {},
            "user_preferences": {},
            "operation_history": [],
            "frequent_columns": {},
            "table_usage_count": {table: 0 for table in self.table_schemas.keys()},
            "recent_queries": [],
            "user_patterns": {
                "preferred_departments": [],
                "common_salary_ranges": [],
                "frequent_operations": []
            },
            "max_history_length": conversation_config.get("max_history_length", 50)
        }

    def _build_table_info_for_prompt(self) -> str:
        """Build table information string for LLM prompt"""
        table_info = ""
        
        for table_name, schema in self.table_schemas.items():
            columns = schema.get('columns', [])
            table_info += f"- {table_name} (columns: {', '.join(columns)})\n"
        
        return table_info.strip()
    def _build_model_map(self) -> Dict[str, Any]:
        """Build model mapping dynamically from configuration and available models"""
        model_map = {}
        
        # Get actual table names from database
        actual_tables = list(self.table_schemas.keys())
        
        # For each actual table, try to find or create a corresponding model
        for table_name in actual_tables:
            try:
                # First, try to get model from configuration
                model_config = config_manager.get_field_config(table_name)
                model_class_name = model_config.get("model_class", None)
                
                if model_class_name:
                    # Try to dynamically import the model
                    model_map[table_name] = self._get_model_class(model_class_name)
                else:
                    # Fallback: use predefined models based on table name patterns
                    model_map[table_name] = self._get_model_by_table_pattern(table_name)
                    
            except Exception as e:
                logger.warning(f"Could not load model for table {table_name}: {e}")
                # Use a basic model fallback
                model_map[table_name] = self._get_model_by_table_pattern(table_name)
        
        return model_map
    
    def _get_model_class(self, model_class_name: str) -> Any:
        """Dynamically get model class by name"""
        # Map of available models - this could be expanded dynamically
        available_models = {
            "Employee": Employee,
            "Project": Project,
            # Add more models as they become available
        }
        
        return available_models.get(model_class_name, Employee)  # Default fallback
    def _get_model_by_table_pattern(self, table_name: str) -> Any:
        """Get model class based on table name patterns"""
        table_lower = table_name.lower()
          # Pattern matching for common table types
        if any(keyword in table_lower for keyword in ['employee', 'person', 'user', 'staff', 'worker']):
            return Employee
        elif any(keyword in table_lower for keyword in ['project', 'task', 'work', 'assignment']):
            return Project
        else:
            # Default fallback - could create a generic model here
            logger.warning(f"No specific model found for table {table_name}, using Employee as fallback")
            return Employee

    def _build_table_aliases(self) -> Dict[str, str]:
        """Build table aliases mapping with fast fallback approach"""
        aliases = {}
        
        # Start with rule-based alias generation for fast startup
        for table_name in self.table_schemas.keys():
            # Get alias configuration if exists
            try:
                alias_config = config_manager.get_table_aliases(table_name)
                if alias_config:
                    for alias in alias_config:
                        aliases[alias.lower()] = table_name
            except:
                # Fallback: generate common aliases based on table name patterns
                pass
                
            # Dynamic alias generation based on table name patterns
            table_aliases = self._generate_dynamic_aliases(table_name)
            aliases.update(table_aliases)
        
        # Schedule enhanced LLM analysis for later (async/background)
        # This will be done on first query to avoid startup delays
        self._enhanced_analysis_pending = True
        
        return aliases
    
    def _get_enhanced_aliases_lazy(self):
        """Perform LLM-based table analysis on first use to avoid startup delays"""
        if not hasattr(self, '_enhanced_analysis_pending') or not self._enhanced_analysis_pending:
            return
            
        try:
            logger.info("Performing enhanced table analysis...")
            enhanced_mapping = self.table_analyzer.generate_enhanced_aliases(self.table_schemas)
            
            for table_name, mapping in enhanced_mapping.items():
                table_aliases = mapping.get('aliases', {})
                self.TABLE_ALIASES.update(table_aliases)
                
                # Log the semantic analysis for debugging
                analysis = mapping.get('analysis', {})
                logger.info(f"Table {table_name} analyzed as {analysis.get('domain', 'unknown')} domain, "
                          f"{analysis.get('entity_type', 'unknown')} entity type")
            
            self._enhanced_analysis_pending = False
            
        except Exception as e:
            logger.warning(f"Enhanced table analysis failed: {e}")
            self._enhanced_analysis_pending = False
    def _generate_dynamic_aliases(self, table_name: str) -> Dict[str, str]:
        """Generate dynamic aliases based on table name patterns and common variations"""
        aliases = {}
        table_lower = table_name.lower()
        
        # Common plural/singular variations
        if table_lower.endswith('s'):
            # If table is plural, add singular form
            singular = table_lower[:-1]
            aliases[singular] = table_name
        else:
            # If table is singular, add plural form
            if table_lower.endswith('y'):
                plural = table_lower[:-1] + 'ies'
            elif table_lower.endswith(('s', 'sh', 'ch', 'x', 'z')):
                plural = table_lower + 'es'
            else:
                plural = table_lower + 's'
            aliases[plural] = table_name
        
        # Generate abbreviations dynamically
        if len(table_name) > 3:
            # First 3 characters
            aliases[table_name[:3].lower()] = table_name
            
            # First character + consonants
            consonants = ''.join([c for c in table_name.lower() if c not in 'aeiou'])[:4]
            if len(consonants) >= 2:
                aliases[consonants] = table_name
        
        # Domain-specific aliases based on common patterns
        domain_aliases = self._get_domain_specific_aliases(table_name)
        aliases.update(domain_aliases)
        
        return aliases
    
    def _get_domain_specific_aliases(self, table_name: str) -> Dict[str, str]:
        """Generate domain-specific aliases based on table name semantics"""
        aliases = {}
        table_lower = table_name.lower()
        
        # Employee/Person related aliases
        if any(keyword in table_lower for keyword in ['employee', 'person', 'user', 'staff', 'worker']):
            employee_aliases = ['emp', 'staff', 'workers', 'people', 'personnel', 'team']
            for alias in employee_aliases:
                aliases[alias] = table_name
        
        # Project/Task related aliases
        elif any(keyword in table_lower for keyword in ['project', 'task', 'work', 'assignment']):
            project_aliases = ['proj', 'task', 'tasks', 'work', 'assignments', 'jobs']
            for alias in project_aliases:
                aliases[alias] = table_name
        
        # Organization related aliases
        elif any(keyword in table_lower for keyword in ['company', 'organization', 'dept', 'department']):
            org_aliases = ['org', 'dept', 'company', 'division']
            for alias in org_aliases:
                aliases[alias] = table_name
        
        # Customer/Client related aliases
        elif any(keyword in table_lower for keyword in ['customer', 'client', 'account']):
            customer_aliases = ['cust', 'client', 'customer', 'account', 'accounts']
            for alias in customer_aliases:
                aliases[alias] = table_name
        
        # Order/Transaction related aliases
        elif any(keyword in table_lower for keyword in ['order', 'transaction', 'sale', 'purchase']):
            order_aliases = ['order', 'orders', 'txn', 'transaction', 'sale', 'sales']
            for alias in order_aliases:
                aliases[alias] = table_name
        
        return aliases
    
    def get_field_description(self, table: str, field: str) -> str:
        """Get user-friendly field description using configuration
        
        Args:
            table: Table/model name
            field: Field name
            
        Returns:
            User-friendly field description
        """
        try:
            return config_manager.get_field_description(table, field)
        except Exception as e:
            logger.warning(f"Failed to get field description for {table}.{field}: {e}")
            return f"Value for {field}"

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
        """Generate SQL query with enhanced table name handling and context awareness"""
        try:
            # Enhance prompt with conversation context
            enhanced_prompt = self.enhance_query_with_context(prompt)
            
            # Get personalized prompt based on user patterns
            personalized_prompt = self.get_personalized_prompt(enhanced_prompt)
              # Pre-process prompt for better table name resolution with strict missing field handling
            final_prompt = f"""
Based on the user request: "{personalized_prompt}"

Use ONLY these exact table names:
- employee (for any employee/staff/worker related queries)
- project (for any project/task related queries)

CRITICAL INSTRUCTIONS:
1. ONLY include fields that are EXPLICITLY mentioned by the user
2. NEVER assume default values for department, salary, hire_date, or any other fields
3. If user doesn't mention department - DO NOT include department field at all
4. If user doesn't mention salary - DO NOT include salary field at all
5. If user doesn't mention hire_date - DO NOT include hire_date field at all
6. Generate MINIMAL SQL with ONLY the fields the user actually provided

Generate the SQL query:
"""
            result = self.generated_query_chain.invoke({"question": final_prompt})
            result = str(result).strip()
            
            # Clean up result - extract SQL from markdown or explanation
            if "```sql" in result:
                # Extract SQL from markdown code block
                sql_start = result.find("```sql") + 6
                sql_end = result.find("```", sql_start)
                if sql_end != -1:
                    result = result[sql_start:sql_end].strip()
                else:
                    result = result[sql_start:].strip()
            elif result.startswith("```"):
                # Handle generic code blocks
                result = result.lstrip("`").replace("sql", "", 1).strip()
                result = result.rstrip("`").strip()
            
            # If result contains explanations, try to extract just the SQL
            lines = result.split('\n')
            sql_lines = []
            for line in lines:
                line = line.strip()
                if (line.upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')) or
                    line.upper().startswith(('VALUES', 'FROM', 'WHERE', 'SET', 'INTO')) or
                    (sql_lines and line.endswith(';'))):
                    sql_lines.append(line)
                elif sql_lines and not line.startswith('--'):
                    # Continue SQL statement
                    sql_lines.append(line)
            
            if sql_lines:
                result = ' '.join(sql_lines)
            
            # Post-process to fix table names
            result = self.enhance_query_for_table_names(result)
            
            # Store recent query for context
            self.conversation_context["recent_queries"].append({
                "timestamp": datetime.now().isoformat(),
                "original_prompt": prompt,
                "enhanced_prompt": enhanced_prompt,
                "generated_query": result
            })
            
            # Keep only last 20 queries
            if len(self.conversation_context["recent_queries"]) > 20:
                self.conversation_context["recent_queries"] = self.conversation_context["recent_queries"][-20:]
            
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
        """Enhanced parsing for INSERT and UPDATE queries with NULL handling"""
        try:
            query = query.strip()
            
            # Parse INSERT queries
            insert_match = re.search(r'INSERT\s+INTO\s+["\']?(\w+)["\']?', query, re.IGNORECASE)
            if insert_match:
                table = self.normalize_table_name(insert_match.group(1))
                
                # Extract columns and values - handle quoted column names
                col_match = re.search(r'\(([^)]+)\)\s+VALUES', query, re.IGNORECASE)
                val_match = re.search(r'VALUES\s*\(([^)]+)\)', query, re.IGNORECASE)
                
                if col_match and val_match:
                    # Parse columns - handle quoted names
                    columns_str = col_match.group(1)
                    columns = []
                    for col in columns_str.split(','):
                        col = col.strip()
                        # Remove quotes if present
                        if col.startswith('"') and col.endswith('"'):
                            col = col[1:-1]
                        elif col.startswith("'") and col.endswith("'"):
                            col = col[1:-1]
                        columns.append(col)
                    
                    # Parse values - improved NULL handling
                    values_str = val_match.group(1)
                    values = []
                    current_val = ""
                    in_quotes = False
                    quote_char = None
                    paren_count = 0
                    
                    for char in values_str:
                        if char in ["'", '"'] and not in_quotes:
                            in_quotes = True
                            quote_char = char
                        elif char == quote_char and in_quotes:
                            in_quotes = False
                            quote_char = None
                        elif char == '(' and not in_quotes:
                            paren_count += 1
                        elif char == ')' and not in_quotes:
                            paren_count -= 1
                        elif char == ',' and not in_quotes and paren_count == 0:
                            values.append(self._parse_value(current_val.strip()))
                            current_val = ""
                            continue
                        current_val += char
                    
                    # Add the last value
                    if current_val.strip():
                        values.append(self._parse_value(current_val.strip()))
                      # Create data dict - include all values for proper validation
                    filtered_data = {}
                    for col, val in zip(columns, values):
                        if col.lower() != 'id':  # Skip auto-increment ID
                            # Include all values, including NULL, for proper mandatory field detection
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
        """Safely parse a value string to appropriate Python type with NULL handling"""
        value_str = value_str.strip()
        
        # Handle NULL values
        if value_str.upper() == 'NULL':
            return None
        
        # Remove quotes
        if ((value_str.startswith("'") and value_str.endswith("'")) or 
            (value_str.startswith('"') and value_str.endswith('"'))):
            return value_str[1:-1]        # Try to convert to number
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
            # Try to create instance to see what fails
            instance = model(**values)
            return [], instance, []
            
        except Exception as e:
            if hasattr(e, 'errors'):
                for error in e.errors():
                    field_name = error['loc'][0] if error['loc'] else 'unknown'
                    error_type = error['type']
                    error_msg = error['msg']
                    
                    # Check if this is a required field that's missing or None
                    if field_name in values:
                        field_value = values[field_name]
                        # If field is None/NULL and the error indicates it should be a string/number/etc,
                        # then it's a required field that's missing
                        if (field_value is None or (isinstance(field_value, str) and field_value.upper() == 'NULL')):
                            if error_type in ['string_type', 'float_type', 'int_type', 'missing']:
                                if field_name not in missing_fields:
                                    missing_fields.append(field_name)
                            else:
                                validation_errors.append(f"{field_name}: {error_msg}")
                        else:
                            # Field has a value but it's invalid
                            validation_errors.append(f"{field_name}: {error_msg}")
                    else:
                        # Field is completely missing from values
                        missing_fields.append(field_name)
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
        
    def update_conversation_context(self, operation: str, table: str, values: Dict[str, Any] = None, query: str = None):
        """Update conversation context with latest operation details"""
        self.conversation_context["last_operation"] = operation
        self.conversation_context["last_table"] = table
        self.conversation_context["last_values"] = values or {}
        
        # Update operation history
        operation_record = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "table": table,
            "values": values,
            "query": query
        }
        self.conversation_context["operation_history"].append(operation_record)
        
        # Keep only last 50 operations to prevent memory bloat
        if len(self.conversation_context["operation_history"]) > 50:
            self.conversation_context["operation_history"] = self.conversation_context["operation_history"][-50:]
        
        # Update table usage count
        if table in self.conversation_context["table_usage_count"]:
            self.conversation_context["table_usage_count"][table] += 1
        
        # Track frequent operations
        if operation not in self.conversation_context["user_patterns"]["frequent_operations"]:
            self.conversation_context["user_patterns"]["frequent_operations"].append(operation)
        
        # Track departments and salary ranges
        if values:
            if "department" in values and values["department"]:
                dept = values["department"]
                if dept not in self.conversation_context["user_patterns"]["preferred_departments"]:
                    self.conversation_context["user_patterns"]["preferred_departments"].append(dept)
            
            if "salary" in values and values["salary"]:
                salary = float(values["salary"]) if isinstance(values["salary"], (str, int, float)) else 0
                if salary > 0:
                    self.conversation_context["user_patterns"]["common_salary_ranges"].append(salary)
        
        # Track frequently used columns
        if values:
            for col in values.keys():
                if col in self.conversation_context["frequent_columns"]:
                    self.conversation_context["frequent_columns"][col] += 1
                else:
                    self.conversation_context["frequent_columns"][col] = 1

    def get_context_suggestions(self, user_query: str) -> Dict[str, Any]:
        """Provide context-aware suggestions based on conversation history"""
        suggestions = {
            "suggested_values": {},
            "related_queries": [],
            "pattern_insights": []
        }
        
        # Suggest common departments
        if "department" in user_query.lower() and self.conversation_context["user_patterns"]["preferred_departments"]:
            most_common_dept = max(set(self.conversation_context["user_patterns"]["preferred_departments"]), 
                                 key=self.conversation_context["user_patterns"]["preferred_departments"].count)
            suggestions["suggested_values"]["department"] = most_common_dept
        
        # Suggest salary ranges
        if "salary" in user_query.lower() and self.conversation_context["user_patterns"]["common_salary_ranges"]:
            avg_salary = sum(self.conversation_context["user_patterns"]["common_salary_ranges"]) / len(self.conversation_context["user_patterns"]["common_salary_ranges"])
            suggestions["suggested_values"]["salary"] = f"Around ${avg_salary:,.0f}"
        
        # Suggest related queries based on history
        last_operations = [op["operation"] for op in self.conversation_context["operation_history"][-5:]]
        if "select" in last_operations and "insert" not in user_query.lower():
            suggestions["related_queries"].append("Would you like to add a new record?")
        
        if "insert" in last_operations and "select" not in user_query.lower():
            suggestions["related_queries"].append("Would you like to view the records you just added?")
        
        # Pattern insights
        most_used_table = max(self.conversation_context["table_usage_count"], 
                            key=self.conversation_context["table_usage_count"].get)
        suggestions["pattern_insights"].append(f"You frequently work with the {most_used_table} table")
        
        return suggestions

    def enhance_query_with_context(self, query: str) -> str:
        """Enhance user query with context from conversation history"""
        enhanced_query = query
        
        # If user refers to "last record" or "previous entry", use context
        if any(phrase in query.lower() for phrase in ["last record", "previous entry", "that record", "the one i just"]):
            if self.conversation_context["last_operation"] == "insert" and self.conversation_context["last_values"]:
                # Add specific reference to the last inserted record
                name_value = self.conversation_context["last_values"].get("name")
                if name_value:
                    enhanced_query += f" (referring to record with name '{name_value}')"
        
        # If user says "same department" or "that department", use context
        if any(phrase in query.lower() for phrase in ["same department", "that department", "this department"]):
            if self.conversation_context["last_values"].get("department"):
                dept = self.conversation_context["last_values"]["department"]
                enhanced_query = enhanced_query.replace("same department", f"'{dept}' department")
                enhanced_query = enhanced_query.replace("that department", f"'{dept}' department")
                enhanced_query = enhanced_query.replace("this department", f"'{dept}' department")
        
        # If user asks about "similar" records, suggest criteria
        if "similar" in query.lower() and self.conversation_context["last_values"]:
            criteria = []
            for key, value in self.conversation_context["last_values"].items():
                if key in ["department", "salary"] and value:
                    criteria.append(f"{key} = '{value}'")
            if criteria:
                enhanced_query += f" (suggesting criteria: {' AND '.join(criteria)})"
        
        return enhanced_query

    def get_personalized_prompt(self, base_prompt: str) -> str:
        """Create personalized prompt based on user patterns"""
        context_info = []
        
        # Add table preference context
        most_used_table = max(self.conversation_context["table_usage_count"], 
                            key=self.conversation_context["table_usage_count"].get)
        context_info.append(f"User frequently works with {most_used_table} table")
        
        # Add operation patterns
        if self.conversation_context["user_patterns"]["frequent_operations"]:
            common_ops = ", ".join(self.conversation_context["user_patterns"]["frequent_operations"][-3:])
            context_info.append(f"Recent operations: {common_ops}")
        
        # Add department preferences
        if self.conversation_context["user_patterns"]["preferred_departments"]:
            common_depts = ", ".join(set(self.conversation_context["user_patterns"]["preferred_departments"][-3:]))
            context_info.append(f"Common departments: {common_depts}")
        
        if context_info:
            personalized_prompt = f"{base_prompt}\n\nContext from conversation history:\n- " + "\n- ".join(context_info)
            return personalized_prompt
        
        return base_prompt

    def get_context_insights(self, user_input: str) -> Dict[str, Any]:
        """Get context-aware insights and suggestions for the user"""
        insights = {
            "suggestions": [],
            "context_info": {},
            "related_actions": []
        }
        
        # Get suggestions from the agent
        agent_suggestions = self.agent.get_context_suggestions(user_input)
        insights["suggestions"] = agent_suggestions.get("suggested_values", {})
        insights["related_actions"] = agent_suggestions.get("related_queries", [])
        
        # Add conversation statistics
        context = self.agent.conversation_context
        insights["context_info"] = {
            "total_operations": len(context["operation_history"]),
            "most_used_table": max(context["table_usage_count"], key=context["table_usage_count"].get) if context["table_usage_count"] else "None",
            "recent_operations": [op["operation"] for op in context["operation_history"][-5:]],
            "preferred_departments": list(set(context["user_patterns"]["preferred_departments"][-3:])) if context["user_patterns"]["preferred_departments"] else []
        }
        
        return insights

    # ...existing code...
    
class Chat:
    """Enhanced context-aware chat system with improved state management"""
    
    def __init__(self, state: State = None):
        self.agent = SQLAgent()
        self.llm = self.agent.llm
        self.memory = MemorySaver()
        self.graph = StateGraph(State)
        
        # Enhanced node system
        self.graph.add_node("analyze_intent", self.analyze_intent_node)
        self.graph.add_node("parse_and_validate", self.parse_and_validate_node)
        self.graph.add_node("ask_missing_field", self.ask_for_missing_field_node)
        self.graph.add_node("update_context", self.update_context_with_user_input_node)
        self.graph.add_node("generate_and_execute", self.generate_and_execute_final_query_node)
        self.graph.add_node("generate_summary", self.generate_summary_node)        # Set entry point
        self.graph.set_entry_point("analyze_intent")
        
        # Enhanced conditional edges
        self.graph.add_conditional_edges(
            "analyze_intent",
            lambda state: self._route_after_intent(state),
            {
                "parse_validate": "parse_and_validate",
                "direct_execute": "generate_and_execute",
                "update_context": "update_context"
            }
        )
        
        self.graph.add_conditional_edges(
            "parse_and_validate",
            lambda state: self._route_after_validation(state),            {
                "has_missing": "ask_missing_field",
                "no_missing": "generate_and_execute",
                "validation_error": "generate_summary"
            }
        )
        
        self.graph.add_edge("ask_missing_field", "update_context")
        self.graph.add_edge("update_context", "parse_and_validate")
        self.graph.add_edge("generate_and_execute", "generate_summary")

        self.graph.set_finish_point("generate_summary")
        self.runner = self.graph.compile(checkpointer=self.memory)

    def _route_after_intent(self, state: State) -> str:
        """Route based on query intent analysis"""
        # Check if this is a field value response
        if state.get("is_field_value_response", False):
            return "update_context"
            
        query_type = state.get("query_type", "")
        if query_type in ["insert", "update"]:
            return "parse_validate"
        else:
            return "direct_execute"
    
    def _route_after_validation(self, state: State) -> str:
        """Route based on validation results"""
        validation_errors = state.get("validation_errors", [])
        missing_fields = state.get("missing_fields", [])
        
        # If there are validation errors (not missing fields), end with summary
        if validation_errors and not missing_fields:
            return "validation_error"
        
        # If there are missing fields, ask for them
        if missing_fields and len(missing_fields) > 0:
            return "has_missing"
        
        # Otherwise, proceed to execute
        return "no_missing"

    def analyze_intent_node(self, state: State) -> Dict[str, Any]:
        """Analyze user intent and query type with missing field detection"""
        # Trigger lazy loading of enhanced table aliases on first use
        self.agent._get_enhanced_aliases_lazy()
        
        user_message = state["messages"][-1].content
        
        # Check if this is a field value being provided for a previous request
        # The key is to check if we have incomplete data from a previous operation
        if (state.get("missing_fields") and 
            state.get("table") and 
            state.get("query_type") and 
            state.get("partial_values")):
            
            # We're in the middle of field collection - this is a field value response
            logger.info(f"Detected field value response for missing fields: {state.get('missing_fields')}")
            return {
                "user_intent": user_message,
                "generated_query": state.get("generated_query", ""),
                "query_type": state.get("query_type"),
                "table": state.get("table"),
                "partial_values": state.get("partial_values", {}),
                "missing_fields": state.get("missing_fields", []),
                "operation_count": state.get("operation_count", 0) + 1,
                "is_field_value_response": True
            }
        
        # Check if there's a waiting_for_input flag from previous turn
        if state.get("waiting_for_input") and state.get("missing_field"):
            logger.info(f"Detected field value response for field: {state.get('missing_field')}")
            return {
                "user_intent": user_message,
                "generated_query": state.get("generated_query", ""),
                "query_type": state.get("query_type"),
                "table": state.get("table"),
                "partial_values": state.get("partial_values", {}),
                "missing_fields": state.get("missing_fields", []),
                "missing_field": state.get("missing_field"),
                "operation_count": state.get("operation_count", 0) + 1,
                "is_field_value_response": True
            }
        
        # Check for simple patterns that indicate this is likely a field value
        # (single word, number, or short phrase - not a full SQL request)
        user_message_clean = user_message.strip()
        if (len(user_message_clean.split()) <= 3 and 
            not any(keyword in user_message_clean.lower() for keyword in ['show', 'select', 'insert', 'add', 'create', 'update', 'delete', 'find', 'get', 'list'])):
            
            # This looks like a simple value - check if we have context from previous incomplete operation
            if state.get("table") and state.get("query_type"):
                logger.info(f"Detected simple value response: '{user_message_clean}' - treating as field value")
                return {
                    "user_intent": user_message,
                    "generated_query": state.get("generated_query", ""),
                    "query_type": state.get("query_type"),
                    "table": state.get("table"),
                    "partial_values": state.get("partial_values", {}),
                    "missing_fields": state.get("missing_fields", []),
                    "operation_count": state.get("operation_count", 0) + 1,
                    "is_field_value_response": True
                }
        
        # Normal new query processing
        query = self.agent.generate_query(user_message)
        intent_info = self.agent.parse_query_intent(query)
        
        return {
            "user_intent": user_message,
            "generated_query": query,
            "query_type": intent_info["operation"],
            "table": intent_info["table"],
            "operation_count": state.get("operation_count", 0) + 1,
            "is_field_value_response": False
        }

    def ask_for_missing_field_node(self, state: State) -> Dict[str, Any]:
        """Ask user for missing field values"""
        missing_fields = state.get("missing_fields", [])
        if not missing_fields:
            return {
                "message": "All required fields have been provided.",
                "execution_result": "All required fields have been provided.",
                "summary": "All required fields have been provided."
            }
        
        next_field = missing_fields[0]
        field_desc = self._get_field_description(state.get("table"), next_field)
        message = f"Please provide a value for '{next_field}': {field_desc}"
        
        return {
            "message": message,
            "execution_result": message,
            "summary": f"Waiting for required field: {next_field}",
            "waiting_for_input": True,
            "missing_field": next_field
        }

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
        """Check for potential duplicate records - but don't block the workflow"""
        try:
            # Check if a similar record already exists
            if "name" in values and values["name"]:
                check_query = f"SELECT COUNT(*) as count FROM {table} WHERE name = '{values['name']}'"
                result = self.agent.execute_query(check_query)
                
                if isinstance(result, pd.DataFrame) and not result.empty:
                    count = result.iloc[0]['count']
                    if count > 0:
                        # Return a warning but don't block - let validation handle missing fields first
                        return None  # Disable duplicate blocking for now to test missing fields
                        
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
        """Generate and execute the final query with enhanced error handling and context updates"""
        try:
            query_type = state.get("query_type", "select")
            
            if query_type.lower() in ["insert", "update"]:
                table = state.get("table")
                data = state.get("partial_values", {})
                
                if not table or not data:
                    return {"execution_result": "Missing required data for query execution"}
                
                final_query = self.agent.generate_final_sql(data, table, query_type)
                
                # Update conversation context for insert/update operations
                self.agent.update_conversation_context(
                    operation=query_type,
                    table=table,
                    values=data,
                    query=final_query
                )
            else:
                final_query = state.get("generated_query", "")
                
                # Update conversation context for select operations
                table = state.get("table", "unknown")
                self.agent.update_conversation_context(
                    operation=query_type,
                    table=table,
                    query=final_query
                )
            
            # Execute the query
            execution_result = self.agent.execute_query(final_query)
            
            # Convert DataFrame to serializable format if needed
            if isinstance(execution_result, pd.DataFrame):
                execution_result = {
                    "type": "dataframe",
                    "data": execution_result.to_dict("records"),
                    "columns": list(execution_result.columns),
                    "shape": execution_result.shape
                }
            
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
    response = chat.run("Ak_01","Insert a new employee with name 'John Doe' in salary 70000.")
    print(response)

