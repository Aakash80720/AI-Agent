from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
llm = ChatOllama(model="llama3")  # use actual model name like 'llama3' or 'mistral'
db = SQLDatabase.from_uri("sqlite:///test.db")
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
agent = create_sql_agent(llm=llm, toolkit=toolkit, verbose=True)

response = agent.invoke("What is the average age of employees?")
print(response)