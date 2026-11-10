"""
Retail / e-commerce CDC-style data generator.

Every run produces one batch folder under ../data/ containing one CSV per
table. The first run produces an "initial" batch (all rows are inserts).
Every later run produces a "delta" batch: a mix of inserts, updates and a
few deletes, built on top of the state left behind by previous runs.

Usage:
    python generate_data.py
    python generate_data.py --reset      # wipe state and start over
"""

import argparse
import csv
import json
import os
import random
from datetime import datetime, timedelta, timezone

from faker import Faker

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
STATE_PATH = os.path.join(SCRIPT_DIR, "state.json")

fake = Faker()

CATEGORY_NAMES = [
    "Mobile Phones", "Laptops & Computers", "Televisions", "Audio & Headphones",
    "Home Appliances", "Kitchen Appliances", "Furniture", "Footwear",
    "Men's Apparel", "Women's Apparel", "Sports & Fitness", "Books & Stationery",
]

PRODUCT_WORDS = {
    "Mobile Phones": ["Nova", "Pulse", "Edge", "Zenith", "Orbit"],
    "Laptops & Computers": ["ProBook", "AirLite", "WorkStation", "UltraSlim", "GameForce"],
    "Televisions": ["UltraHD", "VividView", "CrystalScreen", "SmartVision", "ClearPixel"],
    "Audio & Headphones": ["BassBoost", "SoundWave", "EchoPods", "AudioMax", "SilentNoise"],
    "Home Appliances": ["HomeMate", "CleanPro", "AirFresh", "CoolBreeze", "PureAir"],
    "Kitchen Appliances": ["ChefMate", "QuickCook", "BlendMax", "GrillPro", "FreshBrew"],
    "Furniture": ["ComfortSit", "WoodCraft", "UrbanDesk", "CozyNest", "ModernLine"],
    "Footwear": ["SwiftStride", "TrailRunner", "UrbanStep", "ComfortWalk", "SprintFlex"],
    "Men's Apparel": ["UrbanFit", "ClassicWear", "ActiveMen", "SharpStyle", "TrendLine"],
    "Women's Apparel": ["ElegantFit", "UrbanChic", "ActiveWomen", "GraceStyle", "TrendLine"],
    "Sports & Fitness": ["FitPro", "EnduroGear", "FlexTrain", "PowerLift", "ActiveEdge"],
    "Books & Stationery": ["InkWell", "PagePro", "NoteCraft", "StudyMate", "WriteEasy"],
}

WAREHOUSES = ["WH-NORTH", "WH-SOUTH", "WH-EAST", "WH-WEST"]
PAYMENT_METHODS = ["credit_card", "debit_card", "upi", "netbanking", "wallet", "cod"]

ORDER_STATUS_FLOW = {
    "pending": ["processing", "cancelled"],
    "processing": ["shipped", "cancelled"],
    "shipped": ["delivered"],
    "delivered": ["returned", "delivered"],
    "cancelled": ["cancelled"],
    "returned": ["returned"],
}

PAYMENT_STATUS_BY_ORDER_STATUS = {
    "pending": "pending",
    "processing": "completed",
    "shipped": "completed",
    "delivered": "completed",
    "cancelled": "failed",
    "returned": "refunded",
}

INITIAL_COUNTS = {
    "customers": 250,
    "products": 120,
    "orders": 400,
}

DELTA_COUNTS = {
    "new_customers": 12,
    "updated_customers": 8,
    "deleted_customers": 2,
    "new_products": 6,
    "updated_products": 10,
    "deleted_products": 1,
    "new_orders": 25,
    "updated_orders": 15,
    "deleted_orders": 3,
    "inventory_updates": 20,
}

CSV_COLUMNS = {
    "categories": ["op", "category_id", "category_name", "parent_category_id", "created_at", "updated_at"],
    "products": ["op", "product_id", "sku", "product_name", "category_id", "price", "description", "created_at", "updated_at"],
    "customers": ["op", "customer_id", "first_name", "last_name", "email", "phone", "address_line", "city", "state", "country", "postal_code", "created_at", "updated_at"],
    "orders": ["op", "order_id", "customer_id", "order_date", "status", "total_amount", "created_at", "updated_at"],
    "order_items": ["op", "order_item_id", "order_id", "product_id", "quantity", "unit_price", "created_at", "updated_at"],
    "payments": ["op", "payment_id", "order_id", "payment_date", "amount", "payment_method", "status", "created_at", "updated_at"],
    "inventory": ["op", "inventory_id", "product_id", "warehouse_location", "quantity_on_hand", "updated_at"],
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def random_past_datetime(days_back=730):
    delta = timedelta(days=random.randint(0, days_back), seconds=random.randint(0, 86400))
    return (datetime.now(timezone.utc) - delta).isoformat()


class Batch:
    """Accumulates rows per table for a single run and writes them to CSV."""

    def __init__(self):
        self.rows = {table: [] for table in CSV_COLUMNS}

    def add(self, table, op, row):
        full_row = {"op": op}
        full_row.update(row)
        self.rows[table].append(full_row)

    def write(self, folder):
        os.makedirs(folder, exist_ok=True)
        written = {}
        for table, columns in CSV_COLUMNS.items():
            rows = self.rows[table]
            if not rows:
                continue
            path = os.path.join(folder, f"{table}.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for row in rows:
                    writer.writerow({col: row.get(col, "") for col in columns})
            written[table] = len(rows)
        return written


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "batch_number": 0,
        "next_ids": {table: 1 for table in CSV_COLUMNS},
        "categories": [],       # [{id, name}]
        "products": [],         # [{id, category_id, name, price}]
        "customers": [],        # [{id, has_orders}]
        "orders": [],           # [{id, customer_id, status, total_amount, item_ids, payment_id}]
    }


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def next_id(state, table):
    value = state["next_ids"][table]
    state["next_ids"][table] += 1
    return value


def make_product_name(category_name):
    word = random.choice(PRODUCT_WORDS[category_name])
    model = random.randint(100, 999)
    return f"{word} {model}"


def generate_categories(state, batch):
    for name in CATEGORY_NAMES:
        cid = next_id(state, "categories")
        ts = now_iso()
        batch.add("categories", "I", {
            "category_id": cid, "category_name": name, "parent_category_id": "",
            "created_at": ts, "updated_at": ts,
        })
        state["categories"].append({"id": cid, "name": name})


def create_product(state, batch, category, op="I"):
    pid = next_id(state, "products")
    name = make_product_name(category["name"])
    price = round(random.uniform(199, 89999), 2)
    ts = now_iso()
    batch.add("products", op, {
        "product_id": pid, "sku": f"SKU-{pid:06d}", "product_name": name,
        "category_id": category["id"], "price": price,
        "description": f"{name} - {category['name']}",
        "created_at": ts, "updated_at": ts,
    })
    product = {"id": pid, "category_id": category["id"], "name": name, "price": price}
    state["products"].append(product)
    for warehouse in random.sample(WAREHOUSES, k=2):
        inv_id = next_id(state, "inventory")
        batch.add("inventory", "I", {
            "inventory_id": inv_id, "product_id": pid, "warehouse_location": warehouse,
            "quantity_on_hand": random.randint(20, 500), "updated_at": ts,
        })
    return product


def create_customer(state, batch, order_date_days_back=730):
    cid = next_id(state, "customers")
    ts = random_past_datetime(order_date_days_back)
    batch.add("customers", "I", {
        "customer_id": cid, "first_name": fake.first_name(), "last_name": fake.last_name(),
        "email": fake.unique.email(), "phone": fake.phone_number(),
        "address_line": fake.street_address(), "city": fake.city(), "state": fake.state(),
        "country": "India" if random.random() < 0.7 else fake.country(),
        "postal_code": fake.postcode(), "created_at": ts, "updated_at": ts,
    })
    customer = {"id": cid, "has_orders": False}
    state["customers"].append(customer)
    return customer


def create_order(state, batch, customer):
    order_id = next_id(state, "orders")
    order_date = random_past_datetime(365)
    products = state["products"]
    chosen = random.sample(products, k=min(len(products), random.randint(1, 4)))
    item_ids = []
    total = 0.0
    for product in chosen:
        item_id = next_id(state, "order_items")
        quantity = random.randint(1, 3)
        unit_price = product["price"]
        total += quantity * unit_price
        batch.add("order_items", "I", {
            "order_item_id": item_id, "order_id": order_id, "product_id": product["id"],
            "quantity": quantity, "unit_price": unit_price,
            "created_at": order_date, "updated_at": order_date,
        })
        item_ids.append(item_id)

    status = random.choices(
        ["pending", "processing", "shipped", "delivered", "cancelled", "returned"],
        weights=[10, 15, 15, 45, 10, 5],
    )[0]
    total = round(total, 2)

    batch.add("orders", "I", {
        "order_id": order_id, "customer_id": customer["id"], "order_date": order_date,
        "status": status, "total_amount": total, "created_at": order_date, "updated_at": order_date,
    })

    payment_id = next_id(state, "payments")
    batch.add("payments", "I", {
        "payment_id": payment_id, "order_id": order_id, "payment_date": order_date,
        "amount": total, "payment_method": random.choice(PAYMENT_METHODS),
        "status": PAYMENT_STATUS_BY_ORDER_STATUS[status],
        "created_at": order_date, "updated_at": order_date,
    })

    customer["has_orders"] = True
    state["orders"].append({
        "id": order_id, "customer_id": customer["id"], "status": status,
        "total_amount": total, "item_ids": item_ids, "payment_id": payment_id,
    })


def generate_initial(state, batch):
    generate_categories(state, batch)
    for _ in range(INITIAL_COUNTS["products"]):
        category = random.choice(state["categories"])
        create_product(state, batch, category)
    for _ in range(INITIAL_COUNTS["customers"]):
        create_customer(state, batch)
    for _ in range(INITIAL_COUNTS["orders"]):
        customer = random.choice(state["customers"])
        create_order(state, batch, customer)


def generate_delta(state, batch):
    ts = now_iso()

    # --- customers: inserts, updates, soft deletes ---
    for _ in range(DELTA_COUNTS["new_customers"]):
        create_customer(state, batch, order_date_days_back=1)

    updatable_customers = [c for c in state["customers"]]
    for customer in random.sample(updatable_customers, k=min(len(updatable_customers), DELTA_COUNTS["updated_customers"])):
        batch.add("customers", "U", {
            "customer_id": customer["id"], "first_name": fake.first_name(), "last_name": fake.last_name(),
            "email": fake.unique.email(), "phone": fake.phone_number(),
            "address_line": fake.street_address(), "city": fake.city(), "state": fake.state(),
            "country": "India", "postal_code": fake.postcode(),
            "created_at": "", "updated_at": ts,
        })

    deletable_customers = [c for c in state["customers"] if not c["has_orders"]]
    for customer in random.sample(deletable_customers, k=min(len(deletable_customers), DELTA_COUNTS["deleted_customers"])):
        batch.add("customers", "D", {"customer_id": customer["id"], "updated_at": ts})
        state["customers"].remove(customer)

    # --- products: inserts, updates, soft deletes ---
    for _ in range(DELTA_COUNTS["new_products"]):
        category = random.choice(state["categories"])
        create_product(state, batch, category)

    for product in random.sample(state["products"], k=min(len(state["products"]), DELTA_COUNTS["updated_products"])):
        new_price = round(product["price"] * random.uniform(0.85, 1.15), 2)
        product["price"] = new_price
        batch.add("products", "U", {
            "product_id": product["id"], "sku": f"SKU-{product['id']:06d}", "product_name": product["name"],
            "category_id": product["category_id"], "price": new_price,
            "description": f"{product['name']} - updated price", "created_at": "", "updated_at": ts,
        })

    for product in random.sample(state["products"], k=min(len(state["products"]), DELTA_COUNTS["deleted_products"])):
        batch.add("products", "D", {"product_id": product["id"], "updated_at": ts})
        state["products"].remove(product)

    # --- inventory: quantity movements on existing products ---
    inv_candidates = state["products"]
    for product in random.sample(inv_candidates, k=min(len(inv_candidates), DELTA_COUNTS["inventory_updates"])):
        for warehouse in random.sample(WAREHOUSES, k=1):
            batch.add("inventory", "U", {
                "inventory_id": "", "product_id": product["id"], "warehouse_location": warehouse,
                "quantity_on_hand": random.randint(0, 500), "updated_at": ts,
            })

    # --- orders: new orders, status-transition updates, cancellations (hard delete) ---
    # Only orders that already existed before this run are eligible for update/delete:
    # the loader applies a whole table's rows before moving to the next table, so an
    # order created and deleted within the same batch would be gone by the time its
    # order_items/payments insert rows are applied, causing a foreign key violation.
    existing_orders = list(state["orders"])

    for _ in range(DELTA_COUNTS["new_orders"]):
        customer = random.choice(state["customers"])
        create_order(state, batch, customer)

    updatable_orders = [o for o in existing_orders if o["status"] not in ("cancelled",)]
    to_update = random.sample(updatable_orders, k=min(len(updatable_orders), DELTA_COUNTS["updated_orders"]))
    to_delete_pool = [o for o in existing_orders if o not in to_update]
    to_delete = random.sample(to_delete_pool, k=min(len(to_delete_pool), DELTA_COUNTS["deleted_orders"]))

    for order in to_update:
        next_status = random.choice(ORDER_STATUS_FLOW[order["status"]])
        order["status"] = next_status
        batch.add("orders", "U", {
            "order_id": order["id"], "customer_id": order["customer_id"], "order_date": "",
            "status": next_status, "total_amount": order["total_amount"], "created_at": "", "updated_at": ts,
        })
        batch.add("payments", "U", {
            "payment_id": order["payment_id"], "order_id": order["id"], "payment_date": "",
            "amount": order["total_amount"], "payment_method": "", "status": PAYMENT_STATUS_BY_ORDER_STATUS[next_status],
            "created_at": "", "updated_at": ts,
        })

    for order in to_delete:
        batch.add("orders", "D", {"order_id": order["id"], "updated_at": ts})
        state["orders"].remove(order)


def main():
    parser = argparse.ArgumentParser(description="Generate initial/delta CSV batches for the retail schema.")
    parser.add_argument("--reset", action="store_true", help="Discard existing state and start a fresh initial batch.")
    args = parser.parse_args()

    if args.reset and os.path.exists(STATE_PATH):
        os.remove(STATE_PATH)

    state = load_state()
    batch = Batch()
    is_initial = state["batch_number"] == 0

    if is_initial:
        generate_initial(state, batch)
    else:
        generate_delta(state, batch)

    state["batch_number"] += 1
    batch_type = "initial" if is_initial else "delta"
    folder_name = f"batch_{state['batch_number']:04d}_{batch_type}"
    folder_path = os.path.join(DATA_DIR, folder_name)

    written = batch.write(folder_path)
    save_state(state)

    print(f"Wrote {batch_type} batch '{folder_name}' to {folder_path}")
    for table, count in written.items():
        print(f"  {table}: {count} rows")


if __name__ == "__main__":
    main()
