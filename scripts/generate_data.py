import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

random.seed(42)  # same random data every run

DB_PATH = Path("data/coffee_shop.db")
START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 9, 30)
NUM_CUSTOMERS = 300
NUM_ORDERS = 4000

STORES = [
    ("Brew Haven Banjara Hills", "Hyderabad", "South"),
    ("Brew Haven Indiranagar", "Bengaluru", "South"),
    ("Brew Haven T Nagar", "Chennai", "South"),
    ("Brew Haven Benz Circle", "Vijayawada", "South"),
    ("Brew Haven Koregaon Park", "Pune", "West"),
    ("Brew Haven Bandra", "Mumbai", "West"),
    ("Brew Haven Connaught Place", "Delhi", "North"),
    ("Brew Haven Sector 29", "Gurugram", "North"),
]

PRODUCTS = [
    ("Espresso", "Coffee", 120),
    ("Cappuccino", "Coffee", 180),
    ("Latte", "Coffee", 200),
    ("Cold Brew", "Coffee", 220),
    ("Masala Chai", "Tea", 100),
    ("Green Tea", "Tea", 110),
    ("Iced Lemon Tea", "Tea", 130),
    ("Chocolate Croissant", "Bakery", 150),
    ("Blueberry Muffin", "Bakery", 140),
    ("Veg Sandwich", "Food", 190),
    ("Chicken Wrap", "Food", 230),
    ("Brownie", "Dessert", 160),
]

FIRST_NAMES = ["Aarav", "Ananya", "Vihaan", "Diya", "Rohan", "Priya", "Karthik",
               "Sneha", "Arjun", "Meera", "Ishaan", "Kavya", "Rahul", "Neha",
               "Sai", "Lakshmi", "Varun", "Pooja", "Aditya", "Divya"]
LAST_NAMES = ["Reddy", "Sharma", "Nair", "Iyer", "Patel", "Singh", "Rao",
              "Gupta", "Das", "Menon", "Naidu", "Kumar"]

# busier stores and more popular products get higher weights
STORE_WEIGHTS = [10, 9, 8, 4, 7, 10, 9, 6]
PRODUCT_WEIGHTS = [6, 9, 8, 4, 10, 3, 4, 5, 4, 6, 5, 4]


def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


def create_tables(cur):
    cur.executescript("""
    DROP TABLE IF EXISTS order_items;
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS customers;
    DROP TABLE IF EXISTS products;
    DROP TABLE IF EXISTS stores;

    CREATE TABLE stores (
        store_id INTEGER PRIMARY KEY,
        store_name TEXT,
        city TEXT,
        region TEXT,
        opened_date TEXT
    );
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT,
        category TEXT,
        price REAL
    );
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name TEXT,
        city TEXT,
        signup_date TEXT,
        loyalty_member INTEGER
    );
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        store_id INTEGER,
        order_date TEXT,
        payment_method TEXT,
        total_amount REAL,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
        FOREIGN KEY (store_id) REFERENCES stores (store_id)
    );
    CREATE TABLE order_items (
        item_id INTEGER PRIMARY KEY,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        unit_price REAL,
        FOREIGN KEY (order_id) REFERENCES orders (order_id),
        FOREIGN KEY (product_id) REFERENCES products (product_id)
    );
    """)


def main():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    create_tables(cur)

    # stores
    for i, (name, city, region) in enumerate(STORES, start=1):
        opened = random_date(date(2023, 1, 1), date(2024, 12, 31))
        cur.execute("INSERT INTO stores VALUES (?, ?, ?, ?, ?)",
                    (i, name, city, region, opened.isoformat()))

    # products
    prices = {}
    for i, (name, category, price) in enumerate(PRODUCTS, start=1):
        cur.execute("INSERT INTO products VALUES (?, ?, ?, ?)",
                    (i, name, category, price))
        prices[i] = price
    product_ids = list(prices.keys())

    # customers
    cities = [s[1] for s in STORES]
    signup_dates = {}
    for cid in range(1, NUM_CUSTOMERS + 1):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        signup = random_date(START_DATE, END_DATE - timedelta(days=30))
        signup_dates[cid] = signup
        loyalty = 1 if random.random() < 0.35 else 0
        cur.execute("INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
                    (cid, name, random.choice(cities), signup.isoformat(), loyalty))

    # orders and order items
    item_id = 0
    for order_id in range(1, NUM_ORDERS + 1):
        cid = random.randint(1, NUM_CUSTOMERS)
        store_id = random.choices(range(1, len(STORES) + 1), STORE_WEIGHTS)[0]
        order_date = random_date(signup_dates[cid], END_DATE)
        payment = random.choices(["UPI", "Card", "Cash"], [55, 25, 20])[0]

        n_items = random.choices([1, 2, 3, 4], [40, 35, 18, 7])[0]
        basket = {}
        for pid in random.choices(product_ids, PRODUCT_WEIGHTS, k=n_items):
            basket[pid] = basket.get(pid, 0) + random.choice([1, 1, 1, 2])

        total = 0
        for pid, qty in basket.items():
            item_id += 1
            total += prices[pid] * qty
            cur.execute("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)",
                        (item_id, order_id, pid, qty, prices[pid]))

        cur.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
                    (order_id, cid, store_id, order_date.isoformat(), payment, total))

    conn.commit()
    conn.close()
    print("Database created at", DB_PATH)


if __name__ == "__main__":
    main()