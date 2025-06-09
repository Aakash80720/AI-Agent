# example = [
#         {
#             "input": "Get the project name and budget of the project with the highest budget",
#             "query": "SELECT name, budget FROM project ORDER BY budget DESC LIMIT 1"
#         },
#         {
#             "input": "Get the project name and budget of the project with the lowest budget",
#             "query": "SELECT name, budget FROM project ORDER BY budget ASC LIMIT 1"
#         },
#         {
#             "input": "Get the project name and budget of the project with the highest start date",
#             "query": "SELECT name, start_date FROM project ORDER BY start_date DESC LIMIT 1"
#         },
#         {
#             "input": "Get the project name and budget of the project with the lowest start date",
#             "query": "SELECT name, start_date FROM project ORDER BY start_date ASC LIMIT 1"
#         },
#         {
#             "input": "Get the project name and budget of the project with the highest end date",
#             "query": "SELECT name, end_date FROM project ORDER BY end_date DESC LIMIT 1"
#         },
#         {
#             "input": "Get the project name and budget of the project with the lowest end date",
#             "query": "SELECT name, end_date FROM project ORDER BY end_date ASC LIMIT 1"
#         },
#         {
#             "input": "Get the employee name and salary of the employee with the highest salary",
#             "query": "SELECT name, salary FROM employee ORDER BY salary DESC LIMIT 1"
        
#         },
#         {
#             "input": "Get the employee name and salary of the employee with the lowest salary",
#             "query": "SELECT name, salary FROM employee ORDER BY salary ASC LIMIT 1"
#         },
#         {
#             "input": "Get the employee name and salary of the employee with the highest start date",
#             "query": "SELECT name, start_date FROM employee ORDER BY start_date DESC LIMIT 1"
#         },
#         {
#             "input": "Get the employee name and salary of the employee with the lowest start date",
#             "query": "SELECT name, start_date FROM employee ORDER BY start_date ASC LIMIT 1"
#         },
#         {
#             "input": "List the names of all employees in the HR department",
#             "query": "SELECT name FROM employee WHERE department = 'HR'"
#         },
#         {
#             "input": "List the names of all employees in the Engineering department",
#             "query": "SELECT name FROM employee WHERE department = 'Engineering'"
#         },
#         {
#             "input": "List the names of all employees in the Marketing department",
#             "query": "SELECT name FROM employee WHERE department = 'Marketing'"
#         },
#         {
#             "input": "List the names of all employees in the Finance department",
#             "query": "SELECT name FROM employee WHERE department = 'Finance'"
#         },
#         {
#             "input": "List the names of all employees in the IT department",
#             "query": "SELECT name FROM employee WHERE department = 'IT'"
#         },
#         {
#             "input": "List the names of all employees in the Sales department",
#             "query": "SELECT name FROM employee WHERE department = 'Sales'"
#         },
#         {
#             "input": "List the names of all employees in the Marketing department",
#             "query": "SELECT name FROM employee WHERE department = 'Marketing'"
#         },
#         {
#             "input" : "Insert a new employee with name 'John Doe', salary 60000, and department 'Engineering'",
#             "query" : "INSERT INTO employee (name, salary, department) VALUES ('John Doe', 60000, 'Engineering')"
#         },
#         {
#             "input" : "Update the salary of employee with name 'John Doe' to 70000",
#             "query" : "UPDATE employee SET salary = 70000 WHERE name = 'John Doe'"
#         },
#         {
#             "input" : "Delete the employee with name 'John Doe'",
#             "query" : "DELETE FROM employee WHERE name = 'John Doe'"
#         },
#         {
#             "input" : "Get the project name and budget of the project with the highest budget",
#             "query" : "SELECT name, budget FROM project ORDER BY budget DESC LIMIT 1"
#         },
#         {
#             "input" : "Update the budget of project with name 'Project Alpha' to 200000",
#             "query" : "UPDATE project SET budget = 200000 WHERE name = 'Project Alpha'"
#         },
#         {
#             "input" : "Delete the project with name 'Project Alpha'",
#             "query" : "DELETE FROM project WHERE name = 'Project Alpha'"
#         },
#         {
#             "input" : "Get the employee name and salary of the employee with the highest salary",
#             "query" : "SELECT name, salary FROM employee ORDER BY salary DESC LIMIT 1"
#         },
#         {
#             "input" : "Update the salary of employee with name 'John Doe' to 70000",
#             "query" : "UPDATE employee SET salary = 70000 WHERE name = 'John Doe'"
#         },
#         {
#             "input" : "Delete the employee with name 'John Doe'",
#             "query" : "DELETE FROM employee WHERE name = 'John Doe'"
#         },

#     ]
# vectorstore = Chroma()
# vectorstore.delete_collection()
# sample_prompt = ChatPromptTemplate.from_messages([
#     ("human", "{input}/n SQlQuery:"),
#     ("ai", "{query}")
# ])

# try:
#     example_selector = SemanticSimilarityExampleSelector.from_examples(
#         examples=example,
#         embeddings=OllamaEmbeddings(model="llama3"),
#         vectorstore_cls=Chroma
#     )
# except Exception as e:
#     print("Error initializing SemanticSimilarityExampleSelector:", e)
#     import traceback
#     traceback.print_exc()
#     exit(1)


# few_shot_prompt = FewShotChatMessagePromptTemplate(
#      example_prompt=sample_prompt,
#      example_selector=example_selector,
#      output_parser=StrOutputParser(),     
#  )

# test = few_shot_prompt.format(input = "list the names of all employees in the HR department")
# print("few shot example :",test)

# final_prompt = ChatPromptTemplate.from_messages(
#      [
#          ("system", "You are a MySQL expert. Given an input question, "
#          "create a syntactically correct MySQL query to run. Unless otherwise specificed.\n\n"
#          "Here is the relevant table info: {table_info}\n\n"
#          "Below are a number of examples of questions and their corresponding SQL queries. use the top {top_k} most relevant examples as reference to answer the question.\n\n"),
#          few_shot_prompt,
#          ("human", "{input}"),
#      ]
#  )

# generated_query = create_sql_query_chain(
#         llm=llm,
#         db=db,
#         prompt=final_prompt
#     )

# chain = (
#  RunnablePassthrough.assign(query=generated_query).assign(
#      result=itemgetter("query") | execute_query
#  )
#  | rephrase_answer
#  )

# print("Final Output: ", chain.invoke({"question": data}))

   
# SYSTEM_PROMPT = f"""
# Your purpose is to transform natural language requests into precise, efficient SQL queries that deliver exactly what the user needs.

# <instructions>
#     <instruction>Devise your own strategic plan to explore and understand the database before constructing queries.</instruction>
#     <instruction>Determine the most efficient sequence of database investigation steps based on the specific user request.</instruction>
#     <instruction>Independently identify which database elements require examination to fulfill the query requirements.</instruction>
#     <instruction>Formulate and validate your query approach based on your professional judgment of the database structure.</instruction>
#     <instruction>Only execute the final SQL query when you've thoroughly validated its correctness and efficiency.</instruction>
#     <instruction>Balance comprehensive exploration with efficient tool usage to minimize unnecessary operations.</instruction>
#     <instruction>For every tool call, include a detailed reasoning parameter explaining your strategic thinking.</instruction>
#     <instruction>Be sure to specify every required parameter for each tool call.</instruction>
# </instructions>

# Today is {datetime.now().strftime('%Y-%m-%d')}

# Your responses should be formatted as Markdown. Prefer using tables or lists for displaying data where appropriate.
# Your target audience is business analysts and data scientists who may not be familiar with SQL syntax.
# """.strip()

# @functools.lru_cache(maxsize=1)
# def get_llm():
#     llm = ChatOllama(model="deepseek-coder:33b", temperature=0.7, num_ctx=2048, verbose=False, keep_alive=1)
#     return llm

# @functools.lru_cache(maxsize=1)
# def get_sql_database():
#     db = SQLDatabase.from_uri("sqlite:///test.db")
#     return db

# llm = get_llm()
# db = get_sql_database()



# def calling_tool(call: ToolCall):
    
#     result = []
#     return result

# @tool(parse_docstring=True)
# def insert_value(table: str, values: str, reasoning: str) -> str:
#     """Inserts a new row into the specified table.

#     Args:
#         table: The name of the table to insert into
#         values: The values to insert (in SQL format)
#         reasoning: Detailed explanation of why you need to insert this value

#     Returns:
#         Confirmation message or error message
#     """
#     try:
       
#     except Exception as e:
#         return f"Error inserting values: {str(e)}"

# @tool(parse_docstring=True)
# def list_tables(reasoning : str) -> str:
#     """Lists all user-created tables in the database (excludes SQLite system tables).

#     Args:
#         reasoning: Detailed explanation of why you need to see all tables (relate to the user's query)

#     Returns:
#         String representation of a list containing all table names
#     """
#     try:
#         db = get_sql_database()
#         tables = db.get_table_names()
#         return str(tables)
#     except Exception as e:
#         return f"Error listing tables: {str(e)}"

# @tool(parse_docstring=True)
# def execute_query(query: str, reasoning: str) -> str:
#     """Executes a SQL query on the database.

#     Args:
#         query: The SQL query to execute
#         reasoning: Detailed explanation of why you need to execute this query

#     Returns:
#         Result of the executed query
#     """
#     try:
#         db = get_sql_database()
#         result = db.execute(query)
#         return str(result)
#     except Exception as e:
#         return f"Error executing query: {str(e)}"

# DB_structure_prompt = PromptTemplate.from_template(
#     template=(
#         f"System : {SYSTEM_PROMPT}"
#         "You has access to a SQLite database. This was database's Table structure:"
#         "{table_info}"
#         "Your task is to write only the SQL query to answer the following question."
#         "Your job is to create a syntactically correct SQL query to run."
#         "Your main task to perform the CRUD operations on the database."
#         "{top_k} most relevant tables are shown above."
#         "Question: {input}"
#         "SQL Query:"
#     )
# )



# generated_query = create_sql_query_chain(
#     llm=llm,
#     db=db,
#     prompt= DB_structure_prompt
# )

# query = generated_query.invoke({"question": "What is the average salary of employees?"})
# print(query)
# result = db._execute(query)
# json_response = json.dumps(result, indent=2)
# print(json_response)

