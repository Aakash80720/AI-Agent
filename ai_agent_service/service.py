from operator import itemgetter
from tabnanny import verbose
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
import functools


@functools.lru_cache(maxsize=1)
def get_llm():
    llm = ChatOllama(model="codellama")
    return llm

@functools.lru_cache(maxsize=1)
def get_sql_database():
    # Create a SQLite database in memory
    db = SQLDatabase.from_uri("sqlite:///test.db")
    return db


def get_or_create_vectorstore(vectorstore_cls, collection_name="default"):
    """Get or create a persistent vectorstore collection for caching."""
    return vectorstore_cls(collection_name=collection_name)

@functools.lru_cache(maxsize=1)
def get_example_selector_cached(examples_tuple, embeddings_model_name, vectorstore_cls, k):
    """Cache the example selector to avoid recomputation."""
    # Convert tuple back to list of dicts
    examples = [dict(zip(("input", "query"), ex)) for ex in examples_tuple]
    embeddings = OllamaEmbeddings(model=embeddings_model_name)
    vectorstore = get_or_create_vectorstore(vectorstore_cls)
    return SemanticSimilarityExampleSelector.from_examples(
        examples=examples,
        embeddings=embeddings,
        vectorstore_cls=vectorstore_cls,
        k=k
    )

def create_few_shot_prompt(example_selector, sample_prompt):
    return FewShotChatMessagePromptTemplate(
        example_prompt=sample_prompt,
        example_selector=example_selector,
        output_parser=StrOutputParser(),
    )


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


# Initialize the LLM
llm = get_llm()


db = get_sql_database()


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
    template="""Given the following user question, corresponding User Question, and SQL result, answer the question with following results.
    Question: {question}
    SQL Query: {query}
    SQL Result: {result}
 Answer: """

)

rephrase_answer = answer_prompt | llm | StrOutputParser()

chain = (
 RunnablePassthrough.assign(query=query).assign(
     result=itemgetter("query") | execute_query
 )
 | rephrase_answer
 )

print("Final Output: ", chain.invoke({"question": data}))