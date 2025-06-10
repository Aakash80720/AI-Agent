#!/usr/bin/env python3
"""
Database Manager for SQL Agent
Handles dynamic database connections and operations
"""

import logging
from typing import Dict, Any, Optional, List
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import MetaData, Table, inspect, create_engine
from .config_manager import config_manager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Dynamic database connection and schema management"""
    
    def __init__(self, database_name: Optional[str] = None):
        """Initialize database manager
        
        Args:
            database_name: Name of the database configuration to use.
                          If None, uses the active database.
        """
        self.database_name = database_name
        self._db = None
        self._engine = None
        self._schemas = None
        
        # Initialize database connection
        self.connect()
    
    def connect(self, database_name: Optional[str] = None):
        """Connect to the specified database
        
        Args:
            database_name: Name of the database configuration to use.
                          If None, uses current or active database.
        """
        if database_name:
            self.database_name = database_name
        
        try:
            # Get database URI from configuration
            db_uri = config_manager.get_database_uri(self.database_name)
            logger.info(f"Connecting to database: {self.database_name}")
            logger.debug(f"Database URI: {db_uri}")
            
            # Create SQLDatabase instance
            self._db = SQLDatabase.from_uri(db_uri)
            self._engine = self._db._engine
            
            # Load table schemas
            self._load_schemas()
            
            logger.info(f"Successfully connected to database: {self.database_name}")
            logger.info(f"Available tables: {list(self._schemas.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to connect to database {self.database_name}: {e}")
            raise
    
    def _load_schemas(self):
        """Load table schemas from the connected database"""
        self._schemas = {}
        
        try:
            # Get table names
            tables = self._db.get_usable_table_names()
            
            for table_name in tables:
                # Get column information
                inspector = inspect(self._engine)
                columns = inspector.get_columns(table_name)
                
                self._schemas[table_name] = {
                    'columns': [col['name'] for col in columns],
                    'types': {col['name']: str(col['type']) for col in columns},
                    'column_details': columns
                }
                
        except Exception as e:
            logger.error(f"Failed to load table schemas: {e}")
            # Fallback to configuration-based schemas
            self._load_fallback_schemas()
    
    def _load_fallback_schemas(self):
        """Load fallback schemas from configuration"""
        logger.warning("Using fallback schemas from configuration")
        
        self._schemas = {}
        
        # Get all model configurations
        for model_name in config_manager.get_all_models():
            model_config = config_manager.get_field_config(model_name)
            table_name = model_config.get("table_name", model_name)
            
            columns = []
            types = {}
            
            for field_name, field_config in model_config["fields"].items():
                columns.append(field_name)
                field_type = field_config["type"]
                
                # Map field type to SQL type
                field_types = config_manager._field_config.get("field_types", {})
                sql_type = field_types.get(field_type, {}).get("sql_type", "TEXT")
                types[field_name] = sql_type
            
            self._schemas[table_name] = {
                'columns': columns,
                'types': types,
                'column_details': []
            }
    
    def get_database(self) -> SQLDatabase:
        """Get the SQLDatabase instance
        
        Returns:
            Connected SQLDatabase instance
        """
        if self._db is None:
            raise RuntimeError("Database not connected")
        return self._db
    
    def get_engine(self):
        """Get the SQLAlchemy engine
        
        Returns:
            SQLAlchemy engine instance
        """
        if self._engine is None:
            raise RuntimeError("Database not connected")
        return self._engine
    
    def get_table_schemas(self) -> Dict[str, Dict]:
        """Get table schemas
        
        Returns:
            Dictionary containing table schema information
        """
        if self._schemas is None:
            self._load_schemas()
        return self._schemas
    
    def get_table_names(self) -> List[str]:
        """Get list of available table names
        
        Returns:
            List of table names
        """
        return list(self.get_table_schemas().keys())
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary containing table information
        """
        schemas = self.get_table_schemas()
        
        if table_name not in schemas:
            raise ValueError(f"Table not found: {table_name}")
        
        return schemas[table_name]
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        return table_name in self.get_table_schemas()
    
    def execute_query(self, query: str) -> Any:
        """Execute a SQL query
        
        Args:
            query: SQL query to execute
            
        Returns:
            Query result
        """
        if self._db is None:
            raise RuntimeError("Database not connected")
        
        try:
            logger.debug(f"Executing query: {query}")
            result = self._db.run(query)
            logger.debug(f"Query executed successfully")
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the current database connection
        
        Returns:
            Dictionary containing database connection information
        """
        db_info = config_manager.get_database_info(self.database_name)
        
        # Add runtime information
        db_info.update({
            "connected": self._db is not None,
            "table_count": len(self.get_table_schemas()) if self._schemas else 0,
            "tables": self.get_table_names() if self._schemas else []
        })
        
        return db_info
    
    def switch_database(self, database_name: str):
        """Switch to a different database
        
        Args:
            database_name: Name of the database configuration to switch to
        """
        logger.info(f"Switching from {self.database_name} to {database_name}")
        
        # Close current connection if exists
        if self._db:
            self._db = None
            self._engine = None
            self._schemas = None
        
        # Connect to new database
        self.connect(database_name)
    
    def refresh_schemas(self):
        """Refresh table schemas from the database"""
        logger.info("Refreshing table schemas")
        self._load_schemas()
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status
        
        Returns:
            Dictionary containing connection status information
        """
        status = {
            "connected": self._db is not None,
            "database_name": self.database_name,
            "schemas_loaded": self._schemas is not None,
            "table_count": len(self._schemas) if self._schemas else 0
        }
        
        if self._db:
            try:
                # Test connection with a simple query
                self._db.run("SELECT 1")
                status["connection_healthy"] = True
            except Exception as e:
                status["connection_healthy"] = False
                status["connection_error"] = str(e)
        else:
            status["connection_healthy"] = False
        
        return status

class DatabaseFactory:
    """Factory class for creating database managers"""
    
    _instances = {}
    
    @classmethod
    def get_database_manager(cls, database_name: Optional[str] = None) -> DatabaseManager:
        """Get a database manager instance (singleton per database)
        
        Args:
            database_name: Name of the database configuration
            
        Returns:
            DatabaseManager instance
        """
        if database_name is None:
            database_name = config_manager._database_config.get("active_database", "default")
        
        if database_name not in cls._instances:
            cls._instances[database_name] = DatabaseManager(database_name)
        
        return cls._instances[database_name]
    
    @classmethod
    def clear_cache(cls):
        """Clear all cached database manager instances"""
        cls._instances.clear()
    
    @classmethod
    def get_all_managers(cls) -> Dict[str, DatabaseManager]:
        """Get all cached database manager instances
        
        Returns:
            Dictionary of database managers by name
        """
        return cls._instances.copy()

# Default database manager instance
def get_default_database_manager() -> DatabaseManager:
    """Get the default database manager instance
    
    Returns:
        DatabaseManager for the active database
    """
    return DatabaseFactory.get_database_manager()
