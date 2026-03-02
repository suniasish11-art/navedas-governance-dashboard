"""
live_store.py — SQLite-based live data store for real-time agent integration.

The Navedas agent writes processed orders here.
The dashboard reads from here and updates automatically when this file changes.
"""
import os
import sqlite3
import pandas as pd
from datetime import datetime

_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DIR, "live_orders.db")


def db_exists() -> bool:
    return os.path.exists(DB_PATH)


def get_mtime() -> float:
    """Return file modification timestamp (0 if DB not yet created)."""
    return os.path.getmtime(DB_PATH) if db_exists() else 0.0


def init_from_csv(csv_path: str) -> int:
    """
    Initialize live DB from a baseline CSV file.
    Marks all baseline rows as batch 0 (not an agent run).
    Returns number of rows loaded.
    """
    df = pd.read_csv(csv_path, parse_dates=["order_date"], dayfirst=True)
    df.columns = df.columns.str.strip()
    df["_batch"] = 0
    df["_ts"]    = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("orders", conn, if_exists="replace", index=False)
    conn.close()
    print(f"[Store] DB initialized: {len(df):,} baseline orders  →  {DB_PATH}")
    return len(df)


def append_orders(new_df: pd.DataFrame, batch_id: int) -> None:
    """Append new agent-processed orders to the live DB."""
    df = new_df.copy()
    df["_batch"] = batch_id
    df["_ts"]    = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("orders", conn, if_exists="append", index=False)
    conn.close()


def load_orders() -> pd.DataFrame:
    """Load all orders as a clean DataFrame (internal cols stripped)."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM orders", conn)
    conn.close()
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    return df.drop(columns=["_batch", "_ts"], errors="ignore")


def get_stats() -> dict:
    """Return a stats dict about the live DB for the sidebar panel."""
    if not db_exists():
        return {"total": 0, "batches": 0, "latest_ts": None, "latest_n": 0}
    conn = sqlite3.connect(DB_PATH)
    total   = int(pd.read_sql("SELECT COUNT(*) AS n FROM orders", conn).iloc[0]["n"])
    batches = int(pd.read_sql(
        "SELECT COUNT(DISTINCT _batch) AS n FROM orders WHERE _batch > 0", conn
    ).iloc[0]["n"])
    latest = pd.read_sql(
        "SELECT _ts, COUNT(*) AS n FROM orders "
        "WHERE _batch > 0 GROUP BY _batch ORDER BY _batch DESC LIMIT 1",
        conn,
    )
    conn.close()
    return {
        "total":     total,
        "batches":   batches,
        "latest_ts": latest.iloc[0]["_ts"] if not latest.empty else None,
        "latest_n":  int(latest.iloc[0]["n"]) if not latest.empty else 0,
    }
