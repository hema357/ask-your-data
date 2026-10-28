import os
import re
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "coffee_shop.db"
MODEL = "openai/gpt-oss-20b"

client = Groq(api_key=os.getenv("LLM_API_KEY"))

SYSTEM_PROMPT = """You are an expert SQLite data analyst.
Given a database schema and a question, write ONE SQLite SELECT query that answers it.
Rules:
- Return only the SQL query, with no explanation and no markdown.
- Use only the tables and columns that appear in the schema.
- Use SQLite syntax (for dates use strftime or date functions).
- Write SELECT statements only.
- Money amounts are in Indian rupees.
- Dates are stored as text in YYYY-MM-DD format.
- When returning or grouping by month, use the YYYY-MM format.
- Limit results to 100 rows unless the question asks otherwise.
- If the question cannot be answered using only the tables and columns in the schema, do not guess and do not use an unrelated column as a stand-in. Reply with exactly: CANNOT_ANSWER: followed by a short reason.
- If the request asks to change, delete or drop data, reply with exactly: CANNOT_ANSWER: this app is read-only.
"""


def get_connection():
    # read-only: even a bad query cannot change or delete data
    return sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)


def get_schema():
    conn = get_connection()
    cur = conn.cursor()
    tables = [
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    parts = []
    for table in tables:
        columns = cur.execute(f"PRAGMA table_info({table})").fetchall()
        column_text = ", ".join(f"{c[1]} {c[2]}" for c in columns)

        foreign_keys = cur.execute(f"PRAGMA foreign_key_list({table})").fetchall()
        fk_text = "".join(
            f"\n  Link: {table}.{fk[3]} -> {fk[2]}.{fk[4]}" for fk in foreign_keys
        )

        samples = cur.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
        parts.append(f"Table {table}: ({column_text}){fk_text}\n  Sample rows: {samples}")
    conn.close()
    return "\n\n".join(parts)


def clean_sql(text):
    text = text.strip()
    text = re.sub(r"^```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def generate_sql(question, schema):
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\nDatabase schema:\n" + schema},
            {"role": "user", "content": question},
        ],
    )
    return clean_sql(response.choices[0].message.content)


def run_query(sql):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return columns, rows
    finally:
        conn.close()


FORBIDDEN_WORDS = [
    "insert", "update", "delete", "drop", "alter",
    "create", "attach", "detach", "pragma", "vacuum",
]


def validate_sql(sql):
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("The model returned an empty query.")
    if ";" in cleaned:
        raise ValueError("Only one SQL statement is allowed.")
    lowered = cleaned.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only SELECT queries are allowed.")
    for word in FORBIDDEN_WORDS:
        if re.search(rf"\b{word}\b", lowered):
            raise ValueError(f"Blocked keyword: {word}")
    return cleaned


def fix_sql(question, schema, bad_sql, error):
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\nDatabase schema:\n" + schema},
            {"role": "user", "content": question},
            {"role": "assistant", "content": bad_sql},
            {
                "role": "user",
                "content": f"That query failed with this error:\n{error}\n"
                           "Write a corrected SELECT query. Return only the SQL.",
            },
        ],
    )
    return clean_sql(response.choices[0].message.content)


def ask(question, schema, max_retries=2):
    sql = generate_sql(question, schema)
    error = None
    for attempt in range(max_retries + 1):
        # the model declined to answer
        if sql.strip().upper().startswith("CANNOT_ANSWER"):
            if ":" in sql:
                reason = sql.split(":", 1)[1].strip()
            else:
                reason = "this question can't be answered from the available data."
            return {"sql": "", "columns": [], "rows": [], "attempts": attempt + 1,
                    "error": f"Cannot answer: {reason}"}

        # a blocked query is refused, never "fixed" into something else
        try:
            safe_sql = validate_sql(sql)
        except ValueError as e:
            return {"sql": sql, "columns": [], "rows": [], "attempts": attempt + 1,
                    "error": f"Blocked for safety: {e}"}

        try:
            columns, rows = run_query(safe_sql)
            return {"sql": safe_sql, "columns": columns, "rows": rows,
                    "error": None, "attempts": attempt + 1}
        except Exception as e:
            error = str(e)
            if attempt < max_retries:
                sql = fix_sql(question, schema, sql, error)
    return {"sql": sql, "columns": [], "rows": [], "error": error,
            "attempts": max_retries + 1}


def summarize(question, columns, rows):
    if not rows:
        return "No results found for this question."
    facts = ""
    for i in range(len(columns) - 1, -1, -1):
        valid = [r for r in rows if isinstance(r[i], (int, float))]
        if len(valid) > 1:
            lowest = min(valid, key=lambda r: r[i])
            highest = max(valid, key=lambda r: r[i])
            facts = f"\nLowest row: {lowest}\nHighest row: {highest}"
            break  
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You explain query results to a business user in one or "
                           "two short sentences. Use only the numbers provided. "
                           "Do not invent anything. Money is in Indian rupees. "
                           "The row count only says how many rows the query returned; "
                           "never describe it as a number of records, orders or customers "
                           "unless a column in the data says so. "
                           "For any range, lowest or highest statement, use only the "
                           "Lowest row and Highest row given. "
                           "Do not mention how many rows the query returned.",
            },
            {
                "role": "user",
                "content": f"Question: {question}\nColumns: {columns}\n"
                           f"Rows (up to 20): {rows[:20]}\nRows returned by the query: {len(rows)}{facts}",
            },
        ],
    )
    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    schema = get_schema()

    print("--- Safety checks ---")
    bad_queries = [
        "DELETE FROM orders",
        "DROP TABLE customers",
        "SELECT * FROM orders; DROP TABLE orders",
        "UPDATE products SET price = 0",
    ]
    for bad in bad_queries:
        try:
            validate_sql(bad)
            print("NOT BLOCKED (problem!):", bad)
        except ValueError as e:
            print("Blocked:", bad, "->", e)

    print("\n--- Questions ---")
    questions = [
        "Monthly revenue for 2026",
        "Which payment method is most popular among loyalty members?",
        "Which product category earns the most revenue in each region?",
    ]
    for q in questions:
        print("\nQuestion:", q)
        result = ask(q, schema)
        print("SQL:", result["sql"])
        if result["error"]:
            print("Error:", result["error"])
            continue
        print("Attempts:", result["attempts"])
        for row in result["rows"][:5]:
            print(row)
        print("Summary:", summarize(q, result["columns"], result["rows"]))