import sqlite3


def get_all_orders_with_products():
    """N+1 query: fetches each order's products in a loop instead of a join."""
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, customer_id, total FROM orders")
    orders = cursor.fetchall()

    result = []
    for order in orders:
        order_id = order[0]
        # bug: this executes a separate query per order -- classic N+1
        cursor.execute("SELECT name, price FROM products WHERE order_id = ?", (order_id,))
        products = cursor.fetchall()
        result.append({"order": order, "products": products})

    conn.close()
    return result


def build_report(users):
    """Repeatedly concatenates strings in a loop instead of using join."""
    report = ""
    for user in users:
        # perf: string concatenation in a loop is O(n^2)
        report += f"User: {user['name']}, Email: {user['email']}\n"
    return report
