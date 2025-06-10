#!/usr/bin/env python3
"""
Dynamic Table Analyzer using LLM
Analyzes database tables and generates intelligent aliases and mappings
"""

import json
import logging
from typing import Dict, List, Any, Optional
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

class TableAnalyzer:
    """LLM-powered table analyzer for dynamic alias generation"""
    
    def __init__(self, llm_config: Dict[str, Any]):
        """Initialize the table analyzer with LLM configuration"""
        self.llm = ChatOllama(**llm_config)
        
    def analyze_table_semantics(self, table_name: str, columns: List[str]) -> Dict[str, Any]:
        """Analyze table semantics using LLM to generate intelligent aliases and patterns"""
        
        analysis_prompt = f"""
Analyze this database table and provide intelligent insights:

Table Name: {table_name}
Columns: {', '.join(columns)}

Based on the table name and columns, provide a JSON response with:
1. "domain" - What domain/category this table belongs to (e.g., "hr", "finance", "project_management", "inventory", etc.)
2. "entity_type" - What type of entity this represents (e.g., "person", "transaction", "product", "event", etc.)
3. "common_aliases" - List of 5-10 common aliases people might use for this table
4. "semantic_keywords" - List of related keywords that users might mention when referring to this table
5. "business_context" - Brief description of what this table is used for in business context

Example format:
{{
    "domain": "human_resources",
    "entity_type": "person",
    "common_aliases": ["emp", "employees", "staff", "workers", "personnel", "team", "members"],
    "semantic_keywords": ["hire", "salary", "department", "work", "job", "employment", "career"],
    "business_context": "Stores employee information for HR management and payroll processing"
}}

Respond ONLY with valid JSON:
"""
        
        try:
            # Get LLM analysis
            chain = self.llm | StrOutputParser()
            response = chain.invoke(analysis_prompt)
            
            # Parse JSON response
            analysis = json.loads(response.strip())
            
            # Validate required fields
            required_fields = ["domain", "entity_type", "common_aliases", "semantic_keywords", "business_context"]
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = self._get_fallback_value(field, table_name, columns)
            
            logger.info(f"Successfully analyzed table {table_name}: {analysis['domain']} domain")
            return analysis
            
        except Exception as e:
            logger.warning(f"LLM analysis failed for table {table_name}: {e}")
            return self._get_fallback_analysis(table_name, columns)
    
    def _get_fallback_value(self, field: str, table_name: str, columns: List[str]) -> Any:
        """Provide fallback values if LLM analysis fails"""
        fallbacks = {
            "domain": "general",
            "entity_type": "record",
            "common_aliases": [table_name[:3], table_name + "s" if not table_name.endswith('s') else table_name[:-1]],
            "semantic_keywords": columns[:3],
            "business_context": f"Table for storing {table_name} related data"
        }
        return fallbacks.get(field, "unknown")
    
    def _get_fallback_analysis(self, table_name: str, columns: List[str]) -> Dict[str, Any]:
        """Provide complete fallback analysis if LLM fails"""
        return {
            "domain": self._infer_domain_from_name(table_name),
            "entity_type": self._infer_entity_type(table_name, columns),
            "common_aliases": self._generate_basic_aliases(table_name),
            "semantic_keywords": self._extract_semantic_keywords(table_name, columns),
            "business_context": f"Database table for managing {table_name} records"
        }
    
    def _infer_domain_from_name(self, table_name: str) -> str:
        """Infer domain from table name patterns"""
        name_lower = table_name.lower()
        
        domain_patterns = {
            "human_resources": ["employee", "staff", "worker", "person", "user"],
            "project_management": ["project", "task", "assignment", "milestone"],
            "finance": ["invoice", "payment", "transaction", "account", "budget"],
            "inventory": ["product", "item", "stock", "inventory", "warehouse"],
            "sales": ["customer", "client", "order", "sale", "lead"],
            "support": ["ticket", "issue", "support", "help", "request"]
        }
        
        for domain, keywords in domain_patterns.items():
            if any(keyword in name_lower for keyword in keywords):
                return domain
        
        return "general"
    
    def _infer_entity_type(self, table_name: str, columns: List[str]) -> str:
        """Infer entity type from table name and columns"""
        name_lower = table_name.lower()
        columns_lower = [col.lower() for col in columns]
        
        # Check for person-related patterns
        if any(keyword in name_lower for keyword in ["employee", "user", "person", "staff", "customer", "client"]):
            return "person"
        
        # Check for transaction patterns
        if any(keyword in name_lower for keyword in ["transaction", "payment", "order", "invoice"]):
            return "transaction"
        
        # Check for event patterns
        if any(keyword in name_lower for keyword in ["event", "log", "history", "audit"]):
            return "event"
        
        # Check for product patterns
        if any(keyword in name_lower for keyword in ["product", "item", "inventory", "stock"]):
            return "product"
        
        # Check for project patterns
        if any(keyword in name_lower for keyword in ["project", "task", "assignment"]):
            return "project"
        
        # Check columns for additional hints
        if any(col in columns_lower for col in ["name", "title", "description"]):
            return "entity"
        
        return "record"
    
    def _generate_basic_aliases(self, table_name: str) -> List[str]:
        """Generate basic aliases using simple rules"""
        aliases = []
        name_lower = table_name.lower()
        
        # Add abbreviation
        if len(table_name) >= 3:
            aliases.append(table_name[:3])
        
        # Add plural/singular variations
        if name_lower.endswith('s'):
            aliases.append(name_lower[:-1])  # Remove 's' for singular
        else:
            aliases.append(name_lower + 's')  # Add 's' for plural
        
        # Add common variations based on patterns
        variations = {
            "employee": ["emp", "staff", "worker", "personnel"],
            "project": ["proj", "task", "work"],
            "customer": ["client", "cust"],
            "product": ["item", "prod"],
            "order": ["purchase", "sale"]
        }
        
        for pattern, vars in variations.items():
            if pattern in name_lower:
                aliases.extend(vars)
        
        return list(set(aliases))  # Remove duplicates
    
    def _extract_semantic_keywords(self, table_name: str, columns: List[str]) -> List[str]:
        """Extract semantic keywords from table name and columns"""
        keywords = []
        
        # Add table name parts
        name_parts = table_name.lower().replace('_', ' ').split()
        keywords.extend(name_parts)
        
        # Add relevant columns (exclude technical columns)
        technical_columns = {'id', 'created_at', 'updated_at', 'deleted_at', 'timestamp'}
        relevant_columns = [col for col in columns if col.lower() not in technical_columns]
        keywords.extend(relevant_columns[:5])  # Limit to top 5 columns
        
        return list(set(keywords))

    def generate_enhanced_aliases(self, table_schemas: Dict[str, Dict]) -> Dict[str, Any]:
        """Generate enhanced aliases for all tables using LLM analysis"""
        enhanced_mapping = {}
        
        for table_name, schema in table_schemas.items():
            columns = schema.get('columns', [])
            
            # Get LLM analysis
            analysis = self.analyze_table_semantics(table_name, columns)
            
            # Generate aliases based on analysis
            aliases = {}
            for alias in analysis.get('common_aliases', []):
                aliases[alias.lower()] = table_name
            
            # Add semantic keyword mappings
            for keyword in analysis.get('semantic_keywords', []):
                if keyword.lower() != table_name.lower():
                    aliases[keyword.lower()] = table_name
            
            enhanced_mapping[table_name] = {
                'aliases': aliases,
                'analysis': analysis
            }
        
        return enhanced_mapping
