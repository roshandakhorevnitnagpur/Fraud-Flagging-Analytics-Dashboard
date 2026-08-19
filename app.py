"""
app.py — Fraud Analytics Dashboard
Run: streamlit run app.py
"""

import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Fraud Analytics", layout="wide")
st.title("🛡️ Bank Fraud Analytics Dashboard")
st.divider()

# ── DB Connection (cached) ─────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return mysql.connector.connect(
        host="localhost", user="fraud_user",
        password="fraud_secure_pwd_123", database="fraud_db"
    )

def query(sql):
    cur = get_conn().cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close()
    return pd.DataFrame(rows, columns=cols)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("Filters")
acc_types = ["All"] + query("SELECT DISTINCT account_type FROM accounts ORDER BY account_type")["account_type"].tolist()
selected  = st.sidebar.selectbox("Account Type", acc_types)

acc_filter = "" if selected == "All" else f"WHERE a.account_type = '{selected}'"
acc_filter_plain = "" if selected == "All" else f"WHERE account_type = '{selected}'"

# ── KPI Metrics ────────────────────────────────────────────────────────────────
kpi = query(f"""
    SELECT
        COUNT(t.txn_id)                                      AS total_txns,
        ROUND(SUM(t.amount)/1000000, 2)                      AS vol_m,
        SUM(t.is_flagged)                                    AS flagged,
        ROUND(SUM(t.is_flagged)/COUNT(t.txn_id)*100, 2)     AS flag_pct,
        (SELECT COUNT(*) FROM alerts)                        AS total_alerts
    FROM transactions t JOIN accounts a ON t.account_id = a.account_id
    {acc_filter}
""").iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Transactions", f"{int(kpi.total_txns):,}")
c2.metric("Total Volume",       f"₹{kpi.vol_m}M")
c3.metric("Flagged",            f"{int(kpi.flagged):,}")
c4.metric("Flag Rate",          f"{kpi.flag_pct}%")
c5.metric("Total Alerts",       f"{int(kpi.total_alerts):,}")

st.divider()

# ── Chart 1: Transactions by Account Type ─────────────────────────────────────
st.subheader("Transactions by Account Type")
df1 = query("""
    SELECT a.account_type,
           COUNT(t.txn_id)   AS total_transactions,
           SUM(t.is_flagged) AS flagged
    FROM transactions t JOIN accounts a ON t.account_id = a.account_id
    GROUP BY a.account_type ORDER BY total_transactions DESC
""")
df1["total_transactions"] = df1["total_transactions"].astype(int)
df1["flagged"]            = df1["flagged"].astype(int)
st.plotly_chart(
    px.bar(df1, x="account_type", y=["total_transactions", "flagged"],
           barmode="group", color_discrete_sequence=["#4C8BF5", "#E84545"]),
    width="stretch"
)

st.divider()

# ── Chart 2: Daily Trend (last 90 days) ───────────────────────────────────────
st.subheader("Daily Transactions — Last 90 Days")
if selected == "All":
    trend_sql = """
        SELECT DATE(txn_date) AS day, COUNT(*) AS total, SUM(is_flagged) AS flagged
        FROM transactions
        WHERE txn_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
        GROUP BY DATE(txn_date) ORDER BY day
    """
else:
    trend_sql = f"""
        SELECT DATE(t.txn_date) AS day, COUNT(*) AS total, SUM(t.is_flagged) AS flagged
        FROM transactions t JOIN accounts a ON t.account_id = a.account_id
        WHERE a.account_type = '{selected}'
          AND t.txn_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
        GROUP BY DATE(t.txn_date) ORDER BY day
    """
df2 = query(trend_sql)
df2["total"]   = df2["total"].astype(int)
df2["flagged"] = df2["flagged"].astype(int)
st.plotly_chart(
    px.line(df2, x="day", y=["total", "flagged"],
            color_discrete_sequence=["#4C8BF5", "#E84545"]),
    width="stretch"
)

st.divider()

# ── Chart 3: Alerts by Rule ────────────────────────────────────────────────────
st.subheader("Alerts by Fraud Rule")
df3 = query("SELECT rule_triggered, COUNT(*) AS total FROM alerts GROUP BY rule_triggered ORDER BY total DESC")
df3["total"] = df3["total"].astype(int)
st.plotly_chart(
    px.bar(df3, x="total", y="rule_triggered", orientation="h",
           color_discrete_sequence=["#E84545"]),
    width="stretch"
)

st.divider()

# ── Table 1: Top 10 Recent Flagged Transactions ────────────────────────────────
st.subheader("Top 10 Recent Flagged Transactions")
df4 = query("""
    SELECT t.txn_id, a.customer_name, a.account_type,
           t.amount, t.txn_type, t.city AS txn_city,
           a.city AS home_city, al.rule_triggered, t.txn_date
    FROM transactions t
    JOIN accounts a ON t.account_id = a.account_id
    JOIN alerts al  ON t.txn_id     = al.txn_id
    ORDER BY t.txn_date DESC LIMIT 10
""")
df4["city_flag"] = df4.apply(lambda r: "🚨 Mismatch" if r.txn_city != r.home_city else "✅ Same", axis=1)
df4["amount"]    = df4["amount"].apply(lambda x: f"₹{float(x):,.2f}")
df4.drop(columns=["txn_city", "home_city"], inplace=True)
st.dataframe(df4, hide_index=True)

st.divider()

# ── Table 2: High-Frequency Accounts (>10 txns/day) ───────────────────────────
st.subheader("High-Frequency Accounts  (> 10 transactions / day)")
df5 = query("""
    SELECT t.account_id, a.customer_name, a.account_type,
           DATE(t.txn_date) AS txn_day,
           COUNT(t.txn_id)  AS txns_that_day,
           SUM(t.is_flagged) AS flagged_count
    FROM transactions t JOIN accounts a ON t.account_id = a.account_id
    GROUP BY t.account_id, a.customer_name, a.account_type, DATE(t.txn_date)
    HAVING txns_that_day > 10
    ORDER BY txns_that_day DESC LIMIT 15
""")
st.dataframe(df5, hide_index=True)

st.caption("Vinay Shelke · B.Tech ECE · MySQL + Python + Streamlit + Plotly")
