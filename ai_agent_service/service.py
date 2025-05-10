from operator import itemgetter
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama
from langchain.chat_models import ChatOpenAI
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.agents import create_sql_agent
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
import re
from langchain.chains.sql_database.query import create_sql_query_chain
from openai import OpenAI

from langchain.agents.agent_toolkits import SQLDatabaseToolkit

input_chat_prompt = PromptTemplate(
    input_variables=["table_info", "input", "top_k"],
    output_parser=StrOutputParser(),
    template=(
        "You are a SQL expert. You have access to a database.\n"
        "The following are the database table details:\n"
        "{table_info}\n\n"
        "Top {top_k} most relevant tables are shown above.\n"
        "Your task is to write only the SQL query to answer the following question.\n"
        "Do not include any explanations or comments. Only return valid SQL code.\n\n"
        "Question: {input}\n"
        "SQLQuery:"
    )
)

    
# data = input("Enter your question: ")


# Initialize the database connection
llm = ChatOllama(model="codellama")

db = SQLDatabase.from_uri("sqlite:///test.db")

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
agent = create_sql_agent(llm=llm, toolkit=toolkit, verbose=True)

query = create_sql_query_chain(llm=llm, db=db, prompt=input_chat_prompt)


response = query.invoke({"question": "which employee has the highest salary with name?"})
print(response)

# response = agent.invoke("Group the department and get project and budget?")
# print(response)
print(response)
response = response.strip("```sql")
execute_query = QuerySQLDatabaseTool(db=db)
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

chain = (
    RunnablePassthrough
    .assign(query=RunnableLambda(lambda _: response))
    .assign(result=itemgetter("query") | execute_query)
    | rephrase_answer
)

output = chain.invoke({"question": "which employee has the highest salary with name?"})
print(output)
# print(output)