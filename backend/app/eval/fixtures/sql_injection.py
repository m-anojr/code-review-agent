import sqlite3

def get_user(username):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()

def search_products(term):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%{}%'".format(term))
    return cursor.fetchall()

def delete_record(table, record_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM %s WHERE id = %d" % (table, record_id))
    conn.commit()

def update_email(user_id, email):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET email = '" + email + "' WHERE id = " + str(user_id))
    conn.commit()
