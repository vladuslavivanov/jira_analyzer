"""Script to create database schema and sample data for testing.

This script:
1. Creates SQLite database with analysis_results table
2. Inserts sample analysis results for testing UI
3. Clear to use for development and testing
"""

import sqlite3
from pathlib import Path


def create_database():
    """Create SQLite database with schema and sample data."""
    db_path = Path("results.db")
    
    # Remove existing database if it exists
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing database: {db_path}")
    
    # Create database connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create analysis_results table
    cursor.execute("""
        CREATE TABLE analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT,
            priority TEXT,
            assignee TEXT,
            reporter TEXT,
            quality_score INTEGER,
            rationale TEXT,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("Created database schema")
    
    # Insert sample analysis results
    sample_data = [
        (
            "PROJ-001", "Fix login authentication bug", "Open", "High",
            "John Smith", "Alice Johnson", 8,
            "Good task with clear description. Acceptance criteria could be more specific."
        ),
        (
            "PROJ-002", "Implement user dashboard", "In Progress", "Medium",
            "Jane Doe", "Bob Wilson", 6,
            "Description is somewhat vague. Should define specific metrics to display."
        ),
        (
            "PROJ-003", "Update API documentation", "Done", "Low",
            None, "Alice Johnson", 9,
            "Excellent task with clear scope and deliverable."
        ),
    ]
    
    cursor.executemany("""
        INSERT INTO analysis_results
        (task_id, title, status, priority, assignee, reporter, quality_score, rationale)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, sample_data)
    
    conn.commit()
    print(f"Inserted {len(sample_data)} sample analysis results")
    
    # Verify data was inserted
    cursor.execute("SELECT COUNT(*) FROM analysis_results")
    count = cursor.fetchone()[0]
    print(f"Total analysis results in database: {count}")
    
    conn.close()
    print(f"\nDatabase created successfully: {db_path.absolute()}")
    print("The database is ready for testing the results viewer.")


if __name__ == "__main__":
    create_database()
