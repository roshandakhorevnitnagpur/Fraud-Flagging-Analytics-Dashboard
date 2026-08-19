# Fraud-Flagging Bank Transactions Analytics Dashboard

> An end-to-end data analytics project simulating a real banking fraud detection system — built with Python, MySQL, and Streamlit.

---

## What This Project Does

Banks process millions of transactions daily. Detecting fraud in real time requires fast queries, statistical analysis, and clear reporting.

This project simulates exactly that:
- A **MySQL database** with 500 accounts and 50,000 transactions
- **6 SQL queries** that flag suspicious activity using real fraud-detection logic
- A **live Streamlit dashboard** to visualize transaction patterns and alerts

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Database | MySQL 8.0 | Industry-standard relational database |
| Data Generation | Python + Faker | Realistic fake data for testing |
| DB Connector | mysql-connector-python | Official MySQL driver for Python |
| Dashboard | Streamlit | Fast prototyping of data apps |
| Charts | Plotly | Interactive charts |
| Data Passing | Pandas | Only used to pass SQL results to Streamlit |

> **Design choice:** Raw SQL handles all analysis. Pandas is intentionally kept minimal — only used to pass query results to the frontend.

---

## Database Schema

```
┌─────────────────────┐         ┌──────────────────────────┐         ┌──────────────────────┐
│      accounts       │         │       transactions        │         │        alerts        │
├─────────────────────┤         ├──────────────────────────┤         ├──────────────────────┤
│ account_id (PK)     │◄───────┤ account_id (FK)           │◄───────┤ txn_id (FK)          │
│ customer_name       │         │ txn_id (PK)              │         │ alert_id (PK)        │
│ account_type        │         │ txn_date                 │         │ rule_triggered       │
│ branch              │         │ amount                   │         │ flagged_at           │
│ city                │         │ txn_type                 │         └──────────────────────┘
│ opened_date         │         │ merchant                 │
│ balance             │         │ city                     │
└─────────────────────┘         │ is_flagged               │
                                └──────────────────────────┘
```

**Key design decisions:**
- `DECIMAL(15,2)` for money — avoids floating-point rounding errors that `FLOAT` would cause
- Foreign keys with `ON DELETE CASCADE` — deleting an account removes its transactions and alerts automatically
- Dedicated `fraud_user` instead of `root` — principle of least privilege

---

## SQL Concepts Used

| # | Query | SQL Concept | Business Question |
|---|---|---|---|
| Q1 | Volume by account type | `GROUP BY`, `COUNT`, `SUM` | Which account type has the most activity? |
| Q2 | High-frequency accounts | `HAVING` | Which accounts did >10 txns in a single day? |
| Q3 | Statistical outliers | `CTE`, `STDDEV()` | Which transactions are >3σ above account average? |
| Q4 | Rapid successive txns | `LAG()`, `TIMESTAMPDIFF()` | Two txns from same account within 5 minutes? |
| Q5 | Geographic mismatch | `JOIN`, `WHERE` | Transactions in a different city than account home? |
| Q6 | Alert summary | 3-table `JOIN`, aggregation | Full picture — what rules fired, how often, how much? |

### HAVING vs WHERE — the key difference
```sql
-- WHERE filters individual rows BEFORE grouping
-- HAVING filters groups AFTER grouping

-- This finds accounts with more than 10 txns on a single day:
SELECT account_id, DATE(txn_date), COUNT(*) AS daily_count
FROM transactions
GROUP BY account_id, DATE(txn_date)
HAVING daily_count > 10;   -- can't use WHERE here — count doesn't exist yet
```

### Window Functions — LAG() explained
```sql
-- LAG() looks at the PREVIOUS row in a sorted partition
-- PARTITION BY account_id means: restart for each account
-- ORDER BY txn_date means: sort by time within each account

LAG(txn_date) OVER (PARTITION BY account_id ORDER BY txn_date)
-- gives you the timestamp of the previous transaction for the same account
```

---

## Project Structure

```
sql/
├── setup_db.sql          # Creates fraud_db, fraud_user, and all 3 tables
├── generate_data.py      # Seeds 500 accounts, 50k transactions, ~2500 alerts
├── run_queries.py        # Runs all 6 SQL queries and prints results to terminal
├── app.py                # Streamlit dashboard
├── run_dashboard.bat     # Double-click to launch dashboard (Windows)
├── .vscode/
│   └── launch.json       # VS Code Run button config for Streamlit
├── .gitignore
└── README.md
```

---

## Setup & Run

### Prerequisites
- Python 3.8+
- MySQL 8.0 running locally
- MySQL added to system PATH

### Step 1 — Clone the repo
```bash
git clone <your-repo-url>
cd sql
```

### Step 2 — Create virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux
```

### Step 3 — Install dependencies
```bash
pip install streamlit plotly pandas mysql-connector-python faker
```

### Step 4 — Set up the database
```bash
mysql -u root -p < setup_db.sql
```
Creates: `fraud_db`, user `fraud_user` / `fraud_secure_pwd_123`, and all 3 tables.

### Step 5 — Seed data
```bash
python generate_data.py
```
Expected output:
```
✓ 500 accounts inserted
✓ Inserted rows 1 – 5000
...
accounts        : 500 rows
transactions    : 50,000 rows
alerts          : ~2,500 rows
flagged txns    : ~2,500 (5.0%)
```

### Step 6 — Run the dashboard
```bash
streamlit run app.py
```
Opens at: **http://localhost:8501**

---

## Dashboard

| Section | What it shows |
|---|---|
| KPI Cards | Total transactions, volume, flagged count, flag rate, alert count |
| Bar Chart | Transactions by account type — total vs flagged |
| Donut Chart | Clean vs flagged split |
| Line Chart | Daily transaction volume for last 90 days |
| Alert Bar Chart | Breakdown by fraud rule triggered |
| Top 10 Table | Most recent flagged transactions (all 3 tables joined) |
| High-Freq Table | Accounts with >10 txns in a single day |
| Sidebar Filter | Filter everything by account type |

---

## Performance Notes

- **Batch inserts** — `executemany()` with batches of 5,000 rows is ~50× faster than inserting one row at a time
- **`@st.cache_resource`** — MySQL connection is opened once and reused across all page refreshes, not reconnected every time
- **Indexed FKs** — MySQL auto-indexes foreign keys, making JOINs on `account_id` and `txn_id` fast even at 50k rows

---

## Sample Fraud Rules

| Rule | Logic |
|---|---|
| High Value Single Transaction | Amount > 3 standard deviations above account's own average |
| Rapid Successive Transactions | Two transactions from same account within 5 minutes |
| Out of State Transaction | Transaction city ≠ account's registered city |
| Late Night Large Transfer | Large transfer between 12AM–4AM |
| Round Amount Suspicious | Exact round amounts (e.g. ₹10,000.00) which are atypical |

---
