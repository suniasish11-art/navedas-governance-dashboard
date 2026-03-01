"""
app.py -- Executive Governance Dashboard
Navedas Intervention ROI | Streamlit + Plotly
Run: streamlit run app.py --server.port 8504
"""
import os, sys
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from pipeline import load_and_compute

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Navedas | Executive Governance Dashboard",
    page_icon="dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design tokens ─────────────────────────────────────────────────────────────
BG      = "#f5f6fa"
CARD    = "#ffffff"
BORDER  = "#e2e8f0"
BLUE    = "#2563eb"
GREEN   = "#16a34a"
AMBER   = "#d97706"
RED     = "#dc2626"
PURPLE  = "#7c3aed"
TEXT    = "#0f172a"
SUB     = "#64748b"

CHART_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color=TEXT, size=12),
    margin=dict(l=10, r=10, t=44, b=10),
)

def rgba(hex_c: str, a: float) -> str:
    h = hex_c.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"

def fmt_inr(v):
    if v >= 1e7:  return f"Rs.{v/1e7:.2f}Cr"
    if v >= 1e5:  return f"Rs.{v/1e5:.1f}L"
    return f"Rs.{v:,.0f}"

def fmt_pct(v):   return f"{v:.1f}%"
def fmt_x(v):     return f"{v:.1f}x"
def fmt_n(v):     return f"{int(v):,}"

# ── CSS injection ─────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html,body,[class*="css"]{{font-family:'Inter',system-ui,sans-serif;background:{BG};color:{TEXT};}}
    .stApp{{background:{BG};}}
    .block-container{{padding:1.5rem 2.5rem 2rem 2.5rem;max-width:1600px;}}
    #MainMenu,footer,header{{visibility:hidden;}}
    .stDeployButton{{display:none;}}

    .hero{{background:linear-gradient(135deg,{BLUE} 0%,#1e40af 55%,{PURPLE} 100%);
           border-radius:16px;padding:2.5rem 3rem;margin-bottom:1.5rem;color:#fff;}}
    .hero-eyebrow{{font-size:.7rem;letter-spacing:.18em;text-transform:uppercase;
                   color:rgba(255,255,255,.65);margin-bottom:.5rem;}}
    .hero-title{{font-size:2rem;font-weight:800;margin:0 0 .4rem 0;}}
    .hero-sub{{font-size:.95rem;color:rgba(255,255,255,.8);margin:0;}}
    .hero-badges{{display:flex;gap:.6rem;margin-top:1.4rem;flex-wrap:wrap;}}
    .hero-badge{{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);
                 border-radius:100px;padding:.28rem .85rem;font-size:.76rem;font-weight:500;}}

    .sec-lbl{{font-size:.67rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;
              color:{SUB};margin:1.8rem 0 .9rem 0;display:flex;align-items:center;gap:.6rem;}}
    .sec-lbl::after{{content:'';flex:1;height:1px;background:{BORDER};}}

    .kcard{{background:{CARD};border:1px solid {BORDER};border-radius:12px;
            padding:1.2rem 1.4rem;box-shadow:0 1px 3px rgba(0,0,0,.06);
            position:relative;overflow:hidden;height:100%;}}
    .kcard::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:12px 12px 0 0;}}
    .kcard.blue::before  {{background:{BLUE};}}
    .kcard.green::before {{background:{GREEN};}}
    .kcard.amber::before {{background:{AMBER};}}
    .kcard.red::before   {{background:{RED};}}
    .kcard.purple::before{{background:{PURPLE};}}
    .kcard-lbl{{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;
                color:{SUB};margin-bottom:.45rem;}}
    .kcard-val{{font-size:1.85rem;font-weight:800;line-height:1;margin-bottom:.3rem;}}
    .kcard-val.blue  {{color:{BLUE};}}
    .kcard-val.green {{color:{GREEN};}}
    .kcard-val.amber {{color:{AMBER};}}
    .kcard-val.red   {{color:{RED};}}
    .kcard-val.purple{{color:{PURPLE};}}
    .kcard-sub{{font-size:.73rem;color:{SUB};}}

    .roi-card{{background:linear-gradient(135deg,{GREEN} 0%,#15803d 100%);
               border-radius:16px;padding:1.8rem;color:#fff;text-align:center;height:100%;
               display:flex;flex-direction:column;justify-content:center;}}
    .roi-lbl{{font-size:.72rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;
              color:rgba(255,255,255,.75);margin-bottom:.4rem;}}
    .roi-val{{font-size:3.2rem;font-weight:900;line-height:1;margin-bottom:.2rem;}}
    .roi-sub{{font-size:.82rem;color:rgba(255,255,255,.8);}}

    .story-wrap{{background:{CARD};border:1px solid {BORDER};border-radius:12px;
                 padding:1.4rem 1.5rem;display:flex;align-items:center;
                 gap:0;overflow-x:auto;margin-bottom:.25rem;}}
    .s-step{{display:flex;flex-direction:column;align-items:center;min-width:115px;
             text-align:center;flex:1;}}
    .s-icon{{font-size:1.5rem;margin-bottom:.35rem;}}
    .s-num{{font-size:1.1rem;font-weight:800;color:{BLUE};line-height:1;}}
    .s-lbl{{font-size:.65rem;color:{SUB};margin-top:.2rem;font-weight:500;}}
    .s-arr{{font-size:1.2rem;color:{BORDER};flex-shrink:0;padding:0 .15rem;}}

    .chart-card{{background:{CARD};border:1px solid {BORDER};border-radius:12px;
                 padding:1.2rem 1.4rem;box-shadow:0 1px 3px rgba(0,0,0,.06);}}
    .ct{{font-size:.8rem;font-weight:700;color:{TEXT};text-transform:uppercase;
         letter-spacing:.06em;margin-bottom:.2rem;}}
    .cs{{font-size:.7rem;color:{SUB};margin-bottom:.65rem;}}

    .insight{{background:#dbeafe;border-left:3px solid {BLUE};border-radius:0 8px 8px 0;
              padding:.7rem 1rem;font-size:.77rem;color:#1e40af;margin-top:.6rem;}}

    .footer{{text-align:center;color:{SUB};font-size:.7rem;
             padding:1.8rem 0 1rem 0;border-top:1px solid {BORDER};margin-top:2.5rem;}}
    </style>
    """, unsafe_allow_html=True)


# ── Data load ─────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_data():
    return load_and_compute()


# ── Chart builders ────────────────────────────────────────────────────────────

def gauge_fig(value, title, max_val=100, suffix="%", g_thresh=70, a_thresh=40):
    color = GREEN if value >= g_thresh else (AMBER if value >= a_thresh else RED)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix, "font": {"size": 26, "color": TEXT, "family": "Inter"}},
        title={"text": title, "font": {"size": 10, "color": SUB, "family": "Inter"}},
        gauge={
            "axis": {"range": [0, max_val], "tickcolor": BORDER, "tickfont": {"size": 9}},
            "bar": {"color": color, "thickness": 0.55},
            "bgcolor": BG,
            "bordercolor": BORDER,
            "borderwidth": 1,
            "steps": [
                {"range": [0, max_val * a_thresh / 100], "color": rgba(RED, 0.07)},
                {"range": [max_val * a_thresh / 100, max_val * g_thresh / 100], "color": rgba(AMBER, 0.07)},
                {"range": [max_val * g_thresh / 100, max_val], "color": rgba(GREEN, 0.07)},
            ],
        },
    ))
    fig.update_layout(**CHART_BASE, height=195)
    return fig


def waterfall_fig(kpis):
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["AI-Only Loss", "Navedas Recovery", "Net Residual"],
        y=[kpis["rev_lost_before"], -kpis["rev_prevented"], 0],
        text=[fmt_inr(kpis["rev_lost_before"]),
              "-" + fmt_inr(kpis["rev_prevented"]),
              fmt_inr(kpis["residual_rev_loss"])],
        textposition="outside",
        textfont=dict(size=13, color=TEXT, family="Inter"),
        decreasing={"marker": {"color": GREEN}},
        increasing={"marker": {"color": RED}},
        totals={"marker": {"color": AMBER}},
        connector={"line": {"color": BORDER, "dash": "dot", "width": 1}},
    ))
    y_max = kpis["rev_lost_before"] * 1.22
    fig.update_layout(
        **CHART_BASE, height=340, showlegend=False,
        yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=True,
                   zerolinecolor=BORDER, range=[0, y_max]),
        xaxis=dict(showgrid=False, tickfont=dict(size=12)),
    )
    fig.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    return fig


def funnel_fig(kpis):
    residual_count = kpis["recoverable"] - kpis["recovered"]
    fig = go.Figure(go.Funnel(
        y=["AI Cancellations", "Recoverable Orders", "Successfully Recovered", "Residual"],
        x=[kpis["ai_cancelled"], kpis["recoverable"], kpis["recovered"], residual_count],
        textinfo="value+percent initial",
        marker={"color": [BLUE, PURPLE, GREEN, AMBER]},
        connector={"fillcolor": BG},
        textfont={"family": "Inter", "size": 14, "color": "#ffffff"},
    ))
    fig.update_layout(**CHART_BASE, height=340, showlegend=False)
    return fig


def trend_fig(trend_df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend_df["month"], y=trend_df["cancel_rate"],
        name="AI Cancel Rate %", mode="lines+markers",
        line=dict(color=RED, width=2.5), marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=trend_df["month"], y=trend_df["recovery_rate"],
        name="Recovery Rate %", mode="lines+markers",
        line=dict(color=GREEN, width=2.5), marker=dict(size=5),
    ))
    fig.update_layout(
        **CHART_BASE, height=270,
        legend=dict(orientation="h", y=1.15, x=0, font=dict(size=10)),
        yaxis=dict(title="Rate (%)", showgrid=True, gridcolor=BORDER),
        xaxis=dict(showgrid=False, tickangle=-30),
    )
    return fig


def reason_fig(reason_df):
    y_max = max(reason_df["rev_prevented"].max(), reason_df["margin_saved"].max()) * 1.28
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=reason_df["cancellation_reason"], y=reason_df["rev_prevented"],
        name="Revenue Recovered", marker_color=GREEN,
        text=reason_df["rev_prevented"].map(fmt_inr), textposition="outside",
        textfont=dict(size=12, color=TEXT), cliponaxis=False,
    ))
    fig.add_trace(go.Bar(
        x=reason_df["cancellation_reason"], y=reason_df["margin_saved"],
        name="Margin Saved", marker_color=BLUE,
        text=reason_df["margin_saved"].map(fmt_inr), textposition="outside",
        textfont=dict(size=12, color=TEXT), cliponaxis=False,
    ))
    fig.update_layout(
        **CHART_BASE, height=330, barmode="group",
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor=BORDER, range=[0, y_max]),
        xaxis=dict(showgrid=False, tickangle=-15, tickfont=dict(size=11)),
    )
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    return fig


def residual_fig(resid_df):
    if resid_df.empty:
        return None
    y_max = resid_df["rev_loss"].max() * 1.28
    fig = go.Figure(go.Bar(
        x=resid_df["reason"], y=resid_df["rev_loss"],
        marker_color=AMBER,
        text=resid_df["rev_loss"].map(fmt_inr), textposition="outside",
        textfont=dict(size=12, color=TEXT), cliponaxis=False,
    ))
    fig.update_layout(
        **CHART_BASE, height=310, showlegend=False,
        yaxis=dict(showgrid=True, gridcolor=BORDER, range=[0, y_max]),
        xaxis=dict(showgrid=False, tickangle=-15, tickfont=dict(size=11)),
    )
    fig.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    return fig


def demand_fig(demand_df):
    y_max = max(demand_df["rev_prevented"].max(), demand_df["net_profit"].max()) * 1.28
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=demand_df["demand_level"], y=demand_df["rev_prevented"],
        name="Revenue Prevented", marker_color=GREEN,
        text=demand_df["rev_prevented"].map(fmt_inr), textposition="outside",
        textfont=dict(size=12, color=TEXT), cliponaxis=False,
    ))
    fig.add_trace(go.Bar(
        x=demand_df["demand_level"], y=demand_df["net_profit"],
        name="Net Profit Impact", marker_color=PURPLE,
        text=demand_df["net_profit"].map(fmt_inr), textposition="outside",
        textfont=dict(size=12, color=TEXT), cliponaxis=False,
    ))
    fig.update_layout(
        **CHART_BASE, height=310, barmode="group",
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor=BORDER, range=[0, y_max]),
        xaxis=dict(showgrid=False, tickfont=dict(size=12)),
    )
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    return fig


def profit_hist_fig(df):
    net = df[df["net_profit_impact_due_to_navedas"] != 0]["net_profit_impact_due_to_navedas"]
    mean_val = net.mean()
    fig = go.Figure(go.Histogram(
        x=net, nbinsx=40,
        marker_color=BLUE,
        marker_line_color=CARD, marker_line_width=0.5,
    ))
    fig.add_vline(x=mean_val, line_dash="dash", line_color=GREEN,
                  annotation_text=f"Mean: {fmt_inr(mean_val)}",
                  annotation_font_size=12, annotation_font_color=GREEN)
    fig.update_layout(
        **CHART_BASE, height=250, showlegend=False,
        yaxis=dict(showgrid=True, gridcolor=BORDER),
        xaxis=dict(showgrid=False, title="Net Profit Impact per Order (Rs.)"),
    )
    return fig


# ── KPI card shortcut ─────────────────────────────────────────────────────────
def kcard(label, value, sub, color="blue"):
    st.markdown(f"""
    <div class="kcard {color}">
        <div class="kcard-lbl">{label}</div>
        <div class="kcard-val {color}">{value}</div>
        <div class="kcard-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    inject_css()

    with st.spinner("Loading dataset and computing KPIs..."):
        try:
            df, kpis, trend_df, reason_df, resid_df, demand_df = get_data()
        except FileNotFoundError as e:
            st.error(str(e))
            st.info("Tip: place the CSV file one folder above this app, or in your home directory.")
            st.stop()

    # ── Hero ─────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="hero">
        <div class="hero-eyebrow">Executive Governance Dashboard</div>
        <div class="hero-title">Navedas Intervention Impact Report</div>
        <div class="hero-sub">AI Logic Gap Recovery &nbsp;|&nbsp; Revenue Protection &nbsp;|&nbsp;
                              Margin Preservation &nbsp;|&nbsp; ROI Analysis</div>
        <div class="hero-badges">
            <span class="hero-badge">Orders Analyzed: {fmt_n(kpis['total_orders'])}</span>
            <span class="hero-badge">AI Cancel Rate: {fmt_pct(kpis['ai_cancel_rate'])}</span>
            <span class="hero-badge">Governance ROI: {fmt_x(kpis['gov_roi'])}</span>
            <span class="hero-badge">Recovery Rate: {fmt_pct(kpis['recovery_rate_pool'])}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Story flow ────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">Executive Narrative</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="story-wrap">
        <div class="s-step">
            <div class="s-icon">AI</div>
            <div class="s-num">{fmt_pct(kpis['ai_cancel_rate'])}</div>
            <div class="s-lbl">AI auto-cancelled</div>
        </div>
        <div class="s-arr">-&gt;</div>
        <div class="s-step">
            <div class="s-icon">Gap</div>
            <div class="s-num">{fmt_pct(kpis['pct_recoverable'])}</div>
            <div class="s-lbl">Logic gaps (recoverable)</div>
        </div>
        <div class="s-arr">-&gt;</div>
        <div class="s-step">
            <div class="s-icon">Fix</div>
            <div class="s-num">{fmt_pct(kpis['recovery_rate_pool'])}</div>
            <div class="s-lbl">Navedas recovery rate</div>
        </div>
        <div class="s-arr">-&gt;</div>
        <div class="s-step">
            <div class="s-icon">Rev</div>
            <div class="s-num">{fmt_inr(kpis['rev_prevented'])}</div>
            <div class="s-lbl">Revenue prevented loss</div>
        </div>
        <div class="s-arr">-&gt;</div>
        <div class="s-step">
            <div class="s-icon">Mgn</div>
            <div class="s-num">{fmt_inr(kpis['margin_saved'])}</div>
            <div class="s-lbl">Margin preserved</div>
        </div>
        <div class="s-arr">-&gt;</div>
        <div class="s-step">
            <div class="s-icon">ROI</div>
            <div class="s-num">{fmt_x(kpis['gov_roi'])}</div>
            <div class="s-lbl">ROI delivered</div>
        </div>
        <div class="s-arr">-&gt;</div>
        <div class="s-step">
            <div class="s-icon">Res</div>
            <div class="s-num">{fmt_inr(kpis['residual_rev_loss'])}</div>
            <div class="s-lbl">Residual (ops constrained)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── AI Performance ────────────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">AI Performance Layer</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: kcard("Total Orders", fmt_n(kpis["total_orders"]), "All orders in dataset", "blue")
    with c2: kcard("AI Cancel Rate", fmt_pct(kpis["ai_cancel_rate"]),
                   f"{fmt_n(kpis['ai_cancelled'])} orders auto-cancelled", "red")
    with c3: kcard("Revenue Lost (AI-Only)", fmt_inr(kpis["rev_lost_before"]),
                   "Before any governance intervention", "red")
    with c4: kcard("Profit Lost (AI-Only)", fmt_inr(kpis["profit_lost_before"]),
                   "Gross margin impact before Navedas", "red")

    # ── Recoverability ────────────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">Recoverability Layer</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: kcard("Recoverable Orders", fmt_n(kpis["recoverable"]),
                   f"{fmt_pct(kpis['pct_recoverable'])} of AI cancellations", "amber")
    with c2: kcard("% Recoverable of Cancelled", fmt_pct(kpis["pct_recoverable"]),
                   "Logic gap ratio in AI decisions", "amber")
    with c3: kcard("Recovery Rate (Pool Basis)", fmt_pct(kpis["recovery_rate_pool"]),
                   f"{fmt_n(kpis['recovered'])} of {fmt_n(kpis['recoverable'])} recoverable", "green")
    with c4: kcard("Net Cancellation Reduction", fmt_pct(kpis["net_cancel_reduction"]),
                   "Recovered / Total AI Cancelled", "green")

    # ── Governance Impact ─────────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">Governance Impact Layer -- Navedas</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: kcard("Revenue Prevented", fmt_inr(kpis["rev_prevented"]),
                   "Revenue rescued by Navedas", "green")
    with c2: kcard("Margin Saved", fmt_inr(kpis["margin_saved"]),
                   "Gross margin preserved post-intervention", "green")
    with c3: kcard("Intervention Cost", fmt_inr(kpis["intervention_cost"]),
                   "Total cost of governance intervention", "purple")
    with c4: kcard("Net Profit Impact", fmt_inr(kpis["net_profit_impact"]),
                   "Success gains minus failed-attempt losses & cost", "purple")
    with c5:
        st.markdown(f"""
        <div class="roi-card">
            <div class="roi-lbl">Governance ROI</div>
            <div class="roi-val">{fmt_x(kpis['gov_roi'])}</div>
            <div class="roi-sub">Margin Saved / Intervention Cost</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Governance KPI Reconciliation note ────────────────────────────────────
    failed_count = kpis["recoverable"] - kpis["recovered"]
    success_net  = kpis["margin_saved"] - (kpis["intervention_cost"] * kpis["recovered"] / kpis["recoverable"] if kpis["recoverable"] else 0)
    st.markdown(f"""
    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
                padding:.85rem 1.2rem;font-size:.77rem;color:#166534;margin-top:.5rem;">
        <strong>KPI Reconciliation:</strong> &nbsp;
        Margin Saved (<strong>{fmt_inr(kpis['margin_saved'])}</strong>) minus Intervention Cost
        (<strong>{fmt_inr(kpis['intervention_cost'])}</strong>) = <strong>{fmt_inr(kpis['margin_saved'] - kpis['intervention_cost'])}</strong>.
        &nbsp; Net Profit Impact is lower at <strong>{fmt_inr(kpis['net_profit_impact'])}</strong> because
        the dataset also deducts the profit lost on <strong>{failed_count:,} failed intervention attempts</strong>
        (Rs.{(kpis['margin_saved'] - kpis['intervention_cost'] - kpis['net_profit_impact'])/1e5:.1f}L in failed-case losses).
        &nbsp; Governance ROI = Margin Saved / Total Intervention Cost = <strong>{fmt_x(kpis['gov_roi'])}</strong> (per spec).
    </div>
    """, unsafe_allow_html=True)

    # ── Residual Risk ─────────────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">Residual Risk Layer</div>', unsafe_allow_html=True)
    coverage = (kpis["rev_prevented"] / kpis["rev_lost_before"] * 100) if kpis["rev_lost_before"] else 0
    c1, c2, c3, c4 = st.columns(4)
    with c1: kcard("Residual Revenue Loss", fmt_inr(kpis["residual_rev_loss"]),
                   "Recoverable cases not yet resolved", "amber")
    with c2: kcard("Residual Profit Loss", fmt_inr(kpis["residual_prof_loss"]),
                   "Margin impact of unresolved recoverable", "amber")
    with c3: kcard("Legitimate Non-Recoverable", fmt_n(kpis["legit_non_recover_count"]),
                   f"Revenue: {fmt_inr(kpis['legit_rev_loss'])}", "red")
    with c4: kcard("Governance Coverage", fmt_pct(coverage),
                   "Revenue rescued / total AI-only loss", "blue")

    # ── Gauges ────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">Performance Gauges</div>', unsafe_allow_html=True)
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(gauge_fig(kpis["recovery_rate_pool"], "Recovery Rate (Pool)"),
                        width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)
    with g2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(gauge_fig(kpis["pct_recoverable"], "Logic Gap Rate",
                                  g_thresh=60, a_thresh=30),
                        width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)
    with g3:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(gauge_fig(coverage, "Revenue Coverage"),
                        width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)
    with g4:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        roi_score = min(kpis["gov_roi"] * 10, 100)
        st.plotly_chart(gauge_fig(roi_score, f"ROI Score ({fmt_x(kpis['gov_roi'])})",
                                  suffix="", g_thresh=70, a_thresh=40),
                        width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Waterfall + Funnel ────────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">Revenue Waterfall & Recovery Funnel</div>', unsafe_allow_html=True)
    wc, fc = st.columns([3, 2])
    with wc:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="ct">Revenue Waterfall -- AI-Only vs After Governance</div>', unsafe_allow_html=True)
        st.markdown('<div class="cs">How Navedas intervention converts revenue loss into recovery</div>', unsafe_allow_html=True)
        st.plotly_chart(waterfall_fig(kpis), width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)
    with fc:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="ct">Recovery Funnel</div>', unsafe_allow_html=True)
        st.markdown('<div class="cs">Cancelled -- Recoverable -- Recovered -- Residual</div>', unsafe_allow_html=True)
        st.plotly_chart(funnel_fig(kpis), width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Trend ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">Trend Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="ct">Cancellation & Recovery Rate Over Time (Monthly)</div>', unsafe_allow_html=True)
    st.markdown('<div class="cs">AI cancel rate vs Navedas recovery rate by month</div>', unsafe_allow_html=True)
    st.plotly_chart(trend_fig(trend_df), width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Recovery by Reason + Demand ───────────────────────────────────────────
    st.markdown('<div class="sec-lbl">Recovery Performance & Demand Level Analysis</div>', unsafe_allow_html=True)
    rc, dc = st.columns(2)
    with rc:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="ct">Recovery Performance by Cancellation Reason</div>', unsafe_allow_html=True)
        st.markdown('<div class="cs">Revenue recovered and margin saved per cancellation type</div>', unsafe_allow_html=True)
        st.plotly_chart(reason_fig(reason_df), width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)
    with dc:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="ct">Demand Level Impact</div>', unsafe_allow_html=True)
        st.markdown('<div class="cs">Revenue prevented and net profit by demand segment</div>', unsafe_allow_html=True)
        st.plotly_chart(demand_fig(demand_df), width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Residual Breakdown + Profit Distribution ──────────────────────────────
    st.markdown('<div class="sec-lbl">Residual Loss & Profit Distribution</div>', unsafe_allow_html=True)
    r2, p2 = st.columns(2)
    with r2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="ct">Residual Loss by Intervention Failure Reason</div>', unsafe_allow_html=True)
        st.markdown('<div class="cs">Operationally constrained -- not a governance failure</div>', unsafe_allow_html=True)
        fig_r = residual_fig(resid_df)
        if fig_r:
            st.plotly_chart(fig_r, width="stretch")
        else:
            st.success("No residual intervention failures recorded.")
        st.markdown('</div>', unsafe_allow_html=True)
    with p2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="ct">Net Profit Impact Distribution</div>', unsafe_allow_html=True)
        st.markdown('<div class="cs">Order-level net profit impact from Navedas interventions</div>', unsafe_allow_html=True)
        st.plotly_chart(profit_hist_fig(df), width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Margin Comparison Table ───────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">Margin Comparison -- Before vs After Governance</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    margin_table = pd.DataFrame({
        "Metric": ["Revenue Lost", "Profit Lost", "Margin Saved", "Net Profit Impact", "Intervention Cost"],
        "AI-Only (Before Navedas)": [
            fmt_inr(kpis["rev_lost_before"]),
            fmt_inr(kpis["profit_lost_before"]),
            "Rs.0",
            "-" + fmt_inr(kpis["profit_lost_before"]),
            "Rs.0",
        ],
        "After Navedas Intervention": [
            fmt_inr(kpis["residual_rev_loss"] + kpis["legit_rev_loss"]),
            fmt_inr(kpis["residual_prof_loss"]),
            fmt_inr(kpis["margin_saved"]),
            fmt_inr(kpis["net_profit_impact"]),
            fmt_inr(kpis["intervention_cost"]),
        ],
        "Improvement": [
            "-" + fmt_inr(kpis["rev_prevented"]),
            "-" + fmt_inr(kpis["profit_lost_before"] - kpis["residual_prof_loss"]),
            "+" + fmt_inr(kpis["margin_saved"]),
            "+" + fmt_inr(kpis["net_profit_impact"] + kpis["profit_lost_before"]),
            "—",
        ],
    })
    st.dataframe(margin_table, width="stretch", hide_index=True)
    st.markdown(f"""
    <div class="insight">
        Navedas governance intervention recovered <strong>{fmt_inr(kpis['rev_prevented'])}</strong> in revenue,
        saved <strong>{fmt_inr(kpis['margin_saved'])}</strong> in margin, and delivered a
        <strong>{fmt_x(kpis['gov_roi'])} ROI</strong> on a total intervention cost of
        <strong>{fmt_inr(kpis['intervention_cost'])}</strong>.
        Residual losses are operationally constrained, not a governance failure.
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Raw Data Explorer ─────────────────────────────────────────────────────
    with st.expander("Raw Data Explorer", expanded=False):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            demand_filter = st.selectbox(
                "Demand Level", ["All"] + sorted(df["demand_level"].dropna().unique().tolist()),
                label_visibility="visible",
            )
        with col_f2:
            cancel_filter = st.selectbox("AI Cancelled", ["All", "Yes", "No"],
                                         label_visibility="visible")
        with col_f3:
            success_filter = st.selectbox("Intervention Success", ["All", "Yes", "No"],
                                          label_visibility="visible")

        filtered = df.copy()
        if demand_filter != "All":
            filtered = filtered[filtered["demand_level"] == demand_filter]
        if cancel_filter == "Yes":
            filtered = filtered[filtered["ai_cancel_flag"] == 1]
        elif cancel_filter == "No":
            filtered = filtered[filtered["ai_cancel_flag"] == 0]
        if success_filter == "Yes":
            filtered = filtered[filtered["intervention_success"] == 1]
        elif success_filter == "No":
            filtered = filtered[filtered["intervention_success"] == 0]

        st.caption(f"Showing {len(filtered):,} of {len(df):,} rows")
        st.dataframe(filtered, width="stretch", height=340)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="footer">
        Navedas Executive Governance Dashboard &nbsp;|&nbsp;
        {fmt_n(kpis['total_orders'])} orders analyzed &nbsp;|&nbsp;
        Governance ROI: {fmt_x(kpis['gov_roi'])} &nbsp;|&nbsp;
        Built with Streamlit + Plotly
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
