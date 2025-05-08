import sqlite3

conn = sqlite3.connect("test.db")
cursor = conn.cursor()

cursor.executescript("""

CREATE TABLE project (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    start_date TEXT,
    end_date TEXT,
    budget REAL,
    department TEXT
);

INSERT INTO project (id, name, description, start_date, end_date, budget, department) VALUES
(1, 'Project Alpha', 'AI research project', '2023-01-01', '2023-12-31', 150000, 'Engineering'),
(2, 'Project Beta', 'Marketing campaign', '2023-02-01', '2023-08-31', 80000, 'Marketing'),
(3, 'Project Gamma', 'HR system upgrade', '2023-03-01', '2023-09-30', 50000, 'HR'),
(4, 'Project Delta', 'Financial analysis tool', '2023-04-01', '2023-10-31', 120000, 'Finance'),
(5, 'Project Epsilon', 'New product launch', '2023-05-01', '2023-11-30', 200000, 'Engineering'),
(6, 'Project Zeta', 'Customer feedback system', '2023-06-01', '2023-12-31', 60000, 'Marketing'),
(7, 'Project Eta', 'Employee training program', '2023-07-01', '2023-12-31', 40000, 'HR'),
(8, 'Project Theta', 'Data migration', '2023-08-01', '2023-12-31', 70000, 'Finance'),
(9, 'Project Iota', 'AI chatbot development', '2023-09-01', '2024-03-31', 180000, 'Engineering'),
(10, 'Project Kappa', 'Social media strategy', '2023-10-01', '2024-04-30', 90000, 'Marketing'),
(11, 'Project Lambda', 'Recruitment drive', '2023-11-01', '2024-05-31', 30000, 'HR'),
(12, 'Project Mu', 'Budget optimization', '2023-12-01', '2024-06-30', 110000, 'Finance'),
(13, 'Project Nu', 'Cloud infrastructure setup', '2024-01-01', '2024-07-31', 250000, 'Engineering'),
(14, 'Project Xi', 'Brand awareness campaign', '2024-02-01', '2024-08-31', 85000, 'Marketing'),
(15, 'Project Omicron', 'Employee wellness program', '2024-03-01', '2024-09-30', 45000, 'HR'),
(16, 'Project Pi', 'Risk management system', '2024-04-01', '2024-10-31', 130000, 'Finance'),
(17, 'Project Rho', 'AI-powered analytics', '2024-05-01', '2024-11-30', 220000, 'Engineering'),
(18, 'Project Sigma', 'Market research', '2024-06-01', '2024-12-31', 75000, 'Marketing'),
(19, 'Project Tau', 'HR policy review', '2024-07-01', '2024-12-31', 35000, 'HR'),
(20, 'Project Upsilon', 'Tax compliance system', '2024-08-01', '2025-02-28', 140000, 'Finance');
""")

conn.commit()
conn.close()
