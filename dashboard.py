import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="AI Help Desk Triage Dashboard",
    page_icon="🤖",
    layout="wide"
)

# ── Load data ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)   # refresh every 30 seconds
def load_data():
    log_file = Path("logs/triage_results.json")
    if not log_file.exists() or log_file.stat().st_size == 0:
        return pd.DataFrame()
    with open(log_file) as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df["processed_at"] = pd.to_datetime(df["processed_at"])
    return df

# ── Header ─────────────────────────────────────────────────────────────────
st.title("🤖 AI Help Desk Triage Dashboard")
st.caption(f"Powered by LLaMA 3 70B via Groq API · Last updated: {datetime.now().strftime('%H:%M:%S')}")
st.divider()

df = load_data()

if df.empty:
    st.info("No triage data yet. Run main.py to process tickets.")
    st.stop()

# ── KPI cards ──────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Tickets Triaged", len(df))
with col2:
    escalated = df["escalate"].sum() if "escalate" in df.columns else 0
    st.metric("Escalated", int(escalated), delta=f"{escalated/len(df)*100:.0f}% of total")
with col3:
    avg_conf = df["confidence"].mean() if "confidence" in df.columns else 0
    st.metric("Avg AI Confidence", f"{avg_conf*100:.1f}%")
with col4:
    critical = len(df[df["priority"] == "SEV-1"]) if "priority" in df.columns else 0
    st.metric("Critical (SEV-1)", critical)

st.divider()

# ── Charts ─────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.subheader("Priority Distribution")
    if "priority" in df.columns:
        priority_order = ["SEV-1","SEV-2","SEV-3","SEV-4","SEV-5"]
        priority_counts = df["priority"].value_counts().reindex(priority_order, fill_value=0)
        colors = ["#ef4444","#f97316","#eab308","#22c55e","#3b82f6"]
        fig = px.bar(x=priority_counts.index, y=priority_counts.values,
                     color=priority_counts.index,
                     color_discrete_sequence=colors,
                     labels={"x": "Priority", "y": "Tickets"})
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Department Routing")
    if "department" in df.columns:
        dept_counts = df["department"].value_counts()
        fig2 = px.pie(values=dept_counts.values, names=dept_counts.index,
                      color_discrete_sequence=px.colors.sequential.Blues_r)
        fig2.update_layout(height=300)
        st.plotly_chart(fig2, use_container_width=True)

# ── Ticket feed ────────────────────────────────────────────────────────────
st.subheader("Live Ticket Feed")
display_cols = [c for c in
    ["ticket_id","subject","user_name","priority","department",
     "confidence","escalate","estimated_resolution","processed_at"]
    if c in df.columns]
st.dataframe(
    df[display_cols].sort_values("processed_at", ascending=False),
    use_container_width=True, height=400
)

# ── Auto-refresh ───────────────────────────────────────────────────────────
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()
