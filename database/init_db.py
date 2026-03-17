import sqlite3
import os

db_path = r'c:\Users\55829\OneDrive\Desktop\Leopoldina.D\database\leopoldina.db'
sql_path = r'c:\Users\55829\OneDrive\Desktop\Leopoldina.D\database\schema.sql'

# Ensure directory exists
os.makedirs(os.path.dirname(db_path), exist_ok=True)

try:
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(sql_script)
    conn.commit()
    conn.close()
    print("Database initialized successfully!")
except Exception as e:
    print(f"Error: {e}")
