from operator import itemgetter
from langchain.prompts import ChatMessagePromptTemplate, MessagesPlaceholder, ChatPromptTemplate, FewShotPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_community.embeddings import OllamaEmbeddings

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import re
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain_chroma import Chroma
from openai import OpenAI

input_chat_prompt = PromptTemplate(
    input_variables=["table_info", "input", "top_k"],
    output_parser=StrOutputParser(),
    template=(
        "You are a SQL expert. You have access to a database.\n"
        "The following are the database table details:\n"
        "{table_info}\n\n"
        "Top {top_k} most relevant tables are shown above.\n"
        "Your task is to write only the SQL query to answer the following question.\n"
        "Your job is to create a syntactically correct SQL query to run.\n"
        "Your main task to perform the CRUD operations on the database.\n"
        "You can use the following SQL commands: SELECT, INSERT, UPDATE, DELETE.\n"
        "You have to check some constrains like primary key, foreign key, unique key, not null, etc.\n"
        "Primary key is the unique identifier for a record in a table. use different or next number of last value in that Table.\n"
        "If need you can use the JOIN command to join multiple tables.\n"
        "You can use the WHERE clause to filter the results.\n"
        "Do not include any explanations or comments. Only return valid SQL code.\n\n"
        "Question: {input}\n"
        "SQLQuery:"
    )
)

    
data = input("Enter your question: ")


# Initialize the database connection
llm = ChatOllama(model="deepseek-coder:33b")


db = SQLDatabase.from_uri("sqlite:///test.db")


query = create_sql_query_chain(llm=llm, db=db, prompt=input_chat_prompt)


response = query.invoke({"question": data, "top_k": 3})
print(response)
response = response.strip("```sql")
execute_query = QuerySQLDatabaseTool(db=db, description="execute SQL query")
# match = re.search(r"SQLQuery:\s*(.*)", response, re.IGNORECASE | re.DOTALL)
output = execute_query.invoke(response)
print(output)

answer_prompt = PromptTemplate(
    input_variables=["input"],
    template="""Given the following user question, corresponding SQL query, and SQL result, answer the user question.

 Question: {question}
 SQL Query: {query}
 SQL Result: {result}
 Answer: """

)

rephrase_answer = answer_prompt | llm | StrOutputParser()
example = [
        {
            "input": "Get the project name and budget of the project with the highest budget",
            "query": "SELECT name, budget FROM project ORDER BY budget DESC LIMIT 1"
        },
        {
            "input": "Get the project name and budget of the project with the lowest budget",
            "query": "SELECT name, budget FROM project ORDER BY budget ASC LIMIT 1"
        },
        {
            "input": "Get the project name and budget of the project with the highest start date",
            "query": "SELECT name, start_date FROM project ORDER BY start_date DESC LIMIT 1"
        },
        {
            "input": "Get the project name and budget of the project with the lowest start date",
            "query": "SELECT name, start_date FROM project ORDER BY start_date ASC LIMIT 1"
        },
        {
            "input": "Get the project name and budget of the project with the highest end date",
            "query": "SELECT name, end_date FROM project ORDER BY end_date DESC LIMIT 1"
        },
        {
            "input": "Get the project name and budget of the project with the lowest end date",
            "query": "SELECT name, end_date FROM project ORDER BY end_date ASC LIMIT 1"
        },
        {
            "input": "Get the employee name and salary of the employee with the highest salary",
            "query": "SELECT name, salary FROM employee ORDER BY salary DESC LIMIT 1"
        
        },
        {
            "input": "Get the employee name and salary of the employee with the lowest salary",
            "query": "SELECT name, salary FROM employee ORDER BY salary ASC LIMIT 1"
        },
        {
            "input": "Get the employee name and salary of the employee with the highest start date",
            "query": "SELECT name, start_date FROM employee ORDER BY start_date DESC LIMIT 1"
        },
        {
            "input": "Get the employee name and salary of the employee with the lowest start date",
            "query": "SELECT name, start_date FROM employee ORDER BY start_date ASC LIMIT 1"
        },
        {
            "input": "List the names of all employees in the HR department",
            "query": "SELECT name FROM employee WHERE department = 'HR'"
        },
        {
            "input": "List the names of all employees in the Engineering department",
            "query": "SELECT name FROM employee WHERE department = 'Engineering'"
        },
        {
            "input": "List the names of all employees in the Marketing department",
            "query": "SELECT name FROM employee WHERE department = 'Marketing'"
        },
        {
            "input": "List the names of all employees in the Finance department",
            "query": "SELECT name FROM employee WHERE department = 'Finance'"
        },
        {
            "input": "List the names of all employees in the IT department",
            "query": "SELECT name FROM employee WHERE department = 'IT'"
        },
        {
            "input": "List the names of all employees in the Sales department",
            "query": "SELECT name FROM employee WHERE department = 'Sales'"
        },
        {
            "input": "List the names of all employees in the Marketing department",
            "query": "SELECT name FROM employee WHERE department = 'Marketing'"
        },
        {
            "input" : "Insert a new employee with name 'John Doe', salary 60000, and department 'Engineering'",
            "query" : "INSERT INTO employee (name, salary, department) VALUES ('John Doe', 60000, 'Engineering')"
        },
        {
            "input" : "Update the salary of employee with name 'John Doe' to 70000",
            "query" : "UPDATE employee SET salary = 70000 WHERE name = 'John Doe'"
        },
        {
            "input" : "Delete the employee with name 'John Doe'",
            "query" : "DELETE FROM employee WHERE name = 'John Doe'"
        },
        {
            "input" : "Get the project name and budget of the project with the highest budget",
            "query" : "SELECT name, budget FROM project ORDER BY budget DESC LIMIT 1"
        },
        {
            "input" : "Update the budget of project with name 'Project Alpha' to 200000",
            "query" : "UPDATE project SET budget = 200000 WHERE name = 'Project Alpha'"
        },
        {
            "input" : "Delete the project with name 'Project Alpha'",
            "query" : "DELETE FROM project WHERE name = 'Project Alpha'"
        },
        {
            "input" : "Get the employee name and salary of the employee with the highest salary",
            "query" : "SELECT name, salary FROM employee ORDER BY salary DESC LIMIT 1"
        },
        {
            "input" : "Update the salary of employee with name 'John Doe' to 70000",
            "query" : "UPDATE employee SET salary = 70000 WHERE name = 'John Doe'"
        },
        {
            "input" : "Delete the employee with name 'John Doe'",
            "query" : "DELETE FROM employee WHERE name = 'John Doe'"
        },

    ]
vectorstore = Chroma()
vectorstore.delete_collection()
sample_prompt = ChatPromptTemplate.from_messages([
    ("human", "{input}/n SQlQuery:"),
    ("ai", "{query}")
])

example_selector = SemanticSimilarityExampleSelector.from_examples(
    examples=example,
    embeddings=OllamaEmbeddings(model="llama3"),
    vectorstore_cls=Chroma,
    k=3
)


few_shot_prompt = FewShotChatMessagePromptTemplate(
     example_prompt=sample_prompt,
     example_selector=example_selector,
     output_parser=StrOutputParser(),     
 )

test = few_shot_prompt.format(input = "list the names of all employees in the HR department")
print("few shot example :",test)

final_prompt = ChatPromptTemplate.from_messages(
     [
         ("system", "You are a MySQL expert. Given an input question, "
         "create a syntactically correct MySQL query to run. Unless otherwise specificed.\n\n"
         "Here is the relevant table info: {table_info}\n\n"
         "Top {top_k} most relevant .\n\n"
         "Below are a number of examples of questions and their corresponding SQL queries."),
         few_shot_prompt,
         ("human", "{input}"),
     ]
 )

generated_query = create_sql_query_chain(
        llm=llm,
        db=db,
        prompt=final_prompt
    )

chain = (
 RunnablePassthrough.assign(query=generated_query).assign(
     result=itemgetter("query") | execute_query
 )
 | rephrase_answer
 )

query = input("Enter your question: ")
print("Final Output: ", chain.invoke({"question": query}))