#!/usr/bin/env python3
"""
Setup script to create the database tables for testing
"""

import sqlite3
import os

def setup_test_database():
    """Create the test database with employee and project tables"""
    db_path = "test.db"
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")
    
    # Create new database and tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create employee table
    cursor.execute("""
        CREATE TABLE employee (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT,
            salary REAL,
            hire_date TEXT
        )
    """)
    
    # Create project table
    cursor.execute("""
        CREATE TABLE project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            start_date TEXT,
            end_date TEXT,
            budget REAL,
            department TEXT
        )
    """)
    
    # Insert some sample data
    sample_employees = [
        ("Alice Johnson", "Engineering", 85000, "2023-01-15"),
        ("Bob Smith", "Marketing", 65000, "2023-02-01"),
        ("Carol Davis", "Engineering", 90000, "2022-12-10"),
        ("David Wilson", "Sales", 70000, "2023-03-01"),
        ("Eve Brown", "HR", 75000, "2023-01-20")
    ]
    
    cursor.executemany(
        "INSERT INTO employee (name, department, salary, hire_date) VALUES (?, ?, ?, ?)",
        sample_employees
    )
    
    sample_projects = [
        ("Website Redesign", "Redesign company website", "2023-01-01", "2023-06-30", 50000, "Engineering"),
        ("Marketing Campaign", "Q2 product launch campaign", "2023-04-01", "2023-06-30", 25000, "Marketing"),
        ("Database Migration", "Migrate to cloud database", "2023-02-01", "2023-04-30", 75000, "Engineering")
    ]
    
    cursor.executemany(
        "INSERT INTO project (name, description, start_date, end_date, budget, department) VALUES (?, ?, ?, ?, ?, ?)",
        sample_projects
    )
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database created successfully: {db_path}")
    print("📊 Sample data added:")
    print("   - 5 employees in Engineering, Marketing, Sales, HR departments")
    print("   - 3 projects with various budgets and timelines")

if __name__ == "__main__":
    setup_test_database()
