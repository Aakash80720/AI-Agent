from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.agents import create_sql_agent

from langchain.chains.sql_database.query import create_sql_query_chain

from langchain.agents.agent_toolkits import SQLDatabaseToolkit
llm = ChatOllama(model="llama3")
db = SQLDatabase.from_uri("sqlite:///test.db")
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
agent = create_sql_agent(llm=llm, toolkit=toolkit, verbose=True)

query = create_sql_query_chain(llm=llm, db=db, )


response = query.invoke({"question" : "What is the highest SALARY of employee with name and department?"})
print(response)

# response = agent.invoke("Group the department and get project and budget?")
# print(response)