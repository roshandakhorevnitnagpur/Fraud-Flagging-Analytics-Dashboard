"""
STEP 2 — Faker Data Generation Script
Generates:
  - 500 accounts
  - 50,000 transactions (~5% flagged)
  - alerts for every flagged transaction
Inserts into MySQL fraud_db
"""

import random
from datetime import datetime, timedelta
from faker import Faker
import mysql.connector

# ── Config ────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "user": "fraud_user",
    "password": "fraud_secure_pwd_123",
    "database": "fraud_db",
}

NUM_ACCOUNTS     = 500
NUM_TRANSACTIONS = 50_000
FLAG_RATE        = 0.05          # 5% of transactions will be flagged

# Fraud rules that can be triggered (we'll pick one at random for each alert)
FRAUD_RULES = [
    "High Value Single Transaction",
    "Rapid Successive Transactions",
    "Out of State Transaction",
    "Unusual Merchant Category",
    "Late Night Large Transfer",
    "Multiple Failed Attempts",
    "Round Amount Suspicious",
]

ACCOUNT_TYPES = ["Savings", "Checking", "Money Market", "Current", "Fixed Deposit"]
TXN_TYPES     = ["Withdrawal", "Deposit", "Transfer", "POS Purchase", "Online Payment", "ATM"]

fake = Faker("en_IN")   # Indian locale for realistic names/cities
random.seed(42)         # Makes results reproducible

# ── Helper: random datetime in last 2 years ───────────────────────────────────
def random_datetime():
    start = datetime.now() - timedelta(days=730)
    return start + timedelta(seconds=random.randint(0, 730 * 24 * 3600))

# ── Generate accounts ─────────────────────────────────────────────────────────
def generate_accounts(n):
    accounts = []
    for _ in range(n):
        accounts.append((
            fake.name(),                              # customer_name
            random.choice(ACCOUNT_TYPES),             # account_type
            fake.company() + " Branch",               # branch
            fake.city(),                              # city  ← account's home city
            fake.date_between("-10y", "-1y"),         # opened_date
            round(random.uniform(500, 500_000), 2),  # balance
        ))
    return accounts

# ── Generate transactions ─────────────────────────────────────────────────────
def generate_transactions(account_ids, account_cities, n, flag_rate):
    transactions = []
    flagged_indices = set(random.sample(range(n), int(n * flag_rate)))

    for i in range(n):
        acc_id   = random.choice(account_ids)
        is_flagged = 1 if i in flagged_indices else 0

        # If flagged: sometimes use a different city to simulate out-of-state fraud
        if is_flagged and random.random() < 0.4:
            txn_city = fake.city()   # different city → fraud signal
        else:
            txn_city = account_cities[acc_id]  # same city as account

        transactions.append((
            acc_id,                                     # account_id
            random_datetime(),                          # txn_date
            round(random.uniform(10, 150_000), 2),     # amount
            random.choice(TXN_TYPES),                  # txn_type
            fake.company() if random.random() > 0.2 else None,  # merchant
            txn_city,                                   # city
            is_flagged,                                 # is_flagged
        ))
    return transactions

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    conn   = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # ── 1. Insert accounts ────────────────────────────────────────────────────
    print("Generating 500 accounts...")
    accounts_data = generate_accounts(NUM_ACCOUNTS)

    cursor.executemany("""
        INSERT INTO accounts
            (customer_name, account_type, branch, city, opened_date, balance)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, accounts_data)
    conn.commit()
    print(f"  ✓ {cursor.rowcount} accounts inserted")

    # Fetch back account IDs and their home cities for FK linking
    cursor.execute("SELECT account_id, city FROM accounts")
    rows = cursor.fetchall()
    account_ids    = [r[0] for r in rows]
    account_cities = {r[0]: r[1] for r in rows}

    # ── 2. Insert transactions in batches of 5000 ─────────────────────────────
    print("Generating 50,000 transactions (this may take ~30 seconds)...")
    txn_data = generate_transactions(account_ids, account_cities, NUM_TRANSACTIONS, FLAG_RATE)

    BATCH = 5_000
    for i in range(0, NUM_TRANSACTIONS, BATCH):
        batch = txn_data[i : i + BATCH]
        cursor.executemany("""
            INSERT INTO transactions
                (account_id, txn_date, amount, txn_type, merchant, city, is_flagged)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, batch)
        conn.commit()
        print(f"  ✓ Inserted rows {i+1} – {i+len(batch)}")

    # ── 3. Build alerts for every flagged transaction ─────────────────────────
    print("Creating alerts for flagged transactions...")
    cursor.execute("SELECT txn_id, txn_date FROM transactions WHERE is_flagged = 1")
    flagged_txns = cursor.fetchall()

    alerts_data = [
        (
            txn_id,                           # txn_id
            random.choice(FRAUD_RULES),        # rule_triggered
            txn_date + timedelta(seconds=random.randint(1, 300)),  # flagged_at (shortly after)
        )
        for txn_id, txn_date in flagged_txns
    ]

    cursor.executemany("""
        INSERT INTO alerts (txn_id, rule_triggered, flagged_at)
        VALUES (%s, %s, %s)
    """, alerts_data)
    conn.commit()
    print(f"  ✓ {len(alerts_data)} alerts inserted")

    # ── 4. Summary ────────────────────────────────────────────────────────────
    print("\n── Verification ──────────────────────────────────────────")
    for table in ["accounts", "transactions", "alerts"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:15s}: {count:,} rows")

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE is_flagged = 1")
    flagged_count = cursor.fetchone()[0]
    print(f"  {'flagged txns':15s}: {flagged_count:,} ({flagged_count/NUM_TRANSACTIONS*100:.1f}%)")
    print("──────────────────────────────────────────────────────────")

    cursor.close()
    conn.close()
    print("\nDone! Your database is ready.")

if __name__ == "__main__":
    main()
