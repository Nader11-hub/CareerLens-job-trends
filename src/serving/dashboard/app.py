"""CareerLens Streamlit Dashboard.

A premium dark-themed, multi-section analytics dashboard that consumes the
CareerLens FastAPI to visualise global job market trends.
"""

from __future__ import annotations

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
            "🗂️ Browse Jobs",
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
    st.markdown("# 💸 Salary Analysis")
    st.markdown("Salary insights extracted from job postings across all sources.")
    st.divider()

    # Fetch 200 jobs to analyze salaries
    jobs_df = _safe_fetch("/api/v1/jobs", {"page_size": 200})

    if not jobs_df.empty and "salary_min" in jobs_df.columns:
        # Filter for jobs with valid salary data
        salary_df = jobs_df.dropna(subset=["salary_min", "salary_max"]).copy()
        
        # Calculate average salary for each job
        if not salary_df.empty:
            salary_df["avg_salary"] = (salary_df["salary_min"] + salary_df["salary_max"]) / 2
            
            # Convert non-USD if we want, but since most are USD or we can just group by currency
            currencies = [c for c in salary_df["salary_currency"].unique() if c]
            selected_currency = st.selectbox("Select Currency", options=currencies if len(currencies) > 0 else ["USD"])
            
            curr_df = salary_df[salary_df["salary_currency"] == selected_currency]
            
            if not curr_df.empty:
                # KPI Metrics
                c1, c2, c3 = st.columns(3)
                avg_sal = curr_df["avg_salary"].mean()
                max_sal = curr_df["salary_max"].max()
                pct_sal = (len(salary_df) / len(jobs_df)) * 100
                
                _kpi(c1, f"{selected_currency} {int(avg_sal):,}", "Average Salary")
                _kpi(c2, f"{selected_currency} {int(max_sal):,}", "Maximum Salary")
                _kpi(c3, f"{pct_sal:.1f}%", "Jobs with Salary Info")
                
                st.write("")
                
                # Chart 1: Salary Distribution Histogram
                fig_dist = px.histogram(
                    curr_df,
                    x="avg_salary",
                    nbins=15,
                    title=f"Salary Distribution ({selected_currency})",
                    labels={"avg_salary": "Average Salary"},
                    color_discrete_sequence=[_ACCENT],
                )
                _apply_layout(fig_dist)
                
                # Chart 2: Average Salary by Seniority
                seniority_grp = curr_df.groupby("seniority")["avg_salary"].mean().reset_index()
                # Sort seniority logically
                seniority_order = {"Junior": 0, "Mid-level": 1, "Senior": 2, "Lead": 3, "Unspecified": 4}
                seniority_grp["sort_order"] = seniority_grp["seniority"].map(seniority_order).fillna(5)
                seniority_grp = seniority_grp.sort_values("sort_order")
                
                fig_sen = px.bar(
                    seniority_grp,
                    x="seniority",
                    y="avg_salary",
                    title=f"Average Salary by Seniority ({selected_currency})",
                    labels={"avg_salary": "Avg Salary", "seniority": "Seniority"},
                    color="avg_salary",
                    color_continuous_scale=px.colors.sequential.Blues,
                )
                _apply_layout(fig_sen)
                
                # Render charts side by side
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(fig_dist, use_container_width=True)
                with col2:
                    st.plotly_chart(fig_sen, use_container_width=True)
                    
                st.divider()
                
                # Table: Top paying roles
                st.subheader("🏆 Top Paying Postings")
                top_paying = curr_df.sort_values(by="salary_max", ascending=False).head(10)
                st.dataframe(
                    top_paying[["title", "company_name", "seniority", "salary_min", "salary_max", "url"]],
                    column_config={
                        "url": st.column_config.LinkColumn("Job Link"),
                        "salary_min": st.column_config.NumberColumn("Min Salary", format=f"{selected_currency} %.0f"),
                        "salary_max": st.column_config.NumberColumn("Max Salary", format=f"{selected_currency} %.0f"),
                    },
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info(f"No salary records found for currency: {selected_currency}")
        else:
            st.info("No jobs in this batch have explicit salary ranges. Try running the live pipeline to fetch newer jobs.")
    else:
        st.info("No job data available. Run the pipeline to ingest jobs.")

# ---- Resume Skill Matcher ----------------------------------------------------
elif page == "🧠 Resume Matcher":
    st.markdown("# 🧠 Resume Skill Matcher")
    st.markdown("Paste your skills or resume description below to find matching remote jobs in our database.")
    st.divider()

    # User input for resume/skills
    user_input = st.text_area(
        "Enter your skills, tech stack, or paste your resume text:",
        placeholder="e.g. Python, SQL, PostgreSQL, Docker, FastAPI, dbt, pandas, AWS, git",
        height=150,
    )

    if user_input:
        # Simple tokenization of user input
        import re
        user_skills = set(re.findall(r'\b[a-zA-Z0-9+#\-\.]+\b', user_input.lower()))
        
        # Filter out common stop words / short words unless they are valid tech keywords (like c, go, r)
        stopwords = {"and", "the", "with", "for", "from", "using", "experience", "work", "skills", "development", "data", "software", "engineer", "developer", "role"}
        cleaned_skills = {s for s in user_skills if s not in stopwords and (len(s) > 1 or s in ["c", "r", "go"])}
        
        if cleaned_skills:
            st.write(f"🔍 Identified skills: " + ", ".join(f"`{s}`" for s in sorted(cleaned_skills)))
            
            # Fetch batch of jobs to match
            jobs_df = _safe_fetch("/api/v1/jobs", {"page_size": 200})
            
            if not jobs_df.empty:
                matches = []
                for _, row in jobs_df.iterrows():
                    # Extract job terms
                    job_tags = set(row.get("tags") or [])
                    # Add words from job title to improve matching
                    title_words = set(re.findall(r'\b[a-zA-Z0-9+#\-\.]+\b', row["title"].lower()))
                    job_terms = job_tags.union(title_words)
                    
                    # Intersect skills
                    matched = cleaned_skills.intersection(job_terms)
                    
                    if matched:
                        score = (len(matched) / len(cleaned_skills)) * 100
                        matches.append({
                            "title": row["title"],
                            "company_name": row["company_name"],
                            "country": row.get("country") or "Remote",
                            "seniority": row.get("seniority") or "Mid-level",
                            "matched_skills": list(matched),
                            "match_score": round(score),
                            "url": row["url"]
                        })
                
                if matches:
                    match_df = pd.DataFrame(matches).sort_values(by="match_score", ascending=False)
                    st.success(f"🎉 Found **{len(match_df)}** matching jobs!")
                    
                    # Render matches
                    st.dataframe(
                        match_df[["match_score", "title", "company_name", "country", "seniority", "matched_skills", "url"]],
                        column_config={
                            "match_score": st.column_config.ProgressColumn("Match Score", min_value=0, max_value=100, format="%d%%"),
                            "url": st.column_config.LinkColumn("Apply Link"),
                        },
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("No matching jobs found. Try entering different or more specific technical skills (e.g., Python, SQL, AWS).")
            else:
                st.info("No jobs available to match against.")
        else:
            st.warning("Please enter some valid tech skills (e.g. 'Python, SQL').")
    else:
        st.info("💡 Paste your skills above, and we will scan our database of active jobs to show you matching postings.")

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
    else:
        _empty_chart("Jobs")


# ---------------------------------------------------------------------------
# Auto-refresh — sleeps 60s then clears cache and reruns
# ---------------------------------------------------------------------------
if auto_refresh:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
