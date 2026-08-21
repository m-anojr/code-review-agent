import sqlite3

# Fake AWS Key to test the regex secret scrubber
AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE" 

def get_user_data(username):
    # SQL Injection vulnerability to test the agent
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return cursor.fetchall()
