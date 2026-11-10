"""
Loads generator batch folders (../data/batch_XXXX_initial|delta/) into PostgreSQL.

Each batch is applied inside a single transaction, and recorded in the
etl_batch_control table on success, so re-running the loader safely skips
batches that were already applied.

Usage:
    python load_data.py                         # load every unapplied batch, in order
    python load_data.py --batch batch_0001_initial
    python load_data.py --env-file path\\to\\.env
"""

import argparse
import csv
import os
import re
import json

import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
DEFAULT_ENV_FILE = r"D:\GIT-CODE\git_venkata\venkatab-ai-setup\.env"

TABLE_ORDER = ["categories", "products", "customers", "orders", "order_items", "payments", "inventory"]

TABLE_CONFIG = {
    "categories": {
        "pk": "category_id",
        "insert_columns": ["category_id", "category_name", "parent_category_id", "created_at", "updated_at"],
        "update_columns": ["category_name", "parent_category_id", "updated_at"],
        "delete_mode": "soft",
    },
    "products": {
        "pk": "product_id",
        "insert_columns": ["product_id", "sku", "product_name", "category_id", "price", "description", "created_at", "updated_at"],
        "update_columns": ["sku", "product_name", "category_id", "price", "description", "updated_at"],
        "delete_mode": "soft",
    },
    "customers": {
        "pk": "customer_id",
        "insert_columns": ["customer_id", "first_name", "last_name", "email", "phone", "address_line", "city", "state", "country", "postal_code", "created_at", "updated_at"],
        "update_columns": ["first_name", "last_name", "email", "phone", "address_line", "city", "state", "country", "postal_code", "updated_at"],
        "delete_mode": "soft",
    },
    "orders": {
        "pk": "order_id",
        "insert_columns": ["order_id", "customer_id", "order_date", "status", "total_amount", "created_at", "updated_at"],
        "update_columns": ["status", "total_amount", "updated_at"],
        "delete_mode": "hard",
    },
    "order_items": {
        "pk": "order_item_id",
        "insert_columns": ["order_item_id", "order_id", "product_id", "quantity", "unit_price", "created_at", "updated_at"],
        "update_columns": ["quantity", "unit_price", "updated_at"],
        "delete_mode": "hard",
    },
    "payments": {
        "pk": "payment_id",
        "insert_columns": ["payment_id", "order_id", "payment_date", "amount", "payment_method", "status", "created_at", "updated_at"],
        "update_columns": ["status", "amount", "updated_at"],
        "delete_mode": "hard",
    },
    "inventory": {
        "pk": "inventory_id",
        "insert_columns": ["inventory_id", "product_id", "warehouse_location", "quantity_on_hand", "updated_at"],
        "update_columns": ["quantity_on_hand", "updated_at"],
        "update_key": ["product_id", "warehouse_location"],
        "delete_mode": "hard",
    },
}

BATCH_FOLDER_RE = re.compile(r"^batch_(\d+)_(initial|delta)$")


def clean(value):
    return None if value in (None, "") else value


def read_batch_rows(batch_folder, table):
    path = os.path.join(batch_folder, f"{table}.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def apply_insert(cur, table, config, row):
    columns = config["insert_columns"]
    values = [clean(row.get(col)) for col in columns]
    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT ({config['pk']}) DO NOTHING"
    cur.execute(sql, values)


def apply_update(cur, table, config, row):
    columns = config["update_columns"]
    set_clause = ", ".join(f"{col} = %s" for col in columns)
    values = [clean(row.get(col)) for col in columns]

    if table == "inventory" and not clean(row.get("inventory_id")):
        key_cols = config["update_key"]
        where_clause = " AND ".join(f"{col} = %s" for col in key_cols)
        values += [clean(row.get(col)) for col in key_cols]
    else:
        where_clause = f"{config['pk']} = %s"
        values += [clean(row.get(config["pk"]))]

    sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
    cur.execute(sql, values)


def apply_delete(cur, table, config, row):
    pk_value = clean(row.get(config["pk"]))
    updated_at = clean(row.get("updated_at"))
    if config["delete_mode"] == "soft":
        cur.execute(
            f"UPDATE {table} SET is_deleted = TRUE, updated_at = %s WHERE {config['pk']} = %s",
            [updated_at, pk_value],
        )
    else:
        cur.execute(f"DELETE FROM {table} WHERE {config['pk']} = %s", [pk_value])


def apply_row(cur, table, config, row):
    op = row["op"]
    if op == "I":
        apply_insert(cur, table, config, row)
    elif op == "U":
        apply_update(cur, table, config, row)
    elif op == "D":
        apply_delete(cur, table, config, row)
    else:
        raise ValueError(f"Unknown op '{op}' in table {table}")


def load_batch(conn, batch_name, batch_folder):
    row_counts = {}
    with conn.cursor() as cur:
        for table in TABLE_ORDER:
            config = TABLE_CONFIG[table]
            rows = read_batch_rows(batch_folder, table)
            for row in rows:
                apply_row(cur, table, config, row)
            if rows:
                row_counts[table] = len(rows)

        batch_type = "initial" if "_initial" in batch_name else "delta"
        cur.execute(
            "INSERT INTO etl_batch_control (batch_name, batch_type, row_counts) VALUES (%s, %s, %s)",
            [batch_name, batch_type, Json(row_counts)],
        )
    conn.commit()
    return row_counts


def already_loaded(conn, batch_name):
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM etl_batch_control WHERE batch_name = %s", [batch_name])
        return cur.fetchone() is not None


def discover_batches():
    if not os.path.isdir(DATA_DIR):
        return []
    found = []
    for name in os.listdir(DATA_DIR):
        match = BATCH_FOLDER_RE.match(name)
        if match:
            found.append((int(match.group(1)), name))
    found.sort()
    return [name for _, name in found]


def connect(env_file):
    load_dotenv(env_file)
    return psycopg2.connect(
        host="localhost",
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ.get("POSTGRES_USER", "ai_admin"),
        password=os.environ.get("POSTGRES_PASSWORD", "ai_admin_pw"),
        dbname=os.environ.get("POSTGRES_DB", "ai_setup"),
    )


def main():
    parser = argparse.ArgumentParser(description="Load generator batches into PostgreSQL.")
    parser.add_argument("--batch", help="Load a single batch folder name (e.g. batch_0001_initial). Defaults to all unapplied batches.")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="Path to the .env file with POSTGRES_* connection settings.")
    args = parser.parse_args()

    conn = connect(args.env_file)
    try:
        batches = [args.batch] if args.batch else discover_batches()
        if not batches:
            print("No batches found.")
            return

        for batch_name in batches:
            if already_loaded(conn, batch_name):
                print(f"Skipping '{batch_name}' (already loaded).")
                continue
            batch_folder = os.path.join(DATA_DIR, batch_name)
            row_counts = load_batch(conn, batch_name, batch_folder)
            print(f"Loaded '{batch_name}': {json.dumps(row_counts)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
