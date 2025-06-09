import functools
from datetime import datetime
import json
from re import S
import re
from turtle import st
from typing import Annotated, Optional, TypedDict
from urllib import response
from venv import create

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
from openai import BaseModel
from sqlalchemy import table
from sympy import O
from yarl import Query

class Employee(BaseModel):
    name: str
    department: str
    salary: int
    hire_date: Optional[str] = None

class Project(BaseModel):
    name : str
    start_date : str
    end_date : str
    budget : int
    department : str
    description : Optional[str] = None

class State(TypedDict):
    messages : Annotated[list, add_messages]
    table: str
    query_type: str
    partial_values: dict
    missing_fields: list[str]
    Query: str
    message: str
    final_query: str
    execution_result: str

class SQLAgent:
    @staticmethod
    @functools.lru_cache(maxsize=1)
    def get_llm():
        llm = ChatOllama(model="devstral", temperature=0.7, num_ctx=2048, verbose=False, keep_alive=1)
        return llm    
    @staticmethod
    @functools.lru_cache(maxsize=1)
    def get_sql_database():
        db = SQLDatabase.from_uri("sqlite:///../test.db")
        return db

    def __init__(self):
        self.llm = self.get_llm()
        self.db = self.get_sql_database()
        self.tools = []
        self.tool_names = [tool.name for tool in self.tools]
        self.Sytem_Prompt = f"""
                    Your purpose is to transform natural language requests into precise, efficient SQL queries that deliver exactly what the user needs.

                    <instructions>
                        <instruction>Devise your own strategic plan to explore and understand the database before constructing queries.</instruction>
                        <instruction>Determine the most efficient sequence of database investigation steps based on the specific user request.</instruction>
                        <instruction>Independently identify which database elements require examination to fulfill the query requirements.</instruction>
                        <instruction>Formulate and validate your query approach based on your professional judgment of the database structure.</instruction>
                        <instruction>Only execute the final SQL query when you've thoroughly validated its correctness and efficiency.</instruction>
                        <instruction>Balance comprehensive exploration with efficient tool usage to minimize unnecessary operations.</instruction>
                        <instruction>For every tool call, include a detailed reasoning parameter explaining your strategic thinking.</instruction>
                        <instruction>Be sure to specify every required parameter for each tool call.</instruction>
                    </instructions>

                    Today is {datetime.now().strftime('%Y-%m-%d')}

                    Your responses should be formatted as Markdown. Prefer using tables or lists for displaying data where appropriate.
                    Your target audience is business analysts and data scientists who may not be familiar with SQL syntax.
                    """.strip()
        
        self.DB_structure_prompt = PromptTemplate.from_template(
            template=(
                f"System : {self.Sytem_Prompt}"
                "You have access to a SQLite database. This is the database's table structure:"
                "{table_info}"
                "Your task is to write ONLY the SQL query to answer the following question."
                "Do NOT include any explanations, comments, or code block formatting (no ``` or ```sql)."
                "Return only the SQL statement as plain text."
                "{top_k} most relevant tables are shown above."
                "Question: {input}"
                "SQL Query:"
            ))
        
        self.generated_query_chain = create_sql_query_chain(
            llm=self.llm,
            db=self.db,
            prompt=self.DB_structure_prompt
        )
        self.model_map = {
            "employee": Employee,
            "project": Project
        }


    def generate_query(self, prompt):
        result = self.generated_query_chain.invoke({"question": prompt})
        result = result.strip()
        if result.startswith("```"):
            result = result.lstrip("`").replace("sql", "", 1).strip()
            result = result.rstrip("`").strip()
        return result

    def execute_query(self, query):
        try:
            result = self.db._execute(query)
            json_response = json.dumps(result, indent=2)
            return json_response
        except Exception as e:
            return f"Error executing query: {str(e)}"
        
    def parse_insert_or_update_query(self, query):
        columns = []
        values = []
        match = re.search(r'INSERT INTO (\w+)', query)
        if match:
            table = match.group(1)
            col_match = re.search(r"\((.*?)\)\s+VALUES", query, re.IGNORECASE)
            columns = [c.strip() for c in col_match.group(1).split(',')]
            val_match = re.search(r"VALUES\s*\((.*?)\)", query, re.IGNORECASE)
            values = [eval(v.strip()) for v in val_match.group(1).split(',')]
            return table, "insert", dict(zip(columns, values))
        match = re.search(r'UPDATE (\w+)', query)
        if match:
            table_name = match.group(1)
            set_match = re.search(r"SET\s+(.*?)\s+WHERE", query, re.IGNORECASE | re.DOTALL)
            assignments = set_match.group(1).split(',')
            for pair in assignments:
                key, val = pair.strip().split('=')
                columns.append(key.strip())
                values.append(eval(val.strip()))
                return table_name, "update",dict(zip(columns, values))
        return None
    
    def validate_fields(self,values, model):
        missing_fields = []
        try:
            instance = model(**values)
            return [], instance
        except Exception as e:
            for err in e.errors():
                missing_fields.append(err['loc'][0])
            return missing_fields, e

    def generate_final_sql(self, data, table: str, query_type="insert", where_clause=None):
        columns = ", ".join(data.keys())
        values = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in data.values()])
        
        if query_type.lower() == "insert":
            return f"INSERT INTO {table} ({columns}) VALUES ({values});"
        
        elif query_type.lower() == "update":
            set_clause = ", ".join([f"{col} = '{val}'" if isinstance(val, str) else f"{col} = {val}" for col, val in data.items()])
            if not where_clause:
                raise ValueError("WHERE clause required for safe update.")
            return f"UPDATE {table} SET {set_clause} WHERE {where_clause};"
        
        elif query_type.lower() == "select":
            where_clause = where_clause or "1=1"
            return f"SELECT * FROM {table} WHERE {where_clause};"

        elif query_type.lower() == "delete":
            if not where_clause:
                raise ValueError("WHERE clause required for safe delete.")
            return f"DELETE FROM {table} WHERE {where_clause};"
        
        else:
            raise ValueError("Only 'insert' or 'update' supported.")
        
class Chat:
    def __init__(self, state: State = None):
        self.llm = SQLAgent.get_llm()
        self.agent = SQLAgent()
        self.memory = MemorySaver()
        self.graph = StateGraph(State)
        self.graph.add_node("parse_and_validate", self.parse_and_validate_node)
        self.graph.add_node("ask_missing_field", self.ask_for_missing_field_node)
        self.graph.add_node("update_context", self.update_context_with_user_input_node)
        self.graph.add_node("generate_and_execute", self.generate_and_execute_final_query_node)

        self.graph.set_entry_point("parse_and_validate")

        self.graph.add_conditional_edges(
            "parse_and_validate",
            lambda state: "missing_fields" in state and len(state["missing_fields"]) > 0,
            {
                True: "ask_missing_field",
                False: "generate_and_execute"
            }
        )

        self.graph.add_edge("ask_missing_field", "update_context")
        self.graph.add_edge("update_context", "parse_and_validate")

        self.graph.set_finish_point("generate_and_execute")
        self.runner = self.graph.compile(checkpointer=self.memory)

    def ask_for_missing_field_node(self, state: State):
        missing_fields = state.get("missing_fields", [])
        if not missing_fields:
            return {"message": "All fields are filled."}
        
        next_field = missing_fields[0]
        return {"message": f"Please provide a value for the missing field: {next_field}"}
        
    def parse_and_validate_node(self, state: State):

        user_message = state["messages"][-1].content
        
        query = self.agent.generate_query(user_message)
        parsed = self.agent.parse_insert_or_update_query(query)
        
        if parsed:
            table, query_type, values = parsed
            model = self.agent.model_map.get(table.lower())
            if not model:
                return {"error": f"No model for table {table}"}
            
            missing, _ = self.agent.validate_fields(values, model)
            
            return {
                "table": table,
                "query_type": query_type,
                "partial_values": values,
                "missing_fields": missing
            }
        return {
            "info": "Unable to parse query",
            "Query": query,
            }
    
    def update_context_with_user_input_node(self, state: State):
        user_response = state["messages"][-1].content
        last_missing = state["missing_fields"][0]
        
        updated_values = state.get("partial_values", {})
        updated_values[last_missing] = user_response
        
        model = self.agent.model_map[state["table"]]
        new_missing, _ = self.agent.validate_fields(updated_values, model)
        
        return {
            "partial_values": updated_values,
            "missing_fields": new_missing
        }
    
    def generate_and_execute_final_query_node(self, state: State):
        
        query_type = state.get("query_type", "select")
        final_query = state.get("Query","")
        if query_type.lower() in ["insert", "update"]:
            table = state["table"]
            data = state["partial_values"]
        
            final_query = self.agent.generate_final_sql(data, table, query_type)
        execution_result = self.agent.execute_query(final_query)
        
        return {
            "final_query": final_query,
            "execution_result": execution_result
        }
    
    def run(self, thread_id: str, user_input: str = "List all employees with salary greater than 50000."):
        print("Start chatting with the SQL Agent. Type 'exit' to quit.\n")
        result = self.runner.invoke(
            {
                "messages": [{"role": "user", "content": user_input}]
            },
            {
                "configurable" : {
                    "thread_id": "1",
                }
            }
        )
        # Serialize messages if present in result
        if isinstance(result, dict) and "messages" in result:
            from langchain_core.messages.base import BaseMessage
            serialized = dict(result)
            serialized["messages"] = [
                {"role": getattr(msg, 'type', 'user'), "content": getattr(msg, 'content', str(msg))}
                if hasattr(msg, 'content') else msg
                for msg in serialized["messages"]
            ]
            return serialized
        return result


if __name__ == "__main__":
    # Example usage
    chat = Chat()
    response = chat.run("Insert a new employee with name 'John Doe' in salary 70000.")
    print(response)

# conversation_memory = {}    
# agent = SQLAgent()
# query = agent.generate_query("Insert a new employee with name 'John mem', and salary 70000.")
# print(query)
# llm = agent.get_llm()
# data = agent.parse_insert_or_update_query(query)
# if data:
#     table, query_type ,values = data
#     model = agent.model_map.get(table.lower())
#     if model and query_type is 'insert':
#         missing , instance= agent.validate_fields(values, model)
#         if missing:
#             print(f"Missing fields: {missing}")
#         else:
#             # Here you can save the instance to the database
#             # For example, using SQLAlchemy or any other ORM
#             # session.add(instance)
#             # session.commit()
#             # session.refresh(instance)
#             # print(f"Created instance of {model.__name__}: {instance}")
#             pass
#         print(f"Created instance of {model.__name__}: {instance}")
#     else:
#         print(f"No model found for table: {table}")
#     print(f"Table: {table}, Values: {values}")
# # result = agent.execute_query(query)
# # print(result)

