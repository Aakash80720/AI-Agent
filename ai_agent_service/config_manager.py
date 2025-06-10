#!/usr/bin/env python3
"""
Configuration Manager for SQL Agent
Handles dynamic database connections and field configurations
"""

import json
import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class ConfigManager:
    """Centralized configuration management for SQL Agent"""
    
    def __init__(self, config_dir: str = "config"):
        """Initialize configuration manager
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self._database_config = None
        self._field_config = None
        self._agent_config = None
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        # Load all configurations
        self.load_configurations()
    
    def load_configurations(self):
        """Load all configuration files"""
        try:
            self._database_config = self._load_json_config("database_config.json")
            self._field_config = self._load_json_config("field_config.json")
            self._agent_config = self._load_json_config("agent_config.json")
            logger.info("All configurations loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configurations: {e}")
            raise
    
    def _load_json_config(self, filename: str) -> Dict[str, Any]:
        """Load a JSON configuration file
        
        Args:
            filename: Name of the configuration file
            
        Returns:
            Dictionary containing configuration data
        """
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filename}: {e}")
    
    def get_database_uri(self, database_name: Optional[str] = None) -> str:
        """Get database URI for the specified database
        
        Args:
            database_name: Name of the database configuration to use.
                          If None, uses the active database.
        
        Returns:
            Database URI string
        """
        if database_name is None:
            database_name = self._database_config.get("active_database", "default")
        
        db_config = self._database_config["databases"].get(database_name)
        if not db_config:
            raise ValueError(f"Database configuration not found: {database_name}")
        
        db_type = db_config["type"].lower()
        
        if db_type == "sqlite":
            path = db_config["path"]
            # Handle relative paths
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            return f"sqlite:///{path}"
        
        elif db_type == "mysql":
            username = quote_plus(db_config["username"])
            password = quote_plus(db_config["password"])
            host = db_config["host"]
            port = db_config.get("port", 3306)
            database = db_config["database"]
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
        
        elif db_type == "postgresql":
            username = quote_plus(db_config["username"])
            password = quote_plus(db_config["password"])
            host = db_config["host"]
            port = db_config.get("port", 5432)
            database = db_config["database"]
            return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def get_available_databases(self) -> List[str]:
        """Get list of available database configurations
        
        Returns:
            List of database configuration names
        """
        return list(self._database_config["databases"].keys())
    
    def set_active_database(self, database_name: str):
        """Set the active database configuration
        
        Args:
            database_name: Name of the database configuration to activate
        """
        if database_name not in self._database_config["databases"]:
            raise ValueError(f"Database configuration not found: {database_name}")
        
        self._database_config["active_database"] = database_name
        
        # Save updated configuration
        self._save_json_config("database_config.json", self._database_config)
        logger.info(f"Active database set to: {database_name}")
    
    def get_field_config(self, model_name: str) -> Dict[str, Any]:
        """Get field configuration for a specific model
        
        Args:
            model_name: Name of the model (e.g., 'employee', 'project')
            
        Returns:
            Dictionary containing field configuration
        """
        model_config = self._field_config["models"].get(model_name)
        if not model_config:
            raise ValueError(f"Model configuration not found: {model_name}")
        
        return model_config
    
    def get_field_description(self, model_name: str, field_name: str) -> str:
        """Get user-friendly description for a field
        
        Args:
            model_name: Name of the model
            field_name: Name of the field
            
        Returns:
            User-friendly field description
        """
        model_config = self.get_field_config(model_name)
        field_config = model_config["fields"].get(field_name)
        
        if not field_config:
            return f"Value for {field_name}"
        
        return field_config.get("user_prompt", field_config.get("description", f"Value for {field_name}"))
    
    def get_field_suggestions(self, model_name: str, field_name: str) -> List[str]:
        """Get suggestions for a field
        
        Args:
            model_name: Name of the model
            field_name: Name of the field
            
        Returns:
            List of suggested values
        """
        model_config = self.get_field_config(model_name)
        field_config = model_config["fields"].get(field_name, {})
        
        return field_config.get("suggestions", [])
    
    def get_required_fields(self, model_name: str) -> List[str]:
        """Get list of required fields for a model
        
        Args:
            model_name: Name of the model
            
        Returns:
            List of required field names
        """
        model_config = self.get_field_config(model_name)
        required_fields = []
        
        for field_name, field_config in model_config["fields"].items():
            if field_config.get("required", False):
                required_fields.append(field_name)
        
        return required_fields
    
    def get_all_models(self) -> List[str]:
        """Get list of all available models
        
        Returns:
            List of model names
        """
        return list(self._field_config["models"].keys())
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration
        
        Returns:
            Dictionary containing LLM configuration
        """
        return self._agent_config["llm"]
    
    def get_system_prompt(self) -> str:
        """Get system prompt for the agent
        
        Returns:
            Complete system prompt string
        """
        prompt_config = self._agent_config["system_prompts"]
        
        base_prompt = prompt_config["base_prompt"]
        rules = prompt_config["critical_rules"]
        instructions = prompt_config["query_generation_instructions"]
        
        prompt = f"{base_prompt}\n\nCRITICAL RULES:\n"
        for i, rule in enumerate(rules, 1):
            prompt += f"{i}. {rule}\n"
        
        prompt += "\nQUERY GENERATION INSTRUCTIONS:\n"
        for instruction in instructions:
            prompt += f"- {instruction}\n"
        
        return prompt
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration
        
        Returns:
            Dictionary containing validation settings
        """
        return self._agent_config["validation"]
    
    def get_conversation_config(self) -> Dict[str, Any]:
        """Get conversation configuration
        
        Returns:
            Dictionary containing conversation settings
        """
        return self._agent_config["conversation"]
    
    def _save_json_config(self, filename: str, data: Dict[str, Any]):
        """Save configuration data to JSON file
        
        Args:
            filename: Name of the configuration file
            data: Configuration data to save
        """
        config_path = self.config_dir / filename
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save configuration {filename}: {e}")
            raise
    
    def add_database_config(self, name: str, config: Dict[str, Any]):
        """Add a new database configuration
        
        Args:
            name: Name for the database configuration
            config: Database configuration dictionary
        """
        self._database_config["databases"][name] = config
        self._save_json_config("database_config.json", self._database_config)
        logger.info(f"Added database configuration: {name}")
    
    def add_model_config(self, name: str, config: Dict[str, Any]):
        """Add a new model configuration
        
        Args:
            name: Name for the model configuration
            config: Model configuration dictionary
        """
        self._field_config["models"][name] = config
        self._save_json_config("field_config.json", self._field_config)
        logger.info(f"Added model configuration: {name}")
    
    def get_database_info(self, database_name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a database configuration
        
        Args:
            database_name: Name of the database configuration
            
        Returns:
            Dictionary containing database information
        """
        if database_name is None:
            database_name = self._database_config.get("active_database", "default")
        
        db_config = self._database_config["databases"].get(database_name)
        if not db_config:
            raise ValueError(f"Database configuration not found: {database_name}")
        
        return {
            "name": database_name,
            "type": db_config["type"],
            "description": db_config.get("description", ""),
            "uri": self.get_database_uri(database_name),
            "is_active": database_name == self._database_config.get("active_database")
        }

# Global configuration manager instance
config_manager = ConfigManager()
