# (difficulty, question, hand-written reference SQL)
TESTS = [
    # ---- easy ----
    ("easy", "How many customers are there?",
     "SELECT COUNT(*) FROM customers"),
    ("easy", "How many orders were paid by UPI?",
     "SELECT COUNT(*) FROM orders WHERE payment_method = 'UPI'"),
    ("easy", "What is the total revenue?",
     "SELECT SUM(total_amount) FROM orders"),
    ("easy", "List all stores in the South region.",
     "SELECT store_name FROM stores WHERE region = 'South'"),
    ("easy", "What is the most expensive product?",
     "SELECT product_name FROM products ORDER BY price DESC LIMIT 1"),
    ("easy", "How many loyalty members are there?",
     "SELECT COUNT(*) FROM customers WHERE loyalty_member = 1"),
    ("easy", "How many products are in the Bakery category?",
     "SELECT COUNT(*) FROM products WHERE category = 'Bakery'"),
    ("easy", "What is the average order value?",
     "SELECT AVG(total_amount) FROM orders"),

    # ---- medium ----
    ("medium", "Which store has the highest total revenue?",
     """SELECT s.store_name FROM orders o
        JOIN stores s ON o.store_id = s.store_id
        GROUP BY s.store_id ORDER BY SUM(o.total_amount) DESC LIMIT 1"""),
    ("medium", "Revenue by payment method",
     "SELECT payment_method, SUM(total_amount) FROM orders GROUP BY payment_method"),
    ("medium", "Top 5 best-selling products by quantity",
     """SELECT p.product_name FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        GROUP BY p.product_id ORDER BY SUM(oi.quantity) DESC LIMIT 5"""),
    ("medium", "How many orders were placed in each month of 2026?",
     """SELECT strftime('%Y-%m', order_date), COUNT(*) FROM orders
        WHERE strftime('%Y', order_date) = '2026'
        GROUP BY strftime('%Y-%m', order_date)"""),
    ("medium", "How many loyalty members signed up in each city?",
     "SELECT city, COUNT(*) FROM customers WHERE loyalty_member = 1 GROUP BY city"),
    ("medium", "What is the total revenue from the Coffee category?",
     """SELECT SUM(oi.quantity * oi.unit_price) FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE p.category = 'Coffee'"""),
    ("medium", "How many orders did each store receive?",
     """SELECT s.store_name, COUNT(*) FROM orders o
        JOIN stores s ON o.store_id = s.store_id GROUP BY s.store_id"""),
    ("medium", "Which city has the most customers?",
     "SELECT city FROM customers GROUP BY city ORDER BY COUNT(*) DESC LIMIT 1"),
    ("medium", "What is the average order value for loyalty members?",
     """SELECT AVG(o.total_amount) FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE c.loyalty_member = 1"""),
    ("medium", "How many customers placed more than 20 orders?",
     """SELECT COUNT(*) FROM (SELECT customer_id FROM orders
        GROUP BY customer_id HAVING COUNT(*) > 20)"""),

    # ---- hard ----
    ("hard", "Which product category earns the most revenue in each region?",
     """WITH r AS (
          SELECT s.region AS region, p.category AS category,
                 SUM(oi.quantity * oi.unit_price) AS revenue
          FROM order_items oi
          JOIN orders o ON oi.order_id = o.order_id
          JOIN stores s ON o.store_id = s.store_id
          JOIN products p ON oi.product_id = p.product_id
          GROUP BY s.region, p.category)
        SELECT region, category FROM (
          SELECT region, category,
                 ROW_NUMBER() OVER (PARTITION BY region ORDER BY revenue DESC) AS rn
          FROM r) WHERE rn = 1"""),
    ("hard", "What percentage of orders are paid by UPI?",
     """SELECT 100.0 * SUM(CASE WHEN payment_method = 'UPI' THEN 1 ELSE 0 END)
        / COUNT(*) FROM orders"""),
    ("hard", "Which month of 2026 had the highest revenue?",
     """SELECT strftime('%Y-%m', order_date) FROM orders
        WHERE strftime('%Y', order_date) = '2026'
        GROUP BY strftime('%Y-%m', order_date)
        ORDER BY SUM(total_amount) DESC LIMIT 1"""),
    ("hard", "Who are the top 3 customers by total spending?",
     """SELECT c.customer_name FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        GROUP BY c.customer_id ORDER BY SUM(o.total_amount) DESC LIMIT 3"""),
    ("hard", "Which stores have above-average revenue?",
     """SELECT s.store_name FROM orders o
        JOIN stores s ON o.store_id = s.store_id
        GROUP BY s.store_id
        HAVING SUM(o.total_amount) >
          (SELECT SUM(total_amount) * 1.0 / COUNT(DISTINCT store_id) FROM orders)"""),
    ("hard", "How many orders contained more than 2 different products?",
     """SELECT COUNT(*) FROM (SELECT order_id FROM order_items
        GROUP BY order_id HAVING COUNT(DISTINCT product_id) > 2)"""),
    ("hard", "Which payment method has the highest average order value?",
     """SELECT payment_method FROM orders GROUP BY payment_method
        ORDER BY AVG(total_amount) DESC LIMIT 1"""),
]