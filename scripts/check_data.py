import sqlite3

conn = sqlite3.connect("data/coffee_shop.db")
cur = conn.cursor()

for table in ["stores", "products", "customers", "orders", "order_items"]:
    count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(table, count)

print("\nTop 3 stores by revenue:")
rows = cur.execute("""
    SELECT s.store_name, ROUND(SUM(o.total_amount), 2) AS revenue
    FROM orders o
    JOIN stores s ON o.store_id = s.store_id
    GROUP BY s.store_name
    ORDER BY revenue DESC
    LIMIT 3
""").fetchall()
for row in rows:
    print(row)

conn.close()