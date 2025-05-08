

import sqlite3

conn = sqlite3.connect("test.db")
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE employee (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT,
    salary REAL,
    hire_date TEXT
);

INSERT INTO employee (id, name, department, salary, hire_date) VALUES
(1, 'Alice Johnson', 'Engineering', 75000, '2020-03-15'),
(2, 'Bob Smith', 'Marketing', 62000, '2019-06-10'),
(3, 'Carol Lee', 'HR', 58000, '2021-01-22'),
(4, 'David Kim', 'Engineering', 80000, '2018-09-05'),
(5, 'Eve Turner', 'Finance', 72000, '2022-07-18');
""")

conn.commit()
conn.close()
