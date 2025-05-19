import functools
from datetime import datetime
import json
from re import S
from urllib import response
from venv import create

from langchain_ollama import ChatOllama
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_core.messages.tool import ToolCall
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool
from sympy import O
from yarl import Query


SYSTEM_PROMPT = f"""
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

@functools.lru_cache(maxsize=1)
def get_llm():
    llm = ChatOllama(model="deepseek-coder:33b", temperature=0.7, num_ctx=2048, verbose=False, keep_alive=1)
    return llm

@functools.lru_cache(maxsize=1)
def get_sql_database():
    db = SQLDatabase.from_uri("sqlite:///test.db")
    return db

llm = get_llm()
db = get_sql_database()



def calling_tool(call: ToolCall):
    
    result = []
    return result


@tool(parse_docstring=True)
def list_tables(reasoning : str) -> str:
    """Lists all user-created tables in the database (excludes SQLite system tables).

    Args:
        reasoning: Detailed explanation of why you need to see all tables (relate to the user's query)

    Returns:
        String representation of a list containing all table names
    """
    try:
        db = get_sql_database()
        tables = db.get_table_names()
        return str(tables)
    except Exception as e:
        return f"Error listing tables: {str(e)}"

@tool(parse_docstring=True)
def execute_query(query: str, reasoning: str) -> str:
    """Executes a SQL query on the database.

    Args:
        query: The SQL query to execute
        reasoning: Detailed explanation of why you need to execute this query

    Returns:
        Result of the executed query
    """
    try:
        db = get_sql_database()
        result = db.execute(query)
        return str(result)
    except Exception as e:
        return f"Error executing query: {str(e)}"

DB_structure_prompt = PromptTemplate.from_template(
    template=(
        f"System : {SYSTEM_PROMPT}"
        "You has access to a SQLite database. This was database's Table structure:"
        "{table_info}"
        "Your task is to write only the SQL query to answer the following question."
        "Your job is to create a syntactically correct SQL query to run."
        "Your main task to perform the CRUD operations on the database."
        "{top_k} most relevant tables are shown above."
        "Question: {input}"
        "SQL Query:"
    )
)



generated_query = create_sql_query_chain(
    llm=llm,
    db=db,
    prompt= DB_structure_prompt
)

query = generated_query.invoke({"question": "What is the average salary of employees?"})
print(query)
result = db._execute(query)
json_response = json.dumps(result, indent=2)
print(json_response)
