"""
run_queries.py
Runs all 6 analytical SQL queries and prints results to terminal.
Usage: python run_queries.py
"""

import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "fraud_user",
    "password": "fraud_secure_pwd_123",
    "database": "fraud_db",
}

# ── Pretty printer ─────────────────────────────────────────────────────────────
def run_query(cursor, title, sql):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")
    cursor.execute(sql)
    rows    = cursor.fetchall()
    headers = [desc[0] for desc in cursor.description]

    # Column widths
    col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
                  for i, h in enumerate(headers)]

    # Header row
    header_line = " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))

    # Data rows
    for row in rows:
        print(" | ".join(str(v).ljust(col_widths[i]) for i, v in enumerate(row)))

    print(f"\n  → {len(rows)} row(s) returned")

# ── Queries ────────────────────────────────────────────────────────────────────

Q1 = """
-- Q1: Transaction Volume by Account Type (GROUP BY)
SELECT
    a.account_type,
    COUNT(t.txn_id)          AS total_transactions,
    SUM(t.amount)            AS total_amount,
    ROUND(AVG(t.amount), 2)  AS avg_amount,
    SUM(t.is_flagged)        AS total_flagged
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
GROUP BY a.account_type
ORDER BY total_transactions DESC;
"""

Q2 = """
-- Q2: High-Frequency Accounts (>10 txns in a single day) — HAVING
SELECT
    t.account_id,
    a.customer_name,
    DATE(t.txn_date)         AS txn_day,
    COUNT(t.txn_id)          AS txns_that_day
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
GROUP BY t.account_id, a.customer_name, DATE(t.txn_date)
HAVING txns_that_day > 10
ORDER BY txns_that_day DESC
LIMIT 20;
"""

Q3 = """
-- Q3: Amounts > 3 Standard Deviations above account average — CTE + STDDEV
WITH account_stats AS (
    SELECT
        account_id,
        AVG(amount)   AS avg_amount,
        STDDEV(amount) AS std_amount
    FROM transactions
    GROUP BY account_id
)
SELECT
    t.txn_id,
    t.account_id,
    a.customer_name,
    t.amount,
    ROUND(s.avg_amount, 2)                          AS account_avg,
    ROUND(s.avg_amount + 3 * s.std_amount, 2)       AS threshold_3std,
    t.is_flagged
FROM transactions t
JOIN account_stats s  ON t.account_id = s.account_id
JOIN accounts a       ON t.account_id = a.account_id
WHERE t.amount > (s.avg_amount + 3 * s.std_amount)
ORDER BY t.amount DESC
LIMIT 20;
"""

Q4 = """
-- Q4: Two Transactions within 5 minutes (same account) — LAG + TIMESTAMPDIFF
SELECT
    account_id,
    txn_id,
    txn_date,
    prev_txn_date,
    mins_since_last
FROM (
    SELECT
        account_id,
        txn_id,
        txn_date,
        LAG(txn_date) OVER (PARTITION BY account_id ORDER BY txn_date) AS prev_txn_date,
        TIMESTAMPDIFF(MINUTE,
            LAG(txn_date) OVER (PARTITION BY account_id ORDER BY txn_date),
            txn_date
        ) AS mins_since_last
    FROM transactions
) ranked
WHERE mins_since_last IS NOT NULL
  AND mins_since_last <= 5
ORDER BY mins_since_last ASC
LIMIT 20;
"""

Q5 = """
-- Q5: Transaction City ≠ Account City — JOIN
SELECT
    t.txn_id,
    t.account_id,
    a.customer_name,
    a.city          AS account_city,
    t.city          AS txn_city,
    t.amount,
    t.txn_date,
    t.is_flagged
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
WHERE t.city != a.city
ORDER BY t.amount DESC
LIMIT 20;
"""

Q6 = """
-- Q6: Alert Summary across all 3 tables — Multi-JOIN + Aggregation
SELECT
    al.rule_triggered,
    a.account_type,
    COUNT(al.alert_id)       AS total_alerts,
    ROUND(SUM(t.amount), 2)  AS total_flagged_amount,
    ROUND(AVG(t.amount), 2)  AS avg_flagged_amount
FROM alerts al
JOIN transactions t  ON al.txn_id    = t.txn_id
JOIN accounts a      ON t.account_id = a.account_id
GROUP BY al.rule_triggered, a.account_type
ORDER BY total_alerts DESC;
"""

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    conn   = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    run_query(cursor, "Q1 — Transaction Volume by Account Type",      Q1)
    run_query(cursor, "Q2 — High-Frequency Accounts (>10 txns/day)",  Q2)
    run_query(cursor, "Q3 — Amounts > 3 Std Dev Above Account Avg",   Q3)
    run_query(cursor, "Q4 — Two Transactions Within 5 Minutes",       Q4)
    run_query(cursor, "Q5 — Transaction City ≠ Account City",         Q5)
    run_query(cursor, "Q6 — Alert Summary Across All 3 Tables",       Q6)

    cursor.close()
    conn.close()
    print(f"\n{'═'*60}")
    print("  All 6 queries completed successfully!")
    print(f"{'═'*60}\n")

if __name__ == "__main__":
    main()
