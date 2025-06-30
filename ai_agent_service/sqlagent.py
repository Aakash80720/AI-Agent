import functools
from datetime import datetime
from re import S
import re
from turtle import st
from typing import Annotated, Optional, TypedDict
from urllib import response
from venv import create
import json

from gradio import Json
from huggingface_hub import QuestionAnsweringInput
from langchain_ollama import ChatOllama
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, add_messages
from langgraph.types import interrupt

from langchain_core.messages.tool import ToolCall
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain.memory import ConversationBufferMemory
from langchain.chains.llm import LLMChain
from marshmallow import missing
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
    intent: str
    rephrased_question: str
    question: str
    error: str
    field: str

class SQLAgent:
    @staticmethod
    @functools.lru_cache(maxsize=1)
    def get_llm():
        llm = ChatOllama(model="devstral", temperature=0.5, num_ctx=4048, verbose=False, keep_alive=1)
        return llm    
    @staticmethod
    @functools.lru_cache(maxsize=1)
    def get_sql_database():
        db = SQLDatabase.from_uri("sqlite:///test.db")
        return db

    def __init__(self):
        self.llm = self.get_llm()
        self.db = self.get_sql_database()
        self.tools = []
        self.tool_names = [tool.name for tool in self.tools]
        self.System_Prompt = f"""
                You are a highly skilled data assistant designed to convert natural language requests into optimized SQL queries.

                Your job is to ensure that the generated SQL is correct, efficient, and relevant to the user's intent, using the given database structure.

                Objectives:
                - Understand the users business-level question and convert it into accurate SQL.
                - Always validate table names and column usage with the provided schema.
                - Use joins, filters, aggregations, or CTEs as needed, based on the questions complexity.
                - Prioritize clarity and performance in the SQL output.

                Execution Strategy:
                - Explore the database schema logically.
                - Decide the optimal query structure before composing the final SQL.
                - Use table relationships, foreign keys, and constraints when necessary.
                - Ensure proper filtering and data typing for comparisons (e.g., dates, numbers).

                Decision Guidelines:
                - Avoid unnecessary table joins or subqueries.
                - Use `GROUP BY`, `HAVING`, `LIMIT`, `ORDER BY` only if the user request requires them.
                - Ensure aliases are meaningful if used.
                - Always use `AS` when naming output columns.

                Behavior Rules:
                - Never guess column names or table names — use only whats in the provided schema.
                - Never include explanations, markdown syntax, or comments.
                - Return only valid SQL — no natural language, no surrounding text.
                - Treat this prompt as an instruction, not a conversation.

                Today's date: {datetime.now().strftime('%Y-%m-%d')}
                Target user: Business analysts and data scientists (non-technical audience).
                """.strip()
        
        self.DB_structure_prompt = PromptTemplate.from_template(
            template=(
                f"System : {self.System_Prompt}\n"
                "You have access to a SQLite database. This is the database's table structure:\n\n"
                "Database Info:\n"
                "{table_info}\n"
                "Available Tables: {table_names}\n\n"
                "Your Task\n"
                "Create a SQL query based on the provided database structure and the user's question. With available tables:"
                "Your task is to write ONLY the SQL query to answer the following question."
                "Do NOT include any explanations, comments, or code block formatting (no ``` or ```sql)."
                "Only return the SQL query. No explanation, no markdown, no formatting.\n\n"
                "{top_k} most relevant tables are shown above."
                "Question: {input}"
                "SQL Query:"
            ))
        
        self.generated_query_chain = create_sql_query_chain(
            llm=self.llm,
            db=self.db,
            prompt=self.DB_structure_prompt,
        )
        self.model_map = {
            "employee": Employee,
            "project": Project
        }

        self.intention_prompt = PromptTemplate.from_template(
            template=(
                """
                    You are an intelligent SQL agent designed to assist business users in converting natural language to SQL queries.
                    Your task is to understand user questions and classify both initial requests and follow-up responses that provide missing information.

                    When analyzing a user message, determine:
                    1. Is this a new query request (insert, select, update, delete)?
                    2. Is this providing missing information for a previous request?
                    3. What specific data fields are being provided?

                    Classification categories:
                    - "INITIAL_REQUEST": A new standalone query request
                    - "MISSING_DATA_RESPONSE": Providing values for previously requested missing fields

                    For initial requests, classify the intent as:
                    - 'INSERT': Adding new records
                    - 'SELECT': Retrieving or listing data  
                    - 'UPDATE': Modifying existing records
                    - 'DELETE': Removing records

                    Conditons:
                    - If the question is about inserting new data, intent it as 'insert' and process as 'new process'.
                    - If the question is about collecting Missing fields in existing records for inserting data, intent it as 'insert' and process as 'existing process'.
                    - If the question is about selecting or listing data, intent it as 'select' and process as 'data retrieval'.
                    - If the question is about deleting or removing data, intent it as 'delete' and process as 'data deletion'.
                    - If the question is about updating existing data, intent it as 'update' and process as 'data updation'.

                    For missing data responses, identify:
                        - Which fields are being populated
                        - The values being provided
                        - Any contextual clues indicating this completes a previous request

                    Examples of missing data responses:
                        - "His department is IT" (providing department field)
                        - "She joined on 2023-01-01" (providing date field)
                        - "The salary is 75000" (providing salary field)

                    Additionally, rephrase the question to make it more clear, concise, and suitable for SQL query generation.

                    Respond in the following JSON format:
                    {{
                    "message_type": "INITIAL_REQUEST" | "MISSING_DATA_RESPONSE",
                    "intent": "INSERT" | "SELECT" | "UPDATE" | "DELETE" | null,
                    "fields_provided": {{"field_name": "value", ...}},
                    "rephrased_question": "<clear version if this is an initial request>",
                    "is_continuation": true | false
                    }}

                    Input Message: {input}
                    Context: {table_info}
                    Previous Missing Fields: {missing_fields}
                """
            )
        )

        self.check_for_missing_field_prompt = PromptTemplate.from_template(
            template=(
                """
                You are a smart SQL assistant helping business users translate their natural language into structured data.

                Below is the latest user message:
                "{input}"

                In a previous conversation, the user was trying to complete a task that required the following missing fields:
                {missing_fields}

                Your task is to determine whether the current user message provides a value for **any of the missing fields** listed above.

                If a match is found, return a JSON array with the missing field and the corresponding value.

                Use the exact format below:
                [
                    {{
                        "missing_field": "<name of the field from the missing_fields list>",
                        "value": "<user-provided value>"
                    }}
                ]

                If the message doesn't match any missing field, return an empty array: `[]`
                """))

        self.intent_chain = self.intention_prompt | self.llm | JsonOutputParser()
        self.missing_field_chain = self.check_for_missing_field_prompt | self.llm | JsonOutputParser()

        self.table_info = self.db.get_table_info()
        self.table_names = self.db.get_usable_table_names()

    def get_intent(self, question, missing_fields=None):
        result = self.intent_chain.invoke({
            "input": question,
            "table_info": self.table_info,
            "missing_fields": missing_fields if missing_fields else []
        })
        return result
    
    def get_missing_fields(self, question, missing_fields):

        result = self.missing_field_chain.invoke({
            "input": question,
            "missing_fields": missing_fields
        })
        return result if isinstance(result, list) else []

    def generate_query(self, prompt):
        result = self.generated_query_chain.invoke({"question": prompt, "table_names": self.table_names, "top_k": 3})
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
            
        else:
            raise ValueError("Only 'insert' or 'update' supported.")
        
class Chat:
    def __init__(self, state: State = None):
        self.llm = SQLAgent.get_llm()
        self.agent = SQLAgent()
        self.memory = MemorySaver()
        self.graph = StateGraph(State)
        self.graph.add_node("check_intent", self.check_intent)
        self.graph.add_node("parse_and_validate", self.parse_and_validate_node)
        self.graph.add_node("ask_missing_field", self.ask_for_missing_field_node)
        self.graph.add_node("update_context", self.update_context_with_user_input_node)
        self.graph.add_node("generate_and_execute", self.generate_and_execute_final_query_node)
        self.graph.add_node("query_executor", self.query_executor)

        self.graph.set_entry_point("check_intent")

        self.graph.add_conditional_edges("check_intent",
            lambda state: "intent" in state and state["intent"] in ["insert", "update"],
            {
                True: "parse_and_validate",
                False: "query_executor"
            }
        )

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
        self.graph.set_finish_point("query_executor")
        self.runner = self.graph.compile(checkpointer=self.memory)

    def check_for_missing_fields(self, state: State):
        """
        This node checks if the user input provides values for any missing fields.
        If it does, it returns the missing field and the value provided by the user.
        """
        user_message = state["messages"][-1].content
        missing_fields = state.get("missing_fields", [])
        
        if not missing_fields:
            return {"message": "No missing fields to check."}
        
        result = self.agent.get_missing_fields(user_message, missing_fields)
        
        if result:
            return {
                **state,
                "missing_field": result[0]["missing_field"],
                "value": result[0]["value"]
            }
        else:
            return {"message": "No missing fields provided in the user input."}

    def check_intent(self, state: State):
        user_message = state["messages"][-1].content
        missing_fields = state.get("missing_fields", [])
        intent = self.agent.get_intent(user_message, missing_fields)
        if intent["intent"] in ["insert", "update", "select", "delete"]:
            return {
                **state,
                "intent": intent["intent"],
                "rephrased_question": intent["rephrased_question"],
            }
        else:
            return {
                **state,
                "error": "Queston was not in our scope. Please try again with a valid intent.",
            }
        

    def ask_for_missing_field_node(self, state: State):
        missing_fields = state.get("missing_fields", [])
        if not missing_fields:
            return {"message": "All fields are filled."}
        
        next_field = missing_fields[0]
        return interrupt({
            **state,
            "query": f"Please provide a value for the missing field: {next_field}",
            "field": next_field
            })
        
    def query_executor(self, state: State):
        """
        This node is used to execute the query and return the result.
        """
        prompt = state.get("rephrased_question", "")
        if not prompt.strip():
            return {"error": f"'{prompt}' No query to execute. Please provide a valid question."}
        query = self.agent.generate_query(prompt)
        if not query.strip():
            return {"error": "Failed to generate a valid SQL query."}
        execution_result = self.agent.execute_query(query)
        return {
            **state,
            "execution_result": execution_result,
            "Query": query
        }
    
    def parse_and_validate_node(self, state: State):

        user_message = prompt = state.get("rephrased_question", "")
        
        query = self.agent.generate_query(user_message)
        parsed = self.agent.parse_insert_or_update_query(query)
        
        if parsed:
            table, query_type, values = parsed
            model = self.agent.model_map.get(table.lower())
            if not model:
                return {"error": f"No model for table {table}"}
            
            missing, _ = self.agent.validate_fields(values, model)
            
            return {
                **state,
                "table": table,
                "query_type": query_type,
                "partial_values": values,
                "missing_fields": missing
            }
        return {
            **state,
            "info": "Unable to parse query",
            "Query": query,
            }
    
    def check_intent_for_update(self, state: State):
        """
        This node checks the intent of the user input and returns the intent and rephrased question.
        """
        user_message = state["messages"][-1].content
        missing = state.get("missing_fields", [])
        intent = self.agent.get_intent(user_message)
        
        if intent["intent"] in ["insert", "update", "select", "delete"]:
            return {
                **state,
                "intent": intent["intent"],
                "rephrased_question": intent["rephrased_question"],
            }
        else:
            return {
                **state,
                "error": "Question was not in our scope. Please try again with a valid intent.",
            }
        
    def update_context_with_user_input_node(self, state: State):
        user_response = state["messages"][-1].content
        last_missing = state["missing_fields"][0]
        
        updated_values = state.get("partial_values", {})
        updated_values[last_missing] = user_response
        
        model = self.agent.model_map[state["table"]]
        new_missing, _ = self.agent.validate_fields(updated_values, model)
        
        return {
            **state,
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
            **state,
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
        # Create a serialized copy of the result
            serialized = dict(result)
            
            # Process the messages to a standard format
            serialized["messages"] = [
                {"role": getattr(msg, 'type', 'user'), "content": getattr(msg, 'content', str(msg))}
                if hasattr(msg, 'content') else msg
                for msg in serialized["messages"]
            ]
            
            # Check for interrupts with queries
            if "__interrupt__" in serialized and serialized["__interrupt__"]:
                for interrupt in serialized["__interrupt__"]:
                    if hasattr(interrupt, "value") and "query" in interrupt.value:
                        # Add the query to the serialized response
                        serialized["query"] = interrupt.value["query"]
                        # You might also want to include the field being requested
                        if "field" in interrupt.value:
                            serialized["field"] = interrupt.value["field"]
                        break
        
        # Return the enhanced serialized result
        return serialized
        return result


if __name__ == "__main__":
    # Example usage
    chat = Chat()
    response = chat.run("1","Insert a new employee with name 'John Doe' in salary 70000.")
    print(response)
    response = chat.run("1","His is in IT department. he joined on 2023-01-01.")
    print(response)
