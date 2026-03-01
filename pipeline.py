"""
pipeline.py — Data ingestion and KPI computation for Executive Governance Dashboard.
Single entry point: load_and_compute(csv_path) -> (df, kpis, trend_df, reason_df, residual_df, demand_df)
"""
import os
import pandas as pd
import numpy as np


# ── CSV Loader ────────────────────────────────────────────────────────────────

def find_csv():
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "ecommerce_ production_dataset_5000_rows.csv"),
        os.path.join(os.path.expanduser("~"), "ecommerce_ production_dataset_5000_rows.csv"),
        os.path.join(os.path.expanduser("~"), "Downloads", "ecommerce_ production_dataset_5000_rows.csv"),
        os.path.join(os.path.expanduser("~"), "Documents", "ecommerce_ production_dataset_5000_rows.csv"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return None


def load_csv(path=None):
    if path is None:
        path = find_csv()
    if path is None or not os.path.exists(path):
        raise FileNotFoundError("Dataset not found. Place the CSV in the parent folder of this app.")
    df = pd.read_csv(path, parse_dates=["order_date"], dayfirst=True)
    df.columns = df.columns.str.strip()
    num_cols = [
        "ai_cancel_flag", "recoverable_flag", "intervention_attempted_by_navedas",
        "intervention_success", "revenue_lost_before_ai_only", "revenue_prevented_by_navedas",
        "avoidable_revenue_loss_after_navedas", "profit_lost_before_ai_only",
        "profit_lost_after_navedas", "margin_saved_after_navedas", "intervention_cost",
        "net_profit_impact_due_to_navedas", "recovery_rate_flag",
        "total_order_value", "margin_percent", "unit_price", "quantity",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


# ── KPI Computation ───────────────────────────────────────────────────────────

def compute_kpis(df):
    total_orders       = len(df)
    ai_cancelled       = int(df["ai_cancel_flag"].sum())
    ai_cancel_rate     = ai_cancelled / total_orders * 100

    rev_lost_before    = df["revenue_lost_before_ai_only"].sum()
    profit_lost_before = df["profit_lost_before_ai_only"].sum()

    recoverable        = int(df["recoverable_flag"].sum())
    pct_recoverable    = recoverable / ai_cancelled * 100 if ai_cancelled else 0

    recovered          = int(df["intervention_success"].sum())
    recovery_rate_pool = recovered / recoverable * 100 if recoverable else 0
    net_cancel_reduction = recovered / ai_cancelled * 100 if ai_cancelled else 0

    rev_prevented      = df["revenue_prevented_by_navedas"].sum()
    margin_saved       = df["margin_saved_after_navedas"].sum()
    intervention_cost  = df["intervention_cost"].sum()
    net_profit_impact  = df["net_profit_impact_due_to_navedas"].sum()
    gov_roi            = margin_saved / intervention_cost if intervention_cost else 0

    residual_rev_loss  = df["avoidable_revenue_loss_after_navedas"].sum()
    residual_prof_loss = df["profit_lost_after_navedas"].sum()

    legit_non_recover  = df[(df["ai_cancel_flag"] == 1) & (df["recoverable_flag"] == 0)]
    legit_rev_loss     = legit_non_recover["revenue_lost_before_ai_only"].sum()

    return {
        "total_orders":          total_orders,
        "ai_cancelled":          ai_cancelled,
        "ai_cancel_rate":        ai_cancel_rate,
        "rev_lost_before":       rev_lost_before,
        "profit_lost_before":    profit_lost_before,
        "recoverable":           recoverable,
        "pct_recoverable":       pct_recoverable,
        "recovered":             recovered,
        "recovery_rate_pool":    recovery_rate_pool,
        "net_cancel_reduction":  net_cancel_reduction,
        "rev_prevented":         rev_prevented,
        "margin_saved":          margin_saved,
        "intervention_cost":     intervention_cost,
        "net_profit_impact":     net_profit_impact,
        "gov_roi":               gov_roi,
        "residual_rev_loss":     residual_rev_loss,
        "residual_prof_loss":    residual_prof_loss,
        "legit_rev_loss":        legit_rev_loss,
        "legit_non_recover_count": len(legit_non_recover),
    }


# ── Breakdown Tables ──────────────────────────────────────────────────────────

def compute_trend(df):
    d = df.copy()
    d["month"] = d["order_date"].dt.to_period("M").astype(str)
    g = d.groupby("month").agg(
        total=("order_id", "count"),
        cancelled=("ai_cancel_flag", "sum"),
        recovered=("intervention_success", "sum"),
        rev_prevented=("revenue_prevented_by_navedas", "sum"),
    ).reset_index()
    g["cancel_rate"]   = g["cancelled"] / g["total"] * 100
    g["recovery_rate"] = g["recovered"] / g["cancelled"].replace(0, np.nan) * 100
    return g


def compute_reason_performance(df):
    cancelled = df[df["ai_cancel_flag"] == 1].copy()
    g = cancelled.groupby("cancellation_reason").agg(
        total_cancelled=("order_id", "count"),
        recoverable=("recoverable_flag", "sum"),
        recovered=("intervention_success", "sum"),
        rev_prevented=("revenue_prevented_by_navedas", "sum"),
        margin_saved=("margin_saved_after_navedas", "sum"),
    ).reset_index()
    g["recovery_rate"] = (
        g["recovered"] / g["recoverable"].replace(0, np.nan) * 100
    ).fillna(0)
    return g.sort_values("rev_prevented", ascending=False)


def compute_residual_breakdown(df):
    failed = df[(df["recoverable_flag"] == 1) & (df["intervention_success"] == 0)].copy()
    if failed.empty:
        return pd.DataFrame(columns=["reason", "count", "rev_loss", "profit_loss"])
    g = (
        failed.groupby("intervention_failure_reason")
        .agg(
            count=("order_id", "count"),
            rev_loss=("avoidable_revenue_loss_after_navedas", "sum"),
            profit_loss=("profit_lost_after_navedas", "sum"),
        )
        .reset_index()
        .rename(columns={"intervention_failure_reason": "reason"})
    )
    return g.sort_values("rev_loss", ascending=False)


def compute_demand_impact(df):
    g = df.groupby("demand_level").agg(
        total=("order_id", "count"),
        cancelled=("ai_cancel_flag", "sum"),
        rev_prevented=("revenue_prevented_by_navedas", "sum"),
        margin_saved=("margin_saved_after_navedas", "sum"),
        net_profit=("net_profit_impact_due_to_navedas", "sum"),
    ).reset_index()
    g["cancel_rate"] = g["cancelled"] / g["total"] * 100
    return g


# ── Main entry point ──────────────────────────────────────────────────────────

def load_and_compute(csv_path=None):
    df        = load_csv(csv_path)
    kpis      = compute_kpis(df)
    trend_df  = compute_trend(df)
    reason_df = compute_reason_performance(df)
    resid_df  = compute_residual_breakdown(df)
    demand_df = compute_demand_impact(df)
    return df, kpis, trend_df, reason_df, resid_df, demand_df
