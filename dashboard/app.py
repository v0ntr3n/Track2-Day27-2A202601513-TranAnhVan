from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "latest_metrics.json"
HISTORY = ROOT / "data" / "history" / "metrics_history.csv"

st.set_page_config(page_title="Data Reliability Command Center", layout="wide")
st.title("🛡️ Data Reliability Command Center")
st.caption("Data Observability, Contract Enforcement, Anomaly Detection & SRE SLO Monitoring")

if not REPORT.exists():
    st.warning("Run `make baseline` first to generate reports/latest_metrics.json")
    st.stop()

report = json.loads(REPORT.read_text(encoding="utf-8"))
slo = report.get("contract_slo", {})

# Top KPIs
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Orders Ingested", report.get("orders_rows", 0))
c2.metric("Freshness", f"{report.get('freshness_minutes', 0.0):.1f} min")
c3.metric("Contract Failures", report.get("failed_contract_checks", 0))
c4.metric("Critical Blockers", report.get("critical_contract_failures", 0))
budget_pct = slo.get("remaining_error_budget_fraction", 1.0) * 100.0
c5.metric("SLO Budget Left", f"{budget_pct:.1f}%", delta=f"{slo.get('burn_rate', 0.0):.1f}x burn", delta_color="inverse")

# Action / Triage Status Banner
crit_fails = report.get("critical_contract_failures", 0)
anom = report.get("row_count_anomaly", {}).get("is_anomaly", False)
slo_breach = slo.get("breached", False)

if crit_fails > 0 or slo_breach:
    st.error("🚨 **INCIDENT STATUS: ACTIVE CRITICAL BREACH** — Pipeline Blocked / On-call Paged")
elif anom:
    st.warning("⚠️ **INCIDENT STATUS: ANOMALY INVESTIGATION** — Metric shift detected, inspect blast radius")
else:
    st.success("✅ **SYSTEM STATUS: HEALTHY** — All contracts, anomalies, and SLOs within budget")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Anomaly & Observability Signals")
    st.json({
        "row_count_anomaly": report.get("row_count_anomaly"),
        "kb_contract_issues": report.get("kb_failed_contract_checks", 0),
        "kb_text_length_signal": report.get("kb_text_length_signal"),
        "contract_slo": slo,
    })

with col_right:
    st.subheader("🎯 Blast Radius Graph")
    blast_radius = report.get("sample_blast_radius_from_stg_orders", [])
    st.write("Source: `stg_orders`")
    for idx, node in enumerate(blast_radius, start=1):
        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{'↳' if idx == len(blast_radius) else '├─'} **Downstream Asset**: `{node}`")

st.divider()
history = pd.read_csv(HISTORY)
st.subheader("📈 Historical Metric Trends")
tab1, tab2 = st.tabs(["Row Count (Seasonality)", "KB Text Length"])
with tab1:
    st.line_chart(history.set_index("date")[["row_count"]])
with tab2:
    st.line_chart(history.set_index("date")[["mean_text_length"]])

