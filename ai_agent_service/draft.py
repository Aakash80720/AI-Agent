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