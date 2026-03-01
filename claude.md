# Navedas Executive Governance Dashboard — claude.md

> **Client-shareable architecture and methodology document.**
> Covers data pipeline, KPI definitions, ROI logic, visual design, and future roadmap.

---

## 1. Architecture Overview

```
governance-dashboard/
├── app.py          — Streamlit UI layer (hero, KPI cards, all charts, raw explorer)
├── pipeline.py     — Data ingestion + KPI computation (single source of truth)
├── requirements.txt
└── claude.md       — This document
```

**Data flow:**
```
CSV on disk
  --> pipeline.load_csv()         -- parse, coerce numerics
  --> pipeline.compute_kpis()     -- aggregate KPIs into flat dict
  --> pipeline.compute_trend()    -- monthly time series
  --> pipeline.compute_reason_performance()
  --> pipeline.compute_residual_breakdown()
  --> pipeline.compute_demand_impact()
  --> app.py renders all sections using Plotly + Streamlit
```

All computation is isolated in `pipeline.py`. `app.py` only calls `load_and_compute()` — a single cached entry point. This makes the pipeline independently testable and reusable.

---

## 2. Tech Stack

| Layer       | Technology         | Reason                                     |
|-------------|--------------------|--------------------------------------------|
| UI          | Streamlit 1.28+    | Rapid interactive dashboard, no JS needed  |
| Charts      | Plotly 5.18+       | Enterprise-grade interactivity, waterfall  |
| Data        | pandas 2.0+        | Robust CSV parsing and groupby operations  |
| Math        | numpy 1.24+        | Safe division with `.replace(0, np.nan)`   |
| Fonts       | Google Fonts/Inter | Premium, legible executive typography      |

No database. No backend server. All computation runs in-process on the local machine.

---

## 3. Dataset Schema

**File:** `ecommerce_ production_dataset_5000_rows.csv` (5,000 rows, 24 columns)

| Column                              | Type    | Description                                         |
|-------------------------------------|---------|-----------------------------------------------------|
| order_id                            | string  | Unique order identifier                             |
| order_date                          | date    | Order placement date (DD-MM-YYYY)                   |
| demand_level                        | string  | High / Medium / Low demand segment                  |
| unit_price                          | float   | Price per unit                                      |
| quantity                            | int     | Units ordered                                       |
| total_order_value                   | float   | unit_price x quantity                               |
| margin_percent                      | float   | Gross margin ratio (0–1)                            |
| ai_cancel_flag                      | 0/1     | 1 = AI auto-cancelled this order                   |
| cancellation_reason                 | string  | Reason AI cancelled (e.g., Payment Expired)         |
| order_status_before_ai_only         | string  | Cancelled / Fulfilled before governance             |
| revenue_lost_before_ai_only         | float   | Revenue lost if no intervention                     |
| recoverable_flag                    | 0/1     | 1 = cancellation was a logic gap (recoverable)      |
| intervention_attempted_by_navedas   | 0/1     | 1 = Navedas tried to intervene                      |
| intervention_success                | 0/1     | 1 = intervention succeeded                          |
| intervention_failure_reason         | string  | Why intervention failed (if applicable)             |
| order_status_after_navedas          | string  | Final order status post-intervention                |
| revenue_prevented_by_navedas        | float   | Revenue saved by successful intervention            |
| avoidable_revenue_loss_after_navedas| float   | Residual recoverable revenue still lost             |
| profit_lost_before_ai_only          | float   | Profit lost before governance                       |
| profit_lost_after_navedas           | float   | Residual profit loss after governance               |
| margin_saved_after_navedas          | float   | Margin recovered by Navedas                         |
| intervention_cost                   | float   | Cost of governance intervention per order           |
| net_profit_impact_due_to_navedas    | float   | margin_saved - intervention_cost                    |
| recovery_rate_flag                  | 0/1     | 1 = order successfully recovered                    |

---

## 4. KPI Formulas

### AI Performance Layer

| KPI                        | Formula                                              |
|----------------------------|------------------------------------------------------|
| Total Orders               | COUNT(all rows)                                      |
| AI Cancellation Rate       | SUM(ai_cancel_flag) / Total Orders * 100             |
| Revenue Lost (AI-Only)     | SUM(revenue_lost_before_ai_only)                     |
| Profit Lost (AI-Only)      | SUM(profit_lost_before_ai_only)                      |

### Recoverability Layer

| KPI                          | Formula                                                      |
|------------------------------|--------------------------------------------------------------|
| Recoverable Orders           | SUM(recoverable_flag)                                        |
| % Recoverable of Cancelled   | Recoverable / AI_Cancelled * 100                             |
| Recovery Rate (Pool Basis)   | SUM(intervention_success) / Recoverable * 100                |
| Net Cancellation Reduction % | SUM(intervention_success) / AI_Cancelled * 100               |

**Two denominator distinction:**
- **Recovery Rate (Pool Basis):** denominator = recoverable orders only. Measures Navedas effectiveness on cases it could act on.
- **Net Cancellation Reduction %:** denominator = all AI cancellations. Measures overall reduction in cancellations from baseline.

### Governance Impact Layer

| KPI                    | Formula                                                    |
|------------------------|------------------------------------------------------------|
| Revenue Prevented      | SUM(revenue_prevented_by_navedas)                          |
| Margin Saved           | SUM(margin_saved_after_navedas)                            |
| Intervention Cost      | SUM(intervention_cost)                                     |
| Net Profit Impact      | SUM(net_profit_impact_due_to_navedas)                      |
| Governance ROI         | Margin Saved / Intervention Cost                           |
| Revenue Coverage       | Revenue Prevented / Revenue Lost (AI-Only) * 100           |

### Residual Risk Layer

| KPI                         | Formula                                                   |
|-----------------------------|-----------------------------------------------------------|
| Residual Revenue Loss       | SUM(avoidable_revenue_loss_after_navedas)                 |
| Residual Profit Loss        | SUM(profit_lost_after_navedas)                            |
| Legitimate Non-Recoverable  | Rows where ai_cancel_flag=1 AND recoverable_flag=0        |
| Breakdown by Failure Reason | GROUP BY intervention_failure_reason WHERE recoverable=1 AND success=0 |

---

## 5. ROI Formula Definition

```
Governance ROI = Total Margin Saved / Total Intervention Cost
```

- **Margin Saved** = sum of `margin_saved_after_navedas` across all successful interventions.
  This represents recovered gross margin (revenue x margin_percent) that would have been lost.
- **Intervention Cost** = sum of `intervention_cost` — the operational cost per intervention attempt.
- **ROI > 1.0** means every rupee spent on governance returned more than one rupee in margin.
- **ROI interpretation:** A value of 85x means Rs.1 of intervention cost recovered Rs.85 of margin.

---

## 6. Recovery Logic Explanation

The dashboard models a three-stage recovery pipeline:

```
Stage 1 — AI Decision:
  All orders evaluated by AI. ai_cancel_flag=1 means AI auto-cancelled.

Stage 2 — Logic Gap Classification:
  recoverable_flag=1 means the cancellation was a logic gap — the order
  COULD have been fulfilled if reviewed. These are "AI errors."

Stage 3 — Navedas Intervention:
  For recoverable orders, Navedas attempts recovery (intervention_attempted=1).
  If successful (intervention_success=1), revenue is saved.
  If unsuccessful, avoidable_revenue_loss_after_navedas records the residual.

Residual losses are operationally constrained (e.g., vendor unavailability,
payment window expired) — NOT a failure of governance logic.
```

---

## 7. Financial Modeling Assumptions

1. `revenue_lost_before_ai_only` = total_order_value for cancelled orders (pre-intervention baseline).
2. `margin_saved_after_navedas` = revenue_prevented * margin_percent (implicit in data).
3. `net_profit_impact_due_to_navedas` = margin_saved - intervention_cost (pre-computed in dataset).
4. `intervention_cost` is a flat per-order cost for governance review actions.
5. Legitimate non-recoverable cancellations (recoverable_flag=0) are treated as unavoidable business losses — governance cannot and should not override these.
6. All currency values are in Indian Rupees (INR). Displays use lakhs (L) and crores (Cr) notation.

---

## 8. Visual Design Reasoning

### Color System
| Color  | Hex       | Usage                                    |
|--------|-----------|------------------------------------------|
| Blue   | #2563eb   | AI baseline metrics, neutral information |
| Green  | #16a34a   | Recovery, savings, positive outcomes     |
| Amber  | #d97706   | Caution, residual risk, partial recovery |
| Red    | #dc2626   | Loss, cancellations, negative outcomes   |
| Purple | #7c3aed   | Governance/intervention actions          |

### Layout Principles
- **Light neutral background (#f5f6fa):** Board-ready, print-safe, professional.
- **White cards with subtle shadow:** Clear visual hierarchy, premium SaaS feel.
- **Color-coded top border on KPI cards:** Instant category recognition.
- **Large typography for KPI values:** Legible from across a conference room.
- **Progressive disclosure:** Story flow banner → KPI layers → charts → raw data.

### Chart Selection Rationale
| Chart             | Justification                                                      |
|-------------------|--------------------------------------------------------------------|
| Waterfall         | Shows revenue transformation from AI-only to post-governance state |
| Funnel            | Natural representation of the recovery pipeline stages             |
| Gauges            | Instant health check for key rates — familiar to C-suite           |
| Grouped bar       | Side-by-side comparison across categories (reason, demand level)   |
| Line chart        | Time-series trends across months                                   |
| Histogram         | Distribution of per-order net profit impact                        |
| Margin table      | Structured before/after comparison for financial review            |

---

## 9. Executive Narrative Summary

> The AI auto-cancellation system flagged approximately **X%** of orders for cancellation.
> Of these, **Y%** were identified as recoverable logic gaps — cases where the AI decision
> was incorrect and the order could have been fulfilled.
>
> Navedas governance intervention recovered **Z%** of the recoverable pool,
> preventing **Rs.X Cr** in revenue loss and preserving **Rs.Y L** in gross margin.
>
> The total cost of intervention was **Rs.Z**, delivering a **Governance ROI of Nx** —
> meaning every rupee invested in governance oversight returned N rupees in margin.
>
> Remaining residual losses are operationally constrained (vendor delays, expired payment windows)
> and represent known operational risk, not a failure of the governance model.

---

## 10. Running the Dashboard

```bash
# Install dependencies (one time)
pip install -r requirements.txt

# Start the dashboard
cd C:\Users\sunit\governance-dashboard
streamlit run app.py --server.port 8504
```

Visit: **http://localhost:8504**

The CSV is auto-discovered from the parent directory (`../ecommerce_ production_dataset_5000_rows.csv`).

---

## 11. Deployment Options

### Streamlit Community Cloud (Free)
1. Push `governance-dashboard/` folder to a GitHub repository.
2. Go to https://share.streamlit.io
3. Select repo, branch = main, main file = `governance-dashboard/app.py`
4. Click Deploy. App is live at a public URL.

### Render / Railway / Heroku
- Add a `Procfile`: `web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- Push to GitHub, connect to Render/Railway, deploy as a web service.

---

## 12. Future Scalability Suggestions

| Enhancement                     | Description                                                      |
|---------------------------------|------------------------------------------------------------------|
| Database backend                | Replace CSV with PostgreSQL/Snowflake for real-time data         |
| Date range filter               | Let users slice the dashboard by custom date ranges              |
| Category drill-down             | Click a reason/demand bar to filter all charts                   |
| Alert thresholds                | Flag when recovery rate drops below configurable threshold       |
| Export to PDF                   | One-click board-ready PDF export via pdfkit or reportlab         |
| API integration                 | Connect to order management system for live updates              |
| Multi-region view               | Split KPIs by geography if region column is available            |
| Predictive ROI model            | ML model to forecast intervention ROI based on order attributes  |
| User authentication             | Role-based access (executive view vs analyst drill-down)         |
| Automated weekly email report   | Scheduled summary email with key KPIs and trend alerts           |

---

## 13. Key Architecture Decisions

### Single entry point
`load_and_compute()` in `pipeline.py` is the ONLY function called from `app.py`.
All breakdown tables are computed there, cached by Streamlit's `@st.cache_data`.

### Safe division pattern
All percentage calculations use:
```python
g["recovery_rate"] = (
    g["recovered"] / g["recoverable"].replace(0, np.nan) * 100
).fillna(0)
```
This prevents ZeroDivisionError and NaN propagation.

### Plotly color compatibility
All Plotly color values use `rgba()` helper function — never 8-digit hex (#rrggbbaa)
which Plotly does not support.

### No matplotlib dependency
Color scales and formatting are handled with pure Python/CSS string operations.
`background_gradient()` (which requires matplotlib) is never used.

---

*Document version: 1.0 | Built for Navedas Executive Review | Confidential*
