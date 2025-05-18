import functools
from datetime import datetime
from venv import create

from langchain_ollama import ChatOllama
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from langchain_core.messages.tool import ToolCall
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool


SYSTEM_PROMPT = f"""
You are Querymancer, a master database engineer with exceptional expertise in SQLite query construction and optimization.
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
    llm = ChatOllama(model="codellama", temperature=0.7, num_ctx=2048, verbose=False, keep_alive=1)
    return llm

@functools.lru_cache(maxsize=1)
def get_sql_database():
    # Create a SQLite database in memory
    db = SQLDatabase.from_uri("sqlite:///test.db")
    return db


llm = get_llm()
db = get_sql_database()

prompt = PromptTemplate.from_template(
    template=(
        """
You are an intelligent SQL agent. Analyze the user input and extract:
- operation: one of [INSERT, READ, UPDATE, DELETE]
- table: name of the target table (e.g., USER)
- fields: key-value dictionary of column names and their provided values

Return result in JSON format only.

User Input: {user_input}
"""
    )
)

full_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", 
        """Analyze the user input and extract:
- operation: one of [INSERT, READ, UPDATE, DELETE]
- table: name of the target table (e.g., USER)
- fields: key-value dictionary of column names and their provided values

Return result in JSON format only.

User Input: {user_input}
""")
])

prompt_chain = full_prompt | llm | JsonOutputParser()

def get_available_tools():

    tools = [
       list_tables,
    ]

def calling_tool(call: ToolCall):
    # Call the tool with the provided arguments
    
    result = []
    return result


@tool(parse_docstring=True)
def list_tables() -> str:
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
    

DB_structure_prompt = PromptTemplate.from_template(
    template=(
        """
        You has access to a SQLite database. This was database's Table structure:
        {table_info}
        Your task is to write only the SQL query to answer the following question.
        Your job is to create a syntactically correct SQL query to run.
        Your main task to perform the CRUD operations on the database.
        {top_k} most relevant tables are shown above.
    """
    )
)

generated_query = create_sql_query_chain(
    llm=llm,
    db=db,
    prompt= DB_structure_prompt,
)



