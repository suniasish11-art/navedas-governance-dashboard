"""
agent.py — Navedas Live Agent Simulator

Simulates real-time order processing and writes new orders to live_orders.db.
The dashboard reads from this DB and updates automatically.

Usage:
  python agent.py                         # run continuously (every 30s)
  python agent.py --once                  # one batch and exit
  python agent.py --interval 10 --orders 50   # custom settings
  python agent.py --reset                 # wipe DB and re-init from CSV
"""
import os, sys, time, random, argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline import find_csv
import live_store

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_INTERVAL = 30   # seconds between batches
DEFAULT_ORDERS   = 20   # new orders per batch


# ── Order generator ────────────────────────────────────────────────────────────

def _safe_num(series, default=0.0):
    return pd.to_numeric(series, errors="coerce").fillna(default)


def generate_orders(template: pd.DataFrame, n: int, batch_num: int) -> pd.DataFrame:
    """
    Generate n synthetic new orders based on the existing data distribution.
    All financial fields are derived so KPIs remain internally consistent.
    """
    # Advance date by 1 day per batch
    latest_date = template["order_date"].max()
    new_date    = latest_date + timedelta(days=batch_num)

    # Sample template rows as a structural base
    rows = template.sample(n=n, replace=True).copy().reset_index(drop=True)

    # Assign new sequential order IDs
    try:
        max_id = int(
            template["order_id"].str.extract(r"(\d+)")[0]
            .dropna().astype(float).max()
        )
    except Exception:
        max_id = 5000
    rows["order_id"]   = [f"ORD-{max_id + i + 1:05d}" for i in range(n)]
    rows["order_date"] = new_date

    # Randomize unit price & quantity ±15 %
    noise = np.random.uniform(0.85, 1.15, n)
    rows["unit_price"] = (_safe_num(rows["unit_price"]) * noise).round(2)
    rows["quantity"]   = (_safe_num(rows["quantity"]) * noise).clip(lower=1).round(0).astype(int)
    rows["total_order_value"] = (rows["unit_price"] * rows["quantity"]).round(2)

    # AI cancellation decision (~30 % cancellation rate)
    rows["ai_cancel_flag"] = np.random.choice([0, 1], n, p=[0.70, 0.30])

    for i in range(n):
        tov = float(rows.at[i, "total_order_value"])
        mp  = float(_safe_num(rows["margin_percent"]).iloc[i]) if "margin_percent" in rows else 0.30

        if rows.at[i, "ai_cancel_flag"] == 0:
            # ── Fulfilled order: zero out all cancellation/intervention cols ──
            for col in [
                "recoverable_flag", "intervention_attempted_by_navedas",
                "intervention_success", "revenue_lost_before_ai_only",
                "profit_lost_before_ai_only", "revenue_prevented_by_navedas",
                "avoidable_revenue_loss_after_navedas", "profit_lost_after_navedas",
                "margin_saved_after_navedas", "intervention_cost",
                "net_profit_impact_due_to_navedas", "recovery_rate_flag",
            ]:
                if col in rows.columns:
                    rows.at[i, col] = 0
        else:
            # ── Cancelled order ──
            rows.at[i, "revenue_lost_before_ai_only"] = round(tov, 2)
            rows.at[i, "profit_lost_before_ai_only"]  = round(tov * mp, 2)

            recoverable = np.random.choice([0, 1], p=[0.35, 0.65])
            rows.at[i, "recoverable_flag"] = recoverable

            if recoverable:
                rows.at[i, "intervention_attempted_by_navedas"] = 1
                success = np.random.choice([0, 1], p=[0.25, 0.75])
                rows.at[i, "intervention_success"] = success
                cost = round(random.uniform(5, 25), 2)
                rows.at[i, "intervention_cost"]    = cost

                if success:
                    ms = round(tov * mp, 2)
                    rows.at[i, "revenue_prevented_by_navedas"]         = round(tov, 2)
                    rows.at[i, "margin_saved_after_navedas"]           = ms
                    rows.at[i, "net_profit_impact_due_to_navedas"]     = round(ms - cost, 2)
                    rows.at[i, "avoidable_revenue_loss_after_navedas"] = 0
                    rows.at[i, "profit_lost_after_navedas"]            = 0
                    rows.at[i, "recovery_rate_flag"]                   = 1
                else:
                    rows.at[i, "revenue_prevented_by_navedas"]         = 0
                    rows.at[i, "margin_saved_after_navedas"]           = 0
                    rows.at[i, "net_profit_impact_due_to_navedas"]     = round(-(tov * mp) - cost, 2)
                    rows.at[i, "avoidable_revenue_loss_after_navedas"] = round(tov, 2)
                    rows.at[i, "profit_lost_after_navedas"]            = round(tov * mp, 2)
                    rows.at[i, "recovery_rate_flag"]                   = 0
            else:
                # Non-recoverable (legitimate AI decision)
                for col in [
                    "intervention_attempted_by_navedas", "intervention_success",
                    "intervention_cost", "revenue_prevented_by_navedas",
                    "margin_saved_after_navedas", "net_profit_impact_due_to_navedas",
                    "avoidable_revenue_loss_after_navedas", "profit_lost_after_navedas",
                    "recovery_rate_flag",
                ]:
                    if col in rows.columns:
                        rows.at[i, col] = 0

    return rows


# ── Runner ─────────────────────────────────────────────────────────────────────

def run(loop: bool = True, interval: int = DEFAULT_INTERVAL, orders_per_batch: int = DEFAULT_ORDERS):
    print("=" * 56)
    print("  Navedas Live Agent  —  Order Processing Simulator")
    print("=" * 56)

    csv_path = find_csv()
    if not csv_path:
        print("[ERROR] Source CSV not found. Place the CSV file in the dashboard folder.")
        sys.exit(1)

    # Init DB from CSV baseline if not already done
    if not live_store.db_exists():
        print("[Init] First run — loading baseline data from CSV...")
        live_store.init_from_csv(csv_path)
        print()

    template = pd.read_csv(csv_path, parse_dates=["order_date"], dayfirst=True)
    template.columns = template.columns.str.strip()

    stats = live_store.get_stats()
    print(f"[DB]     {live_store.DB_PATH}")
    print(f"[Data]   {stats['total']:,} orders in DB | {stats['batches']} prior agent batches")
    print(f"[Config] {orders_per_batch} orders/batch | interval: {interval}s")
    print(f"[Live]   Dashboard will auto-update on each batch.\n")

    batch = stats["batches"] + 1

    while True:
        try:
            t   = datetime.now().strftime("%H:%M:%S")
            new = generate_orders(template, n=orders_per_batch, batch_num=batch)
            live_store.append_orders(new, batch_id=batch)

            total     = live_store.get_stats()["total"]
            cancelled = int(new["ai_cancel_flag"].sum())
            recovered = int(new["intervention_success"].sum())
            rev_saved = float(new["revenue_prevented_by_navedas"].sum())

            print(
                f"[{t}]  Batch #{batch:03d}  "
                f"+{orders_per_batch} orders  |  "
                f"Cancelled: {cancelled}  Recovered: {recovered}  "
                f"Rev saved: ${rev_saved:,.2f}  |  "
                f"DB total: {total:,}"
            )

            batch += 1
            if not loop:
                print("[Done] Single batch complete. Dashboard will update shortly.")
                break

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n[Agent] Stopped by user. Dashboard continues running.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Navedas Live Agent")
    ap.add_argument("--once",     action="store_true", help="Process one batch and exit")
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Seconds between batches (default 30)")
    ap.add_argument("--orders",   type=int, default=DEFAULT_ORDERS,   help="New orders per batch (default 20)")
    ap.add_argument("--reset",    action="store_true", help="Wipe live DB and re-initialize from CSV")
    args = ap.parse_args()

    if args.reset and live_store.db_exists():
        os.remove(live_store.DB_PATH)
        print("[Reset] live_orders.db deleted. Will re-initialize from CSV on next run.")

    run(loop=not args.once, interval=args.interval, orders_per_batch=args.orders)
