"""CareerLens Streamlit Dashboard.

A premium dark-themed, multi-section analytics dashboard that consumes the
CareerLens FastAPI to visualise global job market trends.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path to allow importing 'src'
root_path = Path(__file__).resolve().parents[3]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

from src.config import settings

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="CareerLens — Global Job Trends",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — dark premium look
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ---- Global ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ---- Background ---- */
    .stApp { background: #0e1117; }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-right: 1px solid #21262d;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color: #e6edf3; }

    /* ---- KPI Cards ---- */
    .kpi-card {
        background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 32px rgba(88,166,255,0.15);
    }
    .kpi-number {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #58a6ff, #a5d6ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.1;
    }
    .kpi-label {
        font-size: 0.78rem;
        font-weight: 500;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 6px;
    }

    /* ---- Section headers ---- */
    .section-header {
        font-size: 1.05rem;
        font-weight: 600;
        color: #58a6ff;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 4px;
        border-left: 3px solid #58a6ff;
        padding-left: 10px;
    }

    /* ---- Chart containers ---- */
    .chart-card {
        background: #161b22;
        border: 1px solid #21262d;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.3);
    }

    /* ---- Tables ---- */
    .dataframe { border-radius: 8px; overflow: hidden; }

    /* ---- Divider ---- */
    hr { border-color: #21262d; margin: 32px 0; }

    /* ---- Status pills ---- */
    .pill-ok {
        display: inline-block;
        background: #1a4731;
        color: #3fb950;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .pill-warn {
        display: inline-block;
        background: #3d2b00;
        color: #f0883e;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* ---- Last updated timestamp ---- */
    .last-updated {
        font-size: 0.72rem;
        color: #3fb950;
        background: #1a4731;
        border-radius: 8px;
        padding: 4px 10px;
        display: inline-block;
        margin-top: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Plotly theme
# ---------------------------------------------------------------------------
_PLOTLY_THEME = "plotly_dark"
_BRAND_COLORS = px.colors.sequential.Blues_r
_ACCENT = "#58a6ff"

_CHART_LAYOUT = dict(
    paper_bgcolor="#161b22",
    plot_bgcolor="#161b22",
    font=dict(family="Inter, sans-serif", size=12, color="#c9d1d9"),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#30363d", borderwidth=1),
)


# ---------------------------------------------------------------------------
# Data fetching — cache TTL reduced to 60s for near-real-time freshness
# ---------------------------------------------------------------------------
BASE = settings.api_base_url


@st.cache_data(ttl=60, show_spinner=False)
def _fetch(endpoint: str, params: dict | None = None) -> pd.DataFrame:
    """Fetch JSON data from the CareerLens API and return as a DataFrame."""
    r = requests.get(f"{BASE}{endpoint}", params=params or {}, timeout=15)
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data) if data else pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_stats() -> dict:
    r = requests.get(f"{BASE}/api/v1/stats", timeout=15)
    r.raise_for_status()
    return r.json()


def _safe_fetch(endpoint: str, params: dict | None = None) -> pd.DataFrame:
    """Safely fetch data from the API and handle exceptions by returning an empty DataFrame."""
    try:
        # Request up to 500 records to capture full historical trends
        if params is None:
            params = {}
        if "limit" not in params and "trends" in endpoint:
            params["limit"] = 500
        return _fetch(endpoint, params)
    except Exception as exc:
        st.warning(f"⚠️ Could not load data from {endpoint}: {exc}")
        return pd.DataFrame()


def get_mock_email_html(name: str, skills: list[str], jobs_df: pd.DataFrame) -> str:
    # Build list of jobs matching skills
    import re
    matched_jobs = []
    if jobs_df.empty:
        pass
    elif not skills:
        # Show some recent jobs as demo
        matched_jobs = jobs_df.head(5).to_dict("records")
    else:
        sub_skills = {s.strip().lower() for s in skills if s.strip()}
        for _, row in jobs_df.iterrows():
            job_tags = {t.lower() for t in (row.get("tags") or [])}
            title_words = set(re.findall(r"\b[a-zA-Z0-9+#\-\.]+\b", row["title"].lower()))
            job_terms = job_tags.union(title_words)
            if sub_skills.intersection(job_terms):
                matched_jobs.append(row)
                if len(matched_jobs) >= 5:
                    break

    # Compile HTML mockup
    skills_list_str = ", ".join(f"<code>{s}</code>" for s in skills) if skills else "All remote fields"
    
    job_cards_html = ""
    if not matched_jobs:
        job_cards_html = "<p style='color: #8b949e; text-align: center; padding: 20px;'>No matching jobs found in current cache. Add more general skills (e.g. Python, SQL) to preview.</p>"
    else:
        for job in matched_jobs:
            sal_min = job.get("salary_min")
            sal_max = job.get("salary_max")
            sal_curr = job.get("salary_currency") or "$"
            if pd.notna(sal_min) and pd.notna(sal_max):
                salary_str = f"{sal_curr}{int(sal_min):,} - {sal_curr}{int(sal_max):,}"
            else:
                salary_str = "Not specified"
                
            sen_badge = ""
            seniority = job.get("seniority")
            if seniority and seniority != "Unspecified":
                sen_badge = f'<span class="badge badge-sen">{seniority}</span>'
                
            src_badge = f'<span class="badge badge-src">{job["source"].upper()}</span>'
            location = job.get("country") or "Remote"
            
            job_cards_html += f"""
            <div class="job-card">
                <div class="job-title-row">
                    <a href="{job['url']}" class="job-title" target="_blank">{job['title']}</a>
                    <div>
                        {sen_badge}
                        {src_badge}
                    </div>
                </div>
                <div class="job-company">{job['company_name']}</div>
                <div class="job-meta">
                    <span>📍 {location}</span> &bull; 
                    <span>💰 {salary_str}</span>
                </div>
            </div>
            """
            
    html = f"""
    <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; overflow: hidden; font-family: sans-serif; color: #c9d1d9; max-width: 500px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #1f2937 0%, #111827 100%); padding: 16px; text-align: center; border-bottom: 1px solid #30363d;">
            <h2 style="color: #58a6ff; margin: 0; font-size: 18px;">CareerLens Job Alerts</h2>
            <p style="color: #8b949e; margin: 4px 0 0 0; font-size: 11px;">Global Remote Job Intelligence Digest</p>
        </div>
        <div style="padding: 16px;">
            <p style="font-size: 13px; margin-bottom: 12px;">Hello <strong>{name or 'Subscriber'}</strong>,</p>
            <p style="font-size: 12px; color: #8b949e; margin-bottom: 16px;">Here is your custom daily remote job digest for: {skills_list_str}. We found <strong>{len(matched_jobs)}</strong> new matches since your last update.</p>
            
            {job_cards_html}
        </div>
        <div style="background-color: #0d1117; padding: 12px; text-align: center; border-top: 1px solid #21262d; font-size: 10px; color: #8b949e;">
            This email was sent by CareerLens.<br>
            <span style="color: #f0883e; text-decoration: none;">Unsubscribe from job alerts</span>
        </div>
    </div>
    <style>
        .job-card {{
            background-color: #0d1117;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            text-align: left;
        }}
        .job-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .job-title {{
            color: #58a6ff;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
        }}
        .job-company {{
            color: #e6edf3;
            font-size: 11px;
            margin-top: 2px;
        }}
        .job-meta {{
            font-size: 10px;
            color: #8b949e;
            margin-top: 6px;
        }}
        .badge {{
            display: inline-block;
            font-size: 8px;
            font-weight: 600;
            padding: 1px 5px;
            border-radius: 8px;
            margin-left: 4px;
            text-transform: uppercase;
        }}
        .badge-sen {{
            background-color: #382402;
            color: #f0883e;
        }}
        .badge-src {{
            background-color: #162c46;
            color: #58a6ff;
        }}
    </style>
    """
    return html


def to_excel_data(df: pd.DataFrame) -> bytes:
    """Convert a pandas DataFrame to an Excel file in-memory."""
    import io
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Jobs Data")
    return output.getvalue()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🌐 CareerLens")
    st.markdown("*Global Job Market Intelligence*")
    st.divider()

    st.markdown("### 🔧 Filters")
    top_n = st.slider("Top N results", min_value=5, max_value=50, value=15, step=5)
    seniority_filter = st.selectbox("Seniority Level", ["All", "Junior", "Mid-level", "Senior", "Lead"])
    min_salary_filter = st.number_input("Min Salary (USD)", min_value=0, value=0, step=10000)
    st.divider()

    st.markdown("### 📑 Navigation")
    page = st.radio(
        "View",
        options=[
            "📊 Overview",
            "🌍 Countries",
            "🛠️ Skills",
            "💼 Roles",
            "📈 Time Trends",
            "💸 Salary Analysis",
            "🧠 Resume Matcher",
            "📧 Email Alerts",
            "🗂️ Browse Jobs",
            "🔖 Bookmarks",
        ],
        label_visibility="collapsed",
    )
    st.divider()

    auto_refresh = st.toggle("Auto-refresh (60 s)", value=False)
    if auto_refresh:
        st.caption("⟳ Page will refresh every 60 s")

    # Last updated timestamp — shown regardless of auto-refresh toggle
    _now_str = datetime.now().strftime("%H:%M:%S")
    st.markdown(
        f"<div class='last-updated'>🕒 Last updated: {_now_str}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<br><div style='color:#8b949e;font-size:0.7rem;text-align:center'>"
        "Powered by Remotive API · Built with FastAPI + Streamlit"
        "</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Fetch stats upfront (lightweight, always needed for KPIs and source list)
# Other data is fetched lazily per page to avoid slow navigation.
# ---------------------------------------------------------------------------
try:
    stats = _fetch_stats()
except requests.RequestException as exc:
    st.error(f"❌ Cannot reach the CareerLens API at **{BASE}**")
    st.code(str(exc))
    st.info("Make sure the API is running: `uvicorn src.serving.api.main:app --reload`")
    st.stop()

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _apply_layout(fig: go.Figure) -> go.Figure:
    fig.update_layout(**_CHART_LAYOUT)
    return fig


def _empty_chart(title: str) -> None:
    st.info(f"No data available for **{title}**. Run the pipeline to ingest some jobs.")


def _kpi(col, number: str | int, label: str) -> None:
    col.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-number">{number}</div>'
        f'<div class="kpi-label">{label}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# ══════════════════════════  PAGES  ══════════════════════════
# ---------------------------------------------------------------------------

# ---- Overview ----------------------------------------------------------------
if page == "📊 Overview":
    st.markdown("# 📊 CareerLens Overview")
    st.markdown(
        "Near-real-time snapshot of the global remote job market. "
        "Pipeline runs every 5 minutes; dashboard cache refreshes every 60 seconds."
    )
    st.divider()

    # Lazily fetch only the data required for Overview page
    countries_df = _safe_fetch("/api/v1/trends/countries")
    skills_df = _safe_fetch("/api/v1/trends/skills")

    # KPI row
    c1, c2, c3, c4, c5 = st.columns(5)
    _kpi(c1, f"{stats.get('total_jobs', 0):,}", "Total Jobs")
    _kpi(c2, f"{stats.get('total_countries', 0):,}", "Countries")
    _kpi(c3, f"{stats.get('total_skills', 0):,}", "Skills")
    _kpi(c4, stats.get("earliest_job", "—") or "—", "Earliest Job")
    _kpi(c5, stats.get("latest_job", "—") or "—", "Latest Job")

    st.markdown("<br>", unsafe_allow_html=True)

    # Pipeline health
    dead = stats.get("total_dead_letters", 0)
    sources = ", ".join(stats.get("sources", []))
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        pill = "pill-ok" if dead == 0 else "pill-warn"
        label = "Clean" if dead == 0 else f"{dead} unresolved"
        st.markdown(
            f"**Dead-letter queue:** <span class='{pill}'>{label}</span>",
            unsafe_allow_html=True,
        )
    with col_h2:
        st.markdown(f"**Active sources:** `{sources}`")

    st.divider()

    # Quick charts: top countries + top skills side by side
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section-header">Top Countries</div>', unsafe_allow_html=True)
        if not countries_df.empty:
            top_c = countries_df.groupby("country")["job_count"].sum().nlargest(top_n).reset_index()
            fig = px.bar(
                top_c,
                x="job_count",
                y="country",
                orientation="h",
                color="job_count",
                color_continuous_scale="Blues",
                template=_PLOTLY_THEME,
                labels={"job_count": "Jobs", "country": ""},
            )
            fig.update_coloraxes(showscale=False)
            fig.update_layout(**_CHART_LAYOUT, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            _empty_chart("Countries")

    with right:
        st.markdown('<div class="section-header">Top Skills</div>', unsafe_allow_html=True)
        if not skills_df.empty:
            top_s = skills_df.groupby("skill")["job_count"].sum().nlargest(top_n).reset_index()
            fig = px.bar(
                top_s,
                x="job_count",
                y="skill",
                orientation="h",
                color="job_count",
                color_continuous_scale="Teal",
                template=_PLOTLY_THEME,
                labels={"job_count": "Jobs", "skill": ""},
            )
            fig.update_coloraxes(showscale=False)
            fig.update_layout(**_CHART_LAYOUT, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            _empty_chart("Skills")

# ---- Countries ---------------------------------------------------------------
elif page == "🌍 Countries":
    st.markdown("# 🌍 Job Market by Country")
    st.divider()

    # Lazily fetch only the data required for Countries page
    countries_df = _safe_fetch("/api/v1/trends/countries")

    if countries_df.empty:
        _empty_chart("Countries")
    else:
        # Choropleth world map
        st.markdown(
            '<div class="section-header">Global Hiring Heatmap</div>', unsafe_allow_html=True
        )
        agg = countries_df.groupby("country")["job_count"].sum().reset_index()
        agg = agg[~agg["country"].isin(["Unknown", "Global"])]
        agg = agg.nlargest(top_n, "job_count")
        fig_map = px.choropleth(
            agg,
            locations="country",
            locationmode="country names",
            color="job_count",
            color_continuous_scale="Blues",
            template=_PLOTLY_THEME,
            labels={"job_count": "Total Jobs"},
            title=f"Top {len(agg)} Remote Jobs by Country",
        )
        fig_map.update_layout(**_CHART_LAYOUT, geo=dict(bgcolor="#161b22", showframe=False))
        st.plotly_chart(fig_map, use_container_width=True)

        st.divider()

        # Monthly breakdown
        st.markdown(
            '<div class="section-header">Monthly Trends — Top Countries</div>',
            unsafe_allow_html=True,
        )
        top_countries = (
            countries_df.groupby("country")["job_count"].sum().nlargest(top_n).index.tolist()
        )
        filtered = countries_df[countries_df["country"].isin(top_countries)]
        if not filtered.empty:
            fig = px.bar(
                filtered,
                x="published_month",
                y="job_count",
                color="country",
                barmode="stack",
                template=_PLOTLY_THEME,
                labels={"job_count": "Jobs", "published_month": "Month", "country": "Country"},
                color_discrete_sequence=px.colors.qualitative.Bold,
            )
            fig.update_layout(**_CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

        # Country ranking table
        st.markdown('<div class="section-header">Country Rankings</div>', unsafe_allow_html=True)
        ranking = (
            countries_df.groupby("country")["job_count"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        ranking.index = ranking.index + 1
        ranking.columns = ["Country", "Total Jobs"]
        st.dataframe(ranking.head(50), use_container_width=True)

# ---- Skills ------------------------------------------------------------------
elif page == "🛠️ Skills":
    st.markdown("# 🛠️ In-Demand Skills")
    st.divider()

    # Lazily fetch only the data required for Skills page
    skills_df = _safe_fetch("/api/v1/trends/skills")

    if skills_df.empty:
        _empty_chart("Skills")
    else:
        # Treemap
        st.markdown('<div class="section-header">Skills Treemap</div>', unsafe_allow_html=True)
        limit_skills = min(30, top_n)
        treemap_data = skills_df.groupby("skill")["job_count"].sum().nlargest(limit_skills).reset_index()
        fig_tree = px.treemap(
            treemap_data,
            path=["skill"],
            values="job_count",
            color="job_count",
            color_continuous_scale="Blues",
            template=_PLOTLY_THEME,
            title=f"Top {len(treemap_data)} Skills by Total Job Count",
        )
        fig_tree.update_layout(**_CHART_LAYOUT)
        st.plotly_chart(fig_tree, use_container_width=True)

        st.divider()

        # Monthly skill trends line chart
        st.markdown(
            '<div class="section-header">Skill Momentum Over Time</div>', unsafe_allow_html=True
        )
        top_skills = (
            skills_df.groupby("skill")["job_count"].sum().nlargest(min(8, top_n)).index.tolist()
        )
        skill_time = skills_df[skills_df["skill"].isin(top_skills)]
        if not skill_time.empty:
            fig = px.line(
                skill_time,
                x="published_month",
                y="job_count",
                color="skill",
                markers=True,
                template=_PLOTLY_THEME,
                labels={"job_count": "Jobs", "published_month": "Month"},
                color_discrete_sequence=px.colors.qualitative.Vivid,
            )
            fig.update_layout(**_CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

# ---- Roles -------------------------------------------------------------------
elif page == "💼 Roles":
    st.markdown("# 💼 Job Roles")
    st.divider()

    # Lazily fetch only the data required for Roles page
    roles_df = _safe_fetch("/api/v1/trends/roles")

    if roles_df.empty:
        _empty_chart("Roles")
    else:
        # Role ranking
        st.markdown(
            '<div class="section-header">Top Roles by Total Postings</div>', unsafe_allow_html=True
        )
        role_agg = roles_df.groupby("role")["job_count"].sum().nlargest(top_n).reset_index()
        fig = px.bar(
            role_agg,
            x="job_count",
            y="role",
            orientation="h",
            color="job_count",
            color_continuous_scale="Purples",
            template=_PLOTLY_THEME,
            labels={"job_count": "Total Jobs", "role": ""},
        )
        fig.update_coloraxes(showscale=False)
        fig.update_layout(**_CHART_LAYOUT, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Monthly heatmap
        st.markdown(
            '<div class="section-header">Monthly Role Demand Heatmap</div>', unsafe_allow_html=True
        )
        top_roles = (
            roles_df.groupby("role")["job_count"].sum().nlargest(min(15, top_n)).index.tolist()
        )
        pivot = (
            roles_df[roles_df["role"].isin(top_roles)]
            .pivot_table(index="role", columns="published_month", values="job_count", aggfunc="sum")
            .fillna(0)
        )
        if not pivot.empty:
            fig_hm = px.imshow(
                pivot,
                color_continuous_scale="Blues",
                template=_PLOTLY_THEME,
                labels={"x": "Month", "y": "Role", "color": "Jobs"},
                title=f"Top {len(pivot)} Roles × Month Job Count Heatmap",
            )
            fig_hm.update_layout(**_CHART_LAYOUT)
            st.plotly_chart(fig_hm, use_container_width=True)

# ---- Time Trends -------------------------------------------------------------
elif page == "📈 Time Trends":
    st.markdown("# 📈 Hiring Trends Over Time")
    st.divider()

    # Lazily fetch only the data required for Time Trends page
    time_df = _safe_fetch("/api/v1/trends/time")

    if time_df.empty:
        _empty_chart("Time Trends")
    else:
        # Area chart with trend line
        st.markdown(
            '<div class="section-header">Total Remote Jobs Published per Month</div>',
            unsafe_allow_html=True,
        )
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=time_df["published_month"],
                y=time_df["job_count"],
                mode="lines+markers+text",
                name="Jobs",
                line=dict(color=_ACCENT, width=2.5),
                marker=dict(size=8, color=_ACCENT, line=dict(width=2, color="#0d1117")),
                fill="tozeroy",
                fillcolor="rgba(88,166,255,0.08)",
                text=time_df["job_count"],
                textposition="top center",
                textfont=dict(size=10, color="#8b949e"),
            )
        )
        fig.update_layout(
            **_CHART_LAYOUT,
            xaxis_title="Month",
            yaxis_title="Job Count",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Stats
        total = int(time_df["job_count"].sum())
        peak_row = time_df.loc[time_df["job_count"].idxmax()]
        c1, c2, c3 = st.columns(3)
        _kpi(c1, f"{total:,}", "Total Jobs (all time)")
        _kpi(c2, str(peak_row["published_month"]), "Peak Month")
        _kpi(c3, f"{int(peak_row['job_count']):,}", "Peak Month Jobs")

# ---- Salary Analysis ---------------------------------------------------------
elif page == "💸 Salary Analysis":
    st.markdown("# 💸 Salary Intelligence")
    st.markdown("Dynamic salary aggregation and market intelligence parsed directly from our job trends database.")
    st.divider()

    # Fetch available currencies dynamically
    currencies = []
    try:
        r_curr = requests.get(f"{BASE}/api/v1/salary/currencies", timeout=15)
        if r_curr.status_code == 200:
            currencies = r_curr.json()
    except Exception as exc:
        st.warning(f"Could not load active currencies: {exc}")

    if not currencies:
        currencies = ["USD"]

    selected_currency = st.selectbox("Select Currency", options=currencies)

    # Fetch aggregated salary data
    salary_role_df = _safe_fetch("/api/v1/salary/by-role", {"currency": selected_currency, "limit": 20})
    salary_country_df = _safe_fetch("/api/v1/salary/by-country", {"currency": selected_currency, "limit": 20})

    if not salary_role_df.empty:
        # High-level KPIs
        c1, c2, c3 = st.columns(3)
        avg_sal_role = salary_role_df["avg_salary"].mean()
        highest_paying_role = salary_role_df.iloc[0]["role"]
        highest_paying_val = salary_role_df.iloc[0]["avg_salary"]
        total_sal_jobs = salary_role_df["job_count"].sum()

        _kpi(c1, f"{selected_currency} {int(avg_sal_role):,}", "Average Role Salary")
        _kpi(c2, f"{highest_paying_role}", f"Top Role ({selected_currency} {int(highest_paying_val):,})")
        _kpi(c3, f"{int(total_sal_jobs):,}", "Jobs Analysed")

        st.markdown("<br>", unsafe_allow_html=True)

        left_chart, right_chart = st.columns(2)
        
        with left_chart:
            st.markdown('<div class="section-header">Average Salary by Role</div>', unsafe_allow_html=True)
            fig_role = px.bar(
                salary_role_df.head(top_n),
                x="avg_salary",
                y="role",
                orientation="h",
                color="avg_salary",
                color_continuous_scale="Blues",
                template=_PLOTLY_THEME,
                labels={"avg_salary": "Average Salary", "role": ""},
            )
            fig_role.update_coloraxes(showscale=False)
            fig_role.update_layout(**_CHART_LAYOUT, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_role, use_container_width=True)

        with right_chart:
            st.markdown('<div class="section-header">Average Salary by Country</div>', unsafe_allow_html=True)
            if not salary_country_df.empty:
                fig_country = px.bar(
                    salary_country_df.head(top_n),
                    x="avg_salary",
                    y="country",
                    orientation="h",
                    color="avg_salary",
                    color_continuous_scale="Purples",
                    template=_PLOTLY_THEME,
                    labels={"avg_salary": "Average Salary", "country": ""},
                )
                fig_country.update_coloraxes(showscale=False)
                fig_country.update_layout(**_CHART_LAYOUT, yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig_country, use_container_width=True)
            else:
                _empty_chart("Country Salaries")

        st.divider()

        # Data Table
        st.subheader("📊 Detailed Salary Metrics")
        st.dataframe(
            salary_role_df[["role", "avg_salary", "min_salary", "max_salary", "job_count"]],
            column_config={
                "role": st.column_config.TextColumn("Job Title / Role"),
                "avg_salary": st.column_config.NumberColumn("Avg Salary", format=f"{selected_currency} %.0f"),
                "min_salary": st.column_config.NumberColumn("Min Salary", format=f"{selected_currency} %.0f"),
                "max_salary": st.column_config.NumberColumn("Max Salary", format=f"{selected_currency} %.0f"),
                "job_count": st.column_config.NumberColumn("Job Postings Count"),
            },
            use_container_width=True,
            hide_index=True,
        )

        # Export capabilities
        st.write("")
        exp_sal1, exp_sal2, _ = st.columns([1.2, 1.2, 4])
        with exp_sal1:
            csv_sal = salary_role_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Export Salaries (CSV)",
                data=csv_sal,
                file_name=f"careerlens_role_salaries_{selected_currency}.csv",
                mime="text/csv",
                key="download_salary_csv"
            )
        with exp_sal2:
            try:
                excel_sal = to_excel_data(salary_role_df)
                st.download_button(
                    label="📈 Export Salaries (Excel)",
                    data=excel_sal,
                    file_name=f"careerlens_role_salaries_{selected_currency}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_salary_excel"
                )
            except Exception as e:
                st.caption(f"Excel export disabled: {e}")
    else:
        st.info("No salary details found in the database. Run the pipeline with live source to import jobs with salary info.")

# ---- AI Resume Matcher ----------------------------------------------------
elif page == "🧠 Resume Matcher":
    st.markdown("# 🧠 AI-Powered Resume Matcher")
    st.markdown("Provide your resume or skills. Gemini AI will build a professional summary, extract key skills, suggest roles, and recommend the best-matching remote jobs.")
    st.divider()

    # User input
    resume_input = st.text_area(
        "Paste your resume or skills details below:",
        placeholder="e.g. Senior Data Engineer with 5 years experience in Python, PostgreSQL, AWS, Apache Spark, Airflow, and building data pipelines.",
        height=150,
    )

    if resume_input:
        if len(resume_input.strip()) < 10:
            st.warning("Please provide a longer description (at least 10 characters).")
        else:
            with st.spinner("🧠 Gemini AI is analysing your resume..."):
                payload = {
                    "resume_text": resume_input,
                    "top_n": top_n
                }
                try:
                    r = requests.post(f"{BASE}/api/v1/ai/recommend", json=payload, timeout=30)
                    if r.status_code == 200:
                        result = r.json()
                        
                        # Render AI analysis profile
                        st.subheader("🤖 AI Career Profile Summary")
                        st.markdown(
                            f"""
                            <div style="background: linear-gradient(135deg, #1f2937 0%, #111827 100%); border: 1px solid #30363d; border-radius: 12px; padding: 20px; box-shadow: 0 4px 24px rgba(0,0,0,0.4); margin-bottom: 24px;">
                                <p style="font-size: 1.05rem; line-height: 1.6; color: #e6edf3; font-style: italic; margin: 0;">
                                    "{result['ai_summary']}"
                                </p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        # Render extracted skills
                        st.subheader("🛠️ Extracted Technical Skills")
                        skills_html = "".join(
                            f'<span style="background-color: #162c46; color: #58a6ff; font-weight: 500; font-size: 0.85rem; padding: 4px 12px; border-radius: 16px; margin-right: 8px; margin-bottom: 8px; display: inline-block; border: 1px solid #30363d;">{s}</span>'
                            for s in result["extracted_skills"]
                        )
                        st.markdown(skills_html, unsafe_allow_html=True)
                        st.write("")

                        # Render recommended roles if any
                        if result.get("recommended_roles"):
                            st.subheader("💼 Recommended Positions")
                            roles_html = "".join(
                                f'<span style="background-color: #382402; color: #f0883e; font-weight: 500; font-size: 0.85rem; padding: 4px 12px; border-radius: 16px; margin-right: 8px; margin-bottom: 8px; display: inline-block; border: 1px solid #30363d;">{r}</span>'
                                for r in result["recommended_roles"]
                            )
                            st.markdown(roles_html, unsafe_allow_html=True)
                            st.write("")

                        # Render matching jobs
                        st.subheader("🎯 Matching Jobs in Database")
                        matched_jobs = result["matched_jobs"]
                        
                        if matched_jobs:
                            st.success(f"Found {len(matched_jobs)} matching job listings!")
                            for idx, job in enumerate(matched_jobs):
                                title = job["title"]
                                company = job["company_name"]
                                source = job["source"].upper()
                                url = job["url"]
                                location = job.get("country") or "Remote"
                                seniority = job.get("seniority") or "Unspecified"
                                job_id = job["id"]

                                salary_str = "Not specified"
                                if job.get("salary_min") and job.get("salary_max"):
                                    curr = job.get("salary_currency") or "$"
                                    salary_str = f"{curr}{int(job['salary_min']):,} - {curr}{int(job['salary_max']):,}"

                                with st.container():
                                    st.markdown(
                                        f"""
                                        <div style="background-color: #161b22; border: 1px solid #21262d; border-radius: 12px; padding: 18px; margin-bottom: 12px;">
                                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                                <h4 style="margin: 0; font-size: 1.1rem;"><a href="{url}" target="_blank" style="color: #58a6ff; text-decoration: none;">{title}</a></h4>
                                                <div>
                                                    <span style="background-color: #162c46; color: #58a6ff; font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; font-weight: 600; text-transform: uppercase;">{source}</span>
                                                    <span style="background-color: #382402; color: #f0883e; font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; font-weight: 600; text-transform: uppercase; margin-left: 6px;">{seniority}</span>
                                                </div>
                                            </div>
                                            <div style="color: #e6edf3; font-weight: 500; font-size: 0.95rem; margin-top: 4px;">{company}</div>
                                            <div style="color: #8b949e; font-size: 0.8rem; margin-top: 8px;">
                                                📍 {location} &bull; 💰 {salary_str} &bull; ID: #{job_id}
                                            </div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                                    
                                    # Inline bookmark button
                                    bookmark_btn_col, _ = st.columns([1.5, 4.5])
                                    with bookmark_btn_col:
                                        if st.button("⭐ Bookmark Job", key=f"ai_bk_{job_id}_{idx}", use_container_width=True):
                                            try:
                                                resp = requests.post(f"{BASE}/api/v1/bookmarks", json={"job_id": job_id}, timeout=15)
                                                if resp.status_code == 201:
                                                    st.toast(f"Bookmarked Job #{job_id} successfully!")
                                                else:
                                                    st.error(f"Could not bookmark: {resp.text}")
                                            except Exception as e:
                                                st.error(str(e))
                                    st.write("")
                        else:
                            st.info("No matching jobs in the database. Add more detailed tech stack components to match against.")
                    else:
                        st.error(f"Failed to fetch recommendations: {r.text}")
                except Exception as exc:
                    st.error(f"Connection error: {exc}")
    else:
        st.info("💡 Enter your developer/analyst profile details or paste your resume text to trigger AI job intelligence.")

# ---- Email Alerts ------------------------------------------------------------
elif page == "📧 Email Alerts":
    st.markdown("# 📧 Job Alert Email Subscriptions")
    st.markdown("Set up a customized daily email digest of newly ingested remote jobs matching your skills.")
    st.divider()

    # Dynamic loading of skill options for multiselect
    skills_df = _safe_fetch("/api/v1/trends/skills", {"limit": 100})
    if not skills_df.empty and "skill" in skills_df.columns:
        skill_options = sorted(skills_df["skill"].unique().tolist())
    else:
        skill_options = ["python", "sql", "aws", "docker", "fastapi", "javascript", "react", "kubernetes", "golang", "machine learning"]

    tab1, tab2, tab3 = st.tabs(["✍️ Subscribe", "🚫 Unsubscribe", "🚀 Trigger Alerts Cycle"])

    with tab1:
        st.subheader("Create or Update Subscription")
        col1, col2 = st.columns(2)
        with col1:
            sub_name = st.text_input("Your Name", placeholder="e.g. Alex Johnson")
            sub_email = st.text_input("Your Email", placeholder="e.g. alex@example.com")
            selected_skills = st.multiselect(
                "Filter by Skills (Leave empty to receive all jobs)",
                options=skill_options,
                help="Select specific technology tags you want to monitor."
            )
            
            custom_skills = st.text_input("Add other custom skills (comma-separated)", placeholder="e.g. pytorch, dbt")
            if custom_skills:
                extra_skills = [s.strip().lower() for s in custom_skills.split(",") if s.strip()]
                selected_skills = list(set(selected_skills + extra_skills))

            if st.button("Subscribe", type="primary"):
                if not sub_name or not sub_email:
                    st.error("Please fill in both Name and Email fields.")
                elif "@" not in sub_email or "." not in sub_email:
                    st.error("Please enter a valid email address.")
                else:
                    payload = {
                        "name": sub_name,
                        "email": sub_email,
                        "skills": selected_skills
                    }
                    try:
                        r = requests.post(f"{BASE}/api/v1/subscriptions", json=payload, timeout=15)
                        if r.status_code == 201:
                            st.success(f"🎉 Successfully subscribed {sub_email}!")
                            st.info(
                                "✉️ Email Alerts are active! If real SMTP credentials are not configured in settings, "
                                "the pipeline will run in simulation mode and save the HTML email digests to "
                                "`logs/email_alerts/`."
                            )
                        else:
                            st.error(f"Failed to subscribe: {r.text}")
                    except Exception as exc:
                        st.error(f"Error connecting to server: {exc}")

        with col2:
            st.markdown("### 📧 Live Email Preview")
            st.caption("This mockup dynamically updates to show what your next digest email will look like:")
            preview_jobs_df = _safe_fetch("/api/v1/jobs", {"page_size": 100})
            preview_name = sub_name or "Subscriber"
            preview_html = get_mock_email_html(preview_name, selected_skills, preview_jobs_df)
            st.components.v1.html(preview_html, height=450, scrolling=True)

    with tab2:
        st.subheader("Cancel Subscription")
        unsub_email = st.text_input("Email to Unsubscribe", placeholder="your_email@example.com")
        if st.button("Cancel Alerts", type="secondary"):
            if not unsub_email:
                st.error("Please enter your registered email address.")
            else:
                try:
                    payload = {"email": unsub_email}
                    r = requests.post(f"{BASE}/api/v1/subscriptions/unsubscribe", json=payload, timeout=15)
                    if r.status_code == 200:
                        st.success(f"🚫 Successfully unsubscribed {unsub_email} from all job alerts.")
                    elif r.status_code == 404:
                        st.warning(f"No active subscription found for email: {unsub_email}")
                    else:
                        st.error(f"Error unsubscribing: {r.text}")
                except Exception as exc:
                    st.error(f"Error connecting to server: {exc}")

    with tab3:
        st.subheader("🚀 Manual Alerts Dispatch Cycle")
        st.markdown(
            "Click the button below to manually run the alert cycle now. This will query all active subscribers, "
            "fetch matching jobs ingested since their last alert, build custom HTML digests, and dispatch them via SMTP "
            "(or save them to the local `logs/email_alerts/` directory if simulated)."
        )
        
        force_option = st.checkbox("Bypass 23h elapsed limit (Force send)", value=True)
        
        if st.button("Dispatch Job Alerts Now", type="primary"):
            with st.spinner("Processing subscription digests..."):
                try:
                    r = requests.post(f"{BASE}/api/v1/subscriptions/trigger?force={str(force_option).lower()}", timeout=30)
                    if r.status_code == 200:
                        data = r.json()
                        st.success(f"🎉 Success: {data['message']}")
                        st.balloons()
                        
                        # Give context if simulated
                        st.info(
                            "📂 Simulated HTML output digests are saved at **`logs/email_alerts/`** "
                            "within the project directory. Go there to inspect the generated HTML emails!"
                        )
                    else:
                        st.error(f"Failed to dispatch: {r.text}")
                except Exception as exc:
                    st.error(f"Failed to trigger alerts: {exc}")


# ---- Browse Jobs -------------------------------------------------------------
elif page == "🗂️ Browse Jobs":
    st.markdown("# 🗂️ Browse Job Postings")
    st.markdown("Raw bronze-layer job records from the ingestion pipeline.")
    st.divider()

    # Get all active sources from stats, excluding session alias 'all'
    active_sources = [s for s in stats.get("sources", []) if s != "all"]
    source_filter = st.selectbox("Source", options=["All"] + active_sources)

    # Search / filter
    search = st.text_input(
        "🔍 Search title or company", placeholder="e.g. Data Engineer, Stripe"
    )

    # Fetch jobs dynamically with the selected filters
    params = {"page_size": 200}
    if source_filter != "All":
        params["source"] = source_filter
    if seniority_filter != "All":
        params["seniority"] = seniority_filter
    if min_salary_filter > 0:
        params["min_salary"] = min_salary_filter

    display_df = _safe_fetch("/api/v1/jobs", params)

    if not display_df.empty:
        if search:
            mask = display_df["title"].str.contains(search, case=False, na=False) | display_df[
                "company_name"
            ].str.contains(search, case=False, na=False)
            display_df = display_df[mask]

        st.caption(f"Showing **{len(display_df)}** records")
        st.dataframe(
            display_df[
                [
                    "id",
                    "title",
                    "company_name",
                    "country",
                    "seniority",
                    "salary_min",
                    "salary_max",
                    "salary_currency",
                    "source",
                    "publication_date",
                    "url",
                ]
            ],
            column_config={
                "id": st.column_config.NumberColumn("Job ID", format="%d"),
                "url": st.column_config.LinkColumn("Job Link", help="Click to open the job posting"),
                "publication_date": st.column_config.DatetimeColumn("Published At"),
                "salary_min": st.column_config.NumberColumn("Min Salary", format="$%.0f"),
                "salary_max": st.column_config.NumberColumn("Max Salary", format="$%.0f"),
                "salary_currency": st.column_config.TextColumn("Currency"),
                "seniority": st.column_config.TextColumn("Seniority"),
            },
            use_container_width=True,
            hide_index=True,
        )

        # Export browse jobs data
        st.write("")
        exp_col1, exp_col2, _ = st.columns([1.2, 1.2, 4])
        with exp_col1:
            csv_data = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Export Jobs (CSV)",
                data=csv_data,
                file_name="careerlens_browse_jobs.csv",
                mime="text/csv",
                key="download_browse_csv"
            )
        with exp_col2:
            try:
                excel_data = to_excel_data(display_df)
                st.download_button(
                    label="📈 Export Jobs (Excel)",
                    data=excel_data,
                    file_name="careerlens_browse_jobs.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_browse_excel"
                )
            except Exception as e:
                st.caption(f"Excel export disabled: {e}")

        st.divider()
        st.subheader("🔖 Save/Bookmark Job")
        bk_col1, bk_col2, bk_col3 = st.columns([2, 3, 1.5])
        with bk_col1:
            job_to_bookmark = st.number_input("Enter Job ID to Bookmark", min_value=0, step=1, value=0)
        with bk_col2:
            bookmark_notes = st.text_input("Add personal notes (optional)", placeholder="e.g. Apply by Friday, High match")
        with bk_col3:
            st.write("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("⭐ Bookmark Job", use_container_width=True):
                if job_to_bookmark == 0:
                    st.error("Please enter a valid Job ID.")
                else:
                    try:
                        resp = requests.post(
                            f"{BASE}/api/v1/bookmarks",
                            json={"job_id": job_to_bookmark, "notes": bookmark_notes or None},
                            timeout=15
                        )
                        if resp.status_code == 201:
                            st.success(f"Starred job #{job_to_bookmark}!")
                            st.rerun()
                        else:
                            st.error(f"Error: {resp.json().get('detail', resp.text)}")
                    except Exception as exc:
                        st.error(f"Connection error: {exc}")
    else:
        _empty_chart("Jobs")


# ---- Bookmarks Page -----------------------------------------------------------
elif page == "🔖 Bookmarks":
    st.markdown("# 🔖 Starred & Bookmarked Jobs")
    st.markdown("Your saved remote job opportunities with personal notes.")
    st.divider()

    try:
        r = requests.get(f"{BASE}/api/v1/bookmarks", timeout=15)
        r.raise_for_status()
        bookmarks = r.json()
    except Exception as exc:
        st.error(f"Could not load bookmarks: {exc}")
        bookmarks = []

    if not bookmarks:
        st.info("No bookmarks saved yet. Go to **🗂️ Browse Jobs** to star your first remote job!")
    else:
        st.caption(f"You have **{len(bookmarks)}** starred job listings")
        
        # Display bookmarks as premium cards
        for b in bookmarks:
            b_id = b["id"]
            job_id = b["job_id"]
            title = b["title"] or "Unknown Job"
            company = b["company_name"] or "Unknown Company"
            notes = b["notes"] or ""
            source = b["source"].upper()
            url = b["url"]
            bookmarked_at = b["bookmarked_at"][:10]  # Show date only

            # Layout each bookmark card elegantly
            with st.container():
                st.markdown(
                    f"""
                    <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                        <span style="background-color: #21262d; color: #58a6ff; font-size: 0.7rem; font-weight: 600; padding: 2px 8px; border-radius: 12px; margin-right: 8px;">ID: {job_id}</span>
                        <span style="background-color: #1f2937; color: #8b949e; font-size: 0.7rem; padding: 2px 8px; border-radius: 12px;">{source}</span>
                        <h3 style="margin: 8px 0 2px 0;"><a href="{url}" target="_blank" style="color: #58a6ff; text-decoration: none;">{title}</a></h3>
                        <div style="color: #c9d1d9; font-weight: 500; font-size: 0.9rem; margin-bottom: 8px;">{company}</div>
                        <div style="font-size: 0.75rem; color: #8b949e; margin-bottom: 12px;">Saved on {bookmarked_at}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Interactive Note and Delete buttons
                note_col, del_col = st.columns([5, 1])
                with note_col:
                    new_notes = st.text_input(
                        "Personal Notes",
                        value=notes,
                        placeholder="Click enter to save notes...",
                        key=f"note_input_{job_id}"
                    )
                    if new_notes != notes:
                        try:
                            resp = requests.put(
                                f"{BASE}/api/v1/bookmarks/{job_id}",
                                json={"notes": new_notes or None},
                                timeout=15
                            )
                            if resp.status_code == 200:
                                st.success("Notes saved!")
                                st.rerun()
                        except Exception as exc:
                            st.error(f"Error saving notes: {exc}")
                with del_col:
                    st.write("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ Remove", key=f"del_btn_{job_id}", use_container_width=True):
                        try:
                            resp = requests.delete(f"{BASE}/api/v1/bookmarks/{job_id}", timeout=15)
                            if resp.status_code == 200:
                                st.success("Removed!")
                                st.rerun()
                        except Exception as exc:
                            st.error(f"Error: {exc}")
                
                st.markdown("<hr style='margin: 16px 0; border-color: #21262d;'>", unsafe_allow_html=True)




# ---------------------------------------------------------------------------
# Auto-refresh — sleeps 60s then clears cache and reruns
# ---------------------------------------------------------------------------
if auto_refresh:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
