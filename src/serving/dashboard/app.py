"""CareerLens Streamlit Dashboard.

A premium dark-themed, multi-section analytics dashboard that consumes the
CareerLens FastAPI to visualise global job market trends.
"""

from __future__ import annotations

import json
import os
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
from streamlit_autorefresh import st_autorefresh

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
# Custom CSS — Gradient Mesh Dark Premium Look
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ================================================================
       CAREERLENS — BOLD GRADIENT DESIGN SYSTEM v5  (MESH DARK EDITION)
       Page: Animated Gradient Mesh (#12101C base + indigo/violet/teal/pink blobs)
       Cards: Glassmorphic white surfaces floating above the mesh
       Primary Accent Duo: Indigo to Violet (#4F46E5 → #7C3AED)
       Secondary Accent Duo: Blue to Teal (#2563EB → #06B6D4)
    ================================================================ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300..900;1,14..32,300..900&display=swap');

    :root {
        --color-bg:           #12101C;
        --color-surface:      rgba(21, 18, 31, 0.90);
        --color-surface-glass: rgba(21, 18, 31, 0.70);
        --color-border:       rgba(139, 92, 246, 0.22);
        --color-border-muted: rgba(139, 92, 246, 0.12);
        --color-accent:       #4F46E5;
        --color-accent-hover: #4338CA;
        --color-accent-soft:  rgba(139, 92, 246, 0.12);
        --color-text-primary:   #F8FAFC;
        --color-text-secondary: #CBD5E1;
        --color-text-muted:     #94A3B8;
        --color-success-bg:   rgba(16, 185, 129, 0.08);
        --color-success-text: #10B981;
        --color-success-border: rgba(16, 185, 129, 0.18);
        --color-warn-bg:   rgba(245, 158, 11, 0.08);
        --color-warn-text: #F59E0B;
        --color-warn-border: rgba(245, 158, 11, 0.18);
        --radius-sm:  6px;
        --radius-md:  10px;
        --radius-lg:  14px;
        --gradient-primary:   linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        --gradient-secondary: linear-gradient(135deg, #2563EB 0%, #06B6D4 100%);
        --shadow-card: 0 4px 24px rgba(18, 16, 28, 0.30), 0 1px 4px rgba(79, 70, 229, 0.10);
        --shadow-card-hover: 0 12px 40px rgba(18, 16, 28, 0.45), 0 4px 16px rgba(99, 102, 241, 0.22);
        --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
        --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ── Gradient Mesh Blob Animation ───────────────────────────────── */
    @keyframes meshBlob1 {
        0%   { background-position: 15% 20%, 85% 75%, 72% 12%, 8% 82%; }
        33%  { background-position: 18% 25%, 80% 70%, 78% 18%, 5% 85%; }
        66%  { background-position: 12% 15%, 88% 78%, 68% 10%, 12% 80%; }
        100% { background-position: 15% 20%, 85% 75%, 72% 12%, 8% 82%; }
    }

    /* ── Page Background — Animated Gradient Mesh ───────────────────── */
    .stApp {
        background-color: #12101C !important;
        background-image:
            radial-gradient(ellipse 700px 600px at 15% 20%, rgba(99, 102, 241, 0.52) 0%, transparent 60%),
            radial-gradient(ellipse 800px 650px at 85% 75%, rgba(6, 182, 212, 0.46) 0%, transparent 60%),
            radial-gradient(ellipse 500px 500px at 72% 12%, rgba(217, 70, 239, 0.30) 0%, transparent 55%),
            radial-gradient(ellipse 620px 550px at 8% 82%,  rgba(30, 58, 138, 0.40) 0%, transparent 60%) !important;
        background-size: 200% 200% !important;
        background-attachment: fixed !important;
        animation: meshBlob1 28s ease-in-out infinite alternate !important;
    }
    /* ── Blanket Transparent Reset (Nuclear Option) ─────────────────── */
    .stApp, .stApp * {
        background-color: transparent !important;
    }

    /* ── Selectively Re-Apply Backgrounds with Higher Specificity ─── */
    .stApp {
        background-color: #12101C !important;
    }
    .stApp section[data-testid="stSidebar"] {
        background-color: #15121F !important;
    }
    .stApp .kpi-card,
    .stApp .stMetric,
    .stApp div[data-testid="stPlotlyChart"],
    .stApp .premium-card,
    .stApp .status-toolbar,
    .stApp .top-navbar,
    .stApp .page-header-area,
    .stApp div[data-testid="stDataFrame"],
    .stApp div[data-testid="stDataframe"],
    .stApp div[data-testid="stTabs"],
    .stApp div[data-testid="stExpander"],
    .stApp div[data-testid="stToast"] {
        background-color: var(--color-surface-glass) !important;
        border-color: var(--color-border) !important;
    }
    .stApp div[data-testid="stAlert"] {
        background-color: var(--color-surface-glass) !important;
        border-color: var(--color-border) !important;
    }
    .stApp div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    .stApp div[data-testid="stNumberInput"] div[data-baseweb="input"],
    .stApp .stTextInput input,
    .stApp .stTextArea textarea,
    .stApp div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
    .stApp div[data-testid="stFileUploader"] {
        background-color: #1F1A2D !important;
        color: #FFFFFF !important;
        border-color: var(--color-border) !important;
    }
    .stApp section[data-testid="stSidebar"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    .stApp section[data-testid="stSidebar"] div[data-testid="stNumberInput"] div[data-baseweb="input"] {
        background-color: #221E2F !important;
    }
    .stApp section[data-testid="stSidebar"] button {
        background-color: #2D283E !important;
    }

    /* ── Noise grain overlay for premium texture ─────────────────────── */
    .stApp::before {
        content: "" !important;
        position: fixed !important;
        inset: 0 !important;
        pointer-events: none !important;
        z-index: 0 !important;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E") !important;
        opacity: 0.04 !important;
    }

    /* ── Dark vignette at viewport edges ───────────────────────────── */
    .stApp::after {
        content: "" !important;
        position: fixed !important;
        inset: 0 !important;
        pointer-events: none !important;
        z-index: 0 !important;
        background: radial-gradient(ellipse 120% 120% at 50% 50%, transparent 55%, rgba(5, 4, 12, 0.65) 100%) !important;
    }

    /* ── Global Typography & Reset ──────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: var(--font-sans) !important;
        -webkit-font-smoothing: antialiased !important;
    }
    .main .block-container {
        padding-top: 0 !important;
        padding-bottom: 40px !important;
        max-width: 1200px !important;
        position: relative !important;
        z-index: 1 !important;
    }
    .main [data-testid="stMarkdownContainer"] p,
    .main p {
        color: var(--color-text-secondary) !important;
        font-size: 0.92rem !important;
        line-height: 1.62 !important;
    }
    h1, h2, h3, h4 {
        color: var(--color-text-primary) !important;
        letter-spacing: -0.02em !important;
    }

    /* ── Top Navbar ──────────────────────────────────────────────────── */
    .top-navbar {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        padding: 14px 20px 14px 20px !important;
        margin-bottom: 0px !important;
        position: relative !important;
        border-bottom: none !important;
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border-radius: var(--radius-lg) var(--radius-lg) 0 0 !important;
        border: 1px solid var(--color-border) !important;
        border-bottom: none !important;
    }
    .top-navbar::after {
        content: "" !important;
        position: absolute !important;
        bottom: 0 !important;
        left: 20px !important;
        right: 20px !important;
        height: 2px !important;
        background: var(--gradient-primary) !important;
    }
    .nav-brand {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
    }
    .nav-logo-wrap {
        background: var(--gradient-primary) !important;
        width: 32px !important;
        height: 32px !important;
        border-radius: 8px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25) !important;
    }
    .nav-logo-wrap svg {
        color: #ffffff !important;
        stroke: #ffffff !important;
    }
    .nav-title {
        font-size: 1.05rem !important;
        font-weight: 800 !important;
        color: var(--color-text-primary) !important;
        letter-spacing: -0.02em !important;
    }
    .nav-actions { display: flex; align-items: center; gap: 12px; }
    .nav-badge {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        background: rgba(79, 70, 229, 0.12) !important;
        color: #4F46E5 !important;
        border: 1px solid rgba(79, 70, 229, 0.28) !important;
        border-radius: 20px !important;
        padding: 4px 12px !important;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.12) !important;
    }

    /* ── Page Header Area ───────────────────────────────────────────── */
    .page-header-area {
        padding: 20px 20px 24px 20px !important;
        margin-bottom: 20px !important;
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border-radius: 0 0 var(--radius-lg) var(--radius-lg) !important;
        border: 1px solid var(--color-border) !important;
        border-top: none !important;
        box-shadow: var(--shadow-card) !important;
    }
    .header-icon-badge {
        background: var(--gradient-primary) !important;
        width: 42px !important;
        height: 42px !important;
        border-radius: 10px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1.4rem !important;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.2) !important;
        flex-shrink: 0 !important;
    }
    .page-title {
        font-size: 2.1rem !important;
        font-weight: 800 !important;
        color: var(--color-text-primary) !important;
        letter-spacing: -0.04em !important;
        line-height: 1.2 !important;
    }
    .title-link-icon {
        opacity: 0.5;
        transition: var(--transition);
        margin-left: 8px;
        display: inline-flex;
        align-items: center;
    }
    .title-link-icon:hover {
        opacity: 1;
        transform: scale(1.1);
    }
    .page-subtitle {
        font-size: 0.92rem !important;
        font-weight: 400 !important;
        color: var(--color-text-secondary) !important;
        line-height: 1.62 !important;
    }

    /* ── Status Toolbar (Health / Dead Letter) ──────────────────────── */
    .status-toolbar {
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid var(--color-border) !important;
        border-left: 4px solid #4F46E5 !important;
        border-radius: var(--radius-md) !important;
        padding: 12px 20px !important;
        margin-bottom: 24px !important;
        box-shadow: var(--shadow-card) !important;
        display: flex !important;
        align-items: center !important;
        gap: 20px !important;
        flex-wrap: wrap !important;
    }
    .source-pill {
        background: rgba(79, 70, 229, 0.05) !important;
        color: #4F46E5 !important;
        border: 1px solid rgba(79, 70, 229, 0.15) !important;
        padding: 3px 12px !important;
        border-radius: 20px !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        margin-right: 6px;
        font-family: var(--font-mono) !important;
        transition: var(--transition) !important;
    }
    .source-pill:hover {
        background: var(--gradient-primary) !important;
        color: #ffffff !important;
        border-color: transparent !important;
        box-shadow: 0 4px 10px rgba(79, 70, 229, 0.25) !important;
    }

    /* ── Metric / KPI Cards ────────────────────────────────────────── */
    .kpi-card {
        position: relative !important;
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 20px 20px 18px 20px !important;
        box-shadow: var(--shadow-card) !important;
        transition: var(--transition) !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 12px !important;
        min-height: 110px !important;
        overflow: hidden !important;
    }
    .kpi-card::before {
        content: "" !important;
        position: absolute !important;
        top: -30px !important;
        right: -30px !important;
        width: 90px !important;
        height: 90px !important;
        border-radius: 50% !important;
        filter: blur(28px) !important;
        opacity: 0.18 !important;
        pointer-events: none !important;
        transition: var(--transition) !important;
    }
    .gradient-primary-theme::before { background: var(--gradient-primary) !important; }
    .gradient-secondary-theme::before { background: var(--gradient-secondary) !important; }

    .kpi-card:hover {
        transform: translateY(-3px) !important;
    }
    .gradient-primary-theme:hover {
        border-color: rgba(124, 58, 237, 0.55) !important;
        box-shadow: var(--shadow-card-hover) !important;
    }
    .gradient-secondary-theme:hover {
        border-color: rgba(6, 182, 212, 0.55) !important;
        box-shadow: 0 12px 40px rgba(18, 16, 28, 0.45), 0 4px 16px rgba(6, 182, 212, 0.22) !important;
    }

    .kpi-header-row {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
    }
    .kpi-icon-badge-wrap {
        width: 34px !important;
        height: 34px !important;
        border-radius: 8px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex-shrink: 0 !important;
        color: #ffffff !important;
    }
    .kpi-icon-badge-wrap svg {
        width: 15px !important;
        height: 15px !important;
        stroke: #ffffff !important;
        fill: none !important;
    }
    .gradient-primary-theme .kpi-icon-badge-wrap {
        background: var(--gradient-primary) !important;
        box-shadow: 0 3px 8px rgba(79, 70, 229, 0.25) !important;
    }
    .gradient-secondary-theme .kpi-icon-badge-wrap {
        background: var(--gradient-secondary) !important;
        box-shadow: 0 3px 8px rgba(37, 99, 235, 0.25) !important;
    }
    .kpi-label {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        color: var(--color-text-secondary) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        line-height: 1.2 !important;
    }
    .kpi-number {
        font-size: 2rem !important;
        font-weight: 850 !important;
        letter-spacing: -0.04em !important;
        line-height: 1 !important;
        font-variant-numeric: tabular-nums !important;
        font-family: var(--font-sans) !important;
        padding-left: 2px !important;
        background-clip: text !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        display: inline-block !important;
    }
    .gradient-primary-theme .kpi-number {
        background-image: linear-gradient(135deg, #FFFFFF 30%, #8B5CF6 100%) !important;
    }
    .gradient-secondary-theme .kpi-number {
        background-image: linear-gradient(135deg, #FFFFFF 30%, #06B6D4 100%) !important;
    }

    /* ── Section Headers ────────────────────────────────────────────── */
    .section-header {
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        color: var(--color-text-muted) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        margin-bottom: 16px !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    .section-header::before {
        content: "" !important;
        display: inline-block !important;
        width: 4px !important;
        height: 14px !important;
        border-radius: 2px !important;
        background: var(--gradient-primary) !important;
    }

    /* ── Plotly Chart Wrapper Card ──────────────────────────────────── */
    div[data-testid="stPlotlyChart"] {
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 16px !important;
        box-shadow: var(--shadow-card) !important;
        transition: var(--transition) !important;
    }
    div[data-testid="stPlotlyChart"]:hover {
        transform: translateY(-3px) !important;
        box-shadow: var(--shadow-card-hover) !important;
        border-color: rgba(124, 58, 237, 0.45) !important;
    }
    /* ── Sidebar Background & Layout ────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background-color: #15121F !important;
        background-image: none !important;
        border-right: 1px solid rgba(139, 92, 246, 0.15) !important;
        box-shadow: 4px 0 32px rgba(5, 4, 12, 0.35) !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.10) !important;
    }
    .sidebar-logo-text {
        font-size: 1.5rem !important;
        font-weight: 900 !important;
        background: var(--gradient-primary) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        letter-spacing: -0.04em !important;
        margin-bottom: 4px !important;
        display: inline-block !important;
    }

    /* ── Sidebar Typography & Reset ─────────────────────────────────── */
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: #F8FAFC !important;
        margin-top: 14px !important;
        margin-bottom: 8px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span {
        color: #CBD5E1 !important;
    }
    section[data-testid="stSidebar"] .last-updated {
        font-size: 0.72rem !important;
        color: #94A3B8 !important;
    }

    /* ── Navigation Radio Items ─────────────────────────────────────── */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > div {
        background: transparent !important;
        border-left: 4px solid transparent !important;
        transition: var(--transition) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > div[data-checked="true"] {
        background: linear-gradient(135deg, rgba(79, 70, 229, 0.22) 0%, rgba(124, 58, 237, 0.22) 100%) !important;
        border-left: 4px solid #4F46E5 !important;
        box-shadow: inset 0 0 1px rgba(79, 70, 229, 0.3), 0 2px 8px rgba(5, 4, 12, 0.2) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > div label p {
        color: #94A3B8 !important;
        font-weight: 500 !important;
        transition: var(--transition) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > div[data-checked="true"] label p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        text-shadow: 0 0 12px rgba(139, 92, 246, 0.4) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] > div:hover label p {
        color: #F8FAFC !important;
    }

    /* ── Radio circles/checkmarks ───────────────────────────────────── */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radio"] > div:first-child {
        border-color: rgba(255, 255, 255, 0.28) !important;
        background-color: transparent !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radio"][aria-checked="true"] > div:first-child {
        border-color: #4F46E5 !important;
        background-color: #4F46E5 !important;
        box-shadow: 0 0 8px rgba(79, 70, 229, 0.5) !important;
    }

    /* ── Selectboxes & Number Inputs in Sidebar ────────────────────── */
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] div[data-baseweb="input"] {
        background-color: #221E2F !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: #FFFFFF !important;
        border-radius: var(--radius-sm) !important;
        transition: var(--transition) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] div[data-baseweb="input"]:hover {
        border-color: rgba(139, 92, 246, 0.45) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within {
        border-color: #4F46E5 !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.25) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [role="button"],
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] span,
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] div,
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input {
        color: #FFFFFF !important;
    }

    /* ── Number Input Increment/Decrement Buttons ──────────────────── */
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] button {
        background-color: #2D283E !important;
        color: #FFFFFF !important;
        border: none !important;
        border-left: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.12) !important;
        transition: var(--transition) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] button:hover {
        background-color: #4F46E5 !important;
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] svg {
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }

    /* ── Sliders in Sidebar ────────────────────────────────────────── */
    section[data-testid="stSidebar"] div[data-testid="stSlider"] div[data-baseweb="slider"] > div:first-child {
        background: #374151 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSlider"] [data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] div[data-testid="stSlider"] div {
        color: #F1F5F9 !important;
    }

    /* ── Toggle switches in Sidebar ─────────────────────────────────── */
    section[data-testid="stSidebar"] div[data-testid="stCheckbox"] label p {
        color: #F1F5F9 !important;
    }
    section[data-testid="stSidebar"] button[role="switch"] {
        background-color: #374151 !important;
    }
    section[data-testid="stSidebar"] button[role="switch"][aria-checked="true"] {
        background: var(--gradient-primary) !important;
    }

    /* Slider track & thumb */
    div[data-testid="stSlider"] div[data-baseweb="slider"] > div:first-child {
        background: #E5E7EB !important;
        height: 6px !important;
        border-radius: 3px !important;
    }
    div[data-testid="stSlider"] div[data-baseweb="slider"] > div > div[data-testid="stSliderThumb"] {
        background: var(--gradient-primary) !important;
        height: 6px !important;
    }
    div[data-testid="stSlider"] [role="slider"] {
        background-color: #ffffff !important;
        border: 3px solid #4F46E5 !important;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.4) !important;
        width: 18px !important;
        height: 18px !important;
        transition: var(--transition) !important;
    }
    div[data-testid="stSlider"] [role="slider"]:hover {
        transform: scale(1.1) !important;
        box-shadow: 0 0 12px rgba(79, 70, 229, 0.6) !important;
    }

    /* Selectbox / Number Inputs */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    div[data-testid="stNumberInput"] div[data-baseweb="input"] {
        background-color: #1F1A2D !important;
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--color-border) !important;
        color: var(--color-text-primary) !important;
        transition: var(--transition) !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
    div[data-testid="stNumberInput"] div[data-baseweb="input"]:hover {
        border-color: #9CA3AF !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
    div[data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within {
        border-color: var(--color-accent) !important;
        box-shadow: 0 0 0 3px var(--color-accent-soft) !important;
    }

    /* Toggle switches */
    div[data-testid="stCheckbox"] button[role="switch"][aria-checked="true"] {
        background: var(--gradient-primary) !important;
    }

    /* ── Native Streamlit Widgets (Metric etc.) ────────────────────── */
    .stMetric {
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border-radius: var(--radius-lg) !important;
        border: 1px solid var(--color-border) !important;
        box-shadow: var(--shadow-card) !important;
    }

    /* ── Premium Job Cards ──────────────────────────────────────────── */
    .premium-card {
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 20px 24px !important;
        margin-bottom: 12px !important;
        box-shadow: var(--shadow-card) !important;
        transition: var(--transition) !important;
    }
    .premium-card:hover {
        box-shadow: var(--shadow-card-hover) !important;
        border-color: rgba(124, 58, 237, 0.45) !important;
        transform: translateY(-3px) !important;
    }

    /* ── Buttons ────────────────────────────────────────────────────── */
    .stButton > button {
        background: var(--gradient-primary) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 700 !important;
        padding: 8px 20px !important;
        transition: var(--transition) !important;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3) !important;
    }
    .stButton > button:hover {
        box-shadow: 0 4px 12px rgba(79,70,229,0.25) !important;
    }

    /* ── Text inputs ────────────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--color-border) !important;
        font-size: 0.875rem !important;
        color: var(--color-text-primary) !important;
        background: #1F1A2D !important;
        transition: var(--transition) !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--color-accent) !important;
        box-shadow: 0 0 0 3px var(--color-accent-soft) !important;
    }

    /* ── Native Streamlit metric widget ─────────────────────────────── */
    .stMetric {
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border-radius: var(--radius-lg) !important;
        padding: 16px 20px !important;
        border: 1px solid var(--color-border) !important;
        box-shadow: var(--shadow-card) !important;
    }

    /* ── Sidebar footer/brand text ──────────────────────────────────── */
    .sidebar-footer {
        font-size: 0.72rem !important;
        color: var(--color-text-muted) !important;
        text-align: center !important;
        padding: 16px 0 8px 0 !important;
        border-top: 1px solid rgba(0,0,0,0.10) !important;
    }

    /* ── Dataframe / Table containers ───────────────────────────────── */
    div[data-testid="stDataFrame"],
    div[data-testid="stDataframe"] {
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-lg) !important;
        box-shadow: var(--shadow-card) !important;
        overflow: hidden !important;
    }

    /* ── Tabs bar & panels ──────────────────────────────────────────── */
    div[data-testid="stTabs"] {
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-lg) !important;
        box-shadow: var(--shadow-card) !important;
        padding: 4px 4px 16px 4px !important;
    }
    div[data-testid="stTabs"] button[role="tab"] {
        color: var(--color-text-secondary) !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #4F46E5 !important;
        border-bottom: 2px solid #4F46E5 !important;
    }

    /* ── Expanders ──────────────────────────────────────────────────── */
    div[data-testid="stExpander"] {
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-lg) !important;
        box-shadow: var(--shadow-card) !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stExpander"] summary {
        color: var(--color-text-primary) !important;
        font-weight: 600 !important;
    }

    /* ── Alert boxes (info/warning/error/success) ───────────────────── */
    div[data-testid="stAlert"],
    div[class*="stNotification"] {
        border-radius: var(--radius-md) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        box-shadow: 0 2px 12px rgba(18, 16, 28, 0.15) !important;
    }

    /* ── st.info box ─────────────────────────────────────────────── */
    div[data-testid="stAlert"][data-baseweb="notification"] {
        background: var(--color-surface-glass) !important;
        border-left: 4px solid #3b82f6 !important;
        border-color: var(--color-border) !important;
    }

    /* ── Horizontal divider ─────────────────────────────────────────── */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, rgba(79,70,229,0.25), transparent) !important;
        margin: 20px 0 !important;
    }

    /* ── st.subheader / h2 / h3 bare on mesh ───────────────────────── */
    .main h2, .main h3, .main h4, .main h5, .main h6 {
        color: var(--color-text-primary) !important;
    }

    /* ── st.caption ─────────────────────────────────────────────────── */
    div[data-testid="stCaptionContainer"] p {
        color: var(--color-text-muted) !important;
    }

    /* ── Global text visibility — all native Streamlit widgets ──────── */
    /* Force all text in the app to light colors so nothing is invisible */
    .stApp p,
    .stApp span:not([style*="background"]):not(.nav-badge):not(.pill-ok):not(.pill-warn):not(.source-pill),
    .stApp label,
    .stApp [data-testid="stWidgetLabel"] p,
    .stApp [data-testid="stWidgetLabel"] span,
    .stApp [data-testid="stMarkdownContainer"] p,
    .stApp [data-testid="stMarkdownContainer"] li,
    .stApp [data-testid="stMarkdownContainer"] h1,
    .stApp [data-testid="stMarkdownContainer"] h2,
    .stApp [data-testid="stMarkdownContainer"] h3,
    .stApp [data-testid="stMarkdownContainer"] h4,
    .stApp div[data-testid="stSelectbox"] label,
    .stApp div[data-testid="stMultiSelect"] label,
    .stApp div[data-testid="stTextInput"] label,
    .stApp div[data-testid="stTextArea"] label,
    .stApp div[data-testid="stNumberInput"] label,
    .stApp div[data-testid="stSlider"] label,
    .stApp div[data-testid="stRadio"] label,
    .stApp div[data-testid="stCheckbox"] label,
    .stApp div[data-testid="stFileUploader"] label,
    .stApp div[role="radiogroup"] label,
    .stApp div[data-testid="stRadio"] div[data-testid="stMarkdownContainer"] p {
        color: var(--color-text-secondary) !important;
    }

    /* Headings always full bright white */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: var(--color-text-primary) !important;
    }

    /* Dataframe / table cells and headers */
    .stApp [data-testid="stDataFrame"] td,
    .stApp [data-testid="stDataFrame"] th,
    .stApp [data-testid="stDataframe"] td,
    .stApp [data-testid="stDataframe"] th {
        color: var(--color-text-secondary) !important;
    }

    /* Tab labels */
    .stApp div[data-testid="stTabs"] button[role="tab"] {
        color: var(--color-text-secondary) !important;
    }
    .stApp div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #818CF8 !important;
        border-bottom-color: #818CF8 !important;
    }

    /* Expander summary */
    .stApp div[data-testid="stExpander"] summary,
    .stApp div[data-testid="stExpander"] summary span {
        color: var(--color-text-primary) !important;
    }

    /* Selectbox & multiselect option text */
    .stApp [data-baseweb="select"] [data-baseweb="tag"] span {
        color: var(--color-text-primary) !important;
    }

    /* ── Download buttons ───────────────────────────────────────────── */
    div[data-testid="stDownloadButton"] > button {
        background: var(--gradient-secondary) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 700 !important;
        padding: 8px 20px !important;
        transition: var(--transition) !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3) !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        box-shadow: 0 4px 14px rgba(6, 182, 212, 0.35) !important;
    }

    /* ── File uploader ──────────────────────────────────────────────── */
    div[data-testid="stFileUploader"] {
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 2px dashed var(--color-border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 8px !important;
    }

    /* ── Multiselect ────────────────────────────────────────────────── */
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
        background-color: #1F1A2D !important;
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-sm) !important;
    }

    /* ── Spinner overlay ────────────────────────────────────────────── */
    div[data-testid="stSpinner"] {
        color: #4F46E5 !important;
    }

    /* ── Toast notifications ────────────────────────────────────────── */
    div[data-testid="stToast"] {
        background: var(--color-surface-glass) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255,255,255,0.70) !important;
        box-shadow: var(--shadow-card-hover) !important;
        border-radius: var(--radius-md) !important;
        color: var(--color-text-primary) !important;
    }

    /* ── Progress bar ───────────────────────────────────────────────── */
    div[data-testid="stProgress"] > div {
        background: #E5E7EB !important;
        border-radius: 4px !important;
    }
    div[data-testid="stProgress"] > div > div {
        background: var(--gradient-primary) !important;
        border-radius: 4px !important;
    }

    /* ── Columns gap visual fix on mesh ─────────────────────────────── */
    div[data-testid="column"] {
        position: relative !important;
    }

    /* ── Last-updated caption in sidebar ────────────────────────────── */
    .last-updated {
        font-size: 0.72rem !important;
        color: var(--color-text-muted) !important;
        padding: 4px 0 !important;
    }

    /* ── pill-ok / pill-warn (status toolbar) ───────────────────────── */
    .pill-ok {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        background: rgba(5,150,105,0.10) !important;
        color: #059669 !important;
        border: 1px solid rgba(5,150,105,0.22) !important;
        border-radius: 20px !important;
        padding: 2px 10px !important;
    }
    .pill-warn {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        background: rgba(217,119,6,0.10) !important;
        color: #D97706 !important;
        border: 1px solid rgba(217,119,6,0.22) !important;
        border-radius: 20px !important;
        padding: 2px 10px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Plotly theme & brand colors — design system palette
# ---------------------------------------------------------------------------
_PLOTLY_THEME = "simple_white"
_BRAND_COLORS = ["#4F46E5", "#0D9488", "#8B5CF6", "#10B981", "#F59E0B", "#EC4899"]
_ACCENT = "#4F46E5"

_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, -apple-system, sans-serif", size=11, color="#94A3B8"),
    margin=dict(l=8, r=8, t=32, b=8),
    xaxis=dict(
        gridcolor="rgba(255, 255, 255, 0.08)",
        linecolor="rgba(255, 255, 255, 0.15)",
        tickfont=dict(color="#94A3B8", size=11),
        showgrid=True,
    ),
    yaxis=dict(
        gridcolor="rgba(255, 255, 255, 0.08)",
        linecolor="rgba(255, 255, 255, 0.15)",
        tickfont=dict(color="#CBD5E1", size=11),
        showgrid=False,
    ),
    legend=dict(
        bgcolor="rgba(21, 18, 31, 0.9)",
        bordercolor="rgba(139, 92, 246, 0.2)",
        borderwidth=1,
        font=dict(color="#F8FAFC", size=11),
    ),
    hoverlabel=dict(
        bgcolor="#221E2F",
        bordercolor="rgba(139, 92, 246, 0.3)",
        font=dict(family="Inter, sans-serif", size=12, color="#FFFFFF"),
    ),
)

# ---------------------------------------------------------------------------
# Data fetching & offline simulation fallback
# ---------------------------------------------------------------------------
BASE = settings.api_base_url

# Initialize session state for local/offline fallback mode
if "api_fallback" not in st.session_state:
    st.session_state.api_fallback = False
if "bookmarks" not in st.session_state:
    st.session_state.bookmarks = []
if "subscriptions" not in st.session_state:
    st.session_state.subscriptions = []

# ---------------------------------------------------------------------------
# Authentication session state
# ---------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None
if "auth_error" not in st.session_state:
    st.session_state.auth_error = None
if "auth_tab" not in st.session_state:
    st.session_state.auth_tab = "login"  # "login" | "register"
if "local_users" not in st.session_state:
    st.session_state.local_users = {
        "admin": {"password": "admin123", "role": "admin", "email": "admin@careerlens.io", "is_active": True},
        "user": {"password": "user123", "role": "user", "email": "user@careerlens.io", "is_active": True}
    }

_FALLBACK_CSV = "data/fallback/kaggle_fallback.csv"

@st.cache_data(ttl=600, show_spinner=False)
def _get_fallback_silver_df() -> pd.DataFrame:
    """Load and normalize the local fallback CSV dataset to mimic the Silver schema."""
    import re
    if not os.path.exists(_FALLBACK_CSV):
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(_FALLBACK_CSV)
    except Exception:
        return pd.DataFrame()
    
    df["id"] = df["id"].fillna(0).astype(int)
    df["title"] = df["title"].fillna("Unknown Title")
    df["company_name"] = df["company_name"].fillna("Unknown Company")
    
    # Infer country
    def infer_country(loc):
        if not loc or pd.isna(loc):
            return "Global"
        loc_str = str(loc).strip().lower()
        if "worldwide" in loc_str or "global" in loc_str or "anywhere" in loc_str:
            return "Global"
        if "," in str(loc):
            return str(loc).split(",")[-1].strip()
        return str(loc).strip()
    df["country"] = df["candidate_required_location"].apply(infer_country)
    
    # Classify seniority
    def classify_seniority(title):
        t = str(title).lower()
        if "sr" in t or "senior" in t or "lead" in t or "principal" in t or "director" in t:
            return "Senior"
        if "jr" in t or "junior" in t or "entry" in t or "associate" in t or "intern" in t:
            return "Junior"
        return "Mid"
    df["seniority"] = df["title"].apply(classify_seniority)
    
    # Parse salary
    def parse_salary(sal):
        if not sal or pd.isna(sal):
            return None, None, "USD"
        sal_str = str(sal).lower()
        nums = [int(s) for s in re.findall(r'\d+', sal_str.replace(",", ""))]
        if len(nums) >= 2:
            return float(nums[0]), float(nums[1]), "USD"
        elif len(nums) == 1:
            return float(nums[0]), float(nums[0]), "USD"
        return None, None, "USD"
        
    salaries = df["salary"].apply(parse_salary)
    df["salary_min"] = [s[0] for s in salaries]
    df["salary_max"] = [s[1] for s in salaries]
    df["salary_currency"] = [s[2] for s in salaries]
    
    # Published month
    def get_published_month(d):
        if not d or pd.isna(d):
            return "2026-07"
        try:
            dt = pd.to_datetime(d)
            return dt.strftime("%Y-%m")
        except Exception:
            return "2026-07"
            
    df["published_month"] = df["publication_date"].apply(get_published_month)
    df["source"] = "kaggle"
    
    # Extract tags
    def get_tags(t):
        if not t or pd.isna(t):
            return []
        try:
            if str(t).startswith("["):
                import ast
                return ast.literal_eval(str(t))
            return [s.strip().lower() for s in str(t).split(",") if s.strip()]
        except Exception:
            return [s.strip().lower() for s in str(t).split(",") if s.strip()]
            
    df["tags"] = df["tags"].apply(get_tags)
    df["role"] = df["title"]
    
    return df

class MockResponse:
    """Mimics a requests.Response object for offline API simulation."""
    def __init__(self, json_data, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data) if json_data is not None else ""

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")

def _query_local_sqlite(query: str, params: tuple = ()) -> pd.DataFrame:
    """Helper to query the local SQLite database file directly when backend is down."""
    import sqlite3
    db_path = "careerlens_local.db"
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def _simulate_api(method: str, endpoint: str, json_data: dict | None = None, params: dict | None = None):
    """Simulates API responses locally using either SQLite database tables or the fallback CSV."""
    import re
    from datetime import datetime
    endpoint_clean = endpoint.split("?")[0]
    db_exists = os.path.exists("careerlens_local.db")
    
    # helper for parsing tags array
    def parse_tags(t):
        if not t or pd.isna(t):
            return []
        try:
            if str(t).startswith("["):
                import ast
                return ast.literal_eval(str(t))
            return [s.strip().lower() for s in str(t).split(",") if s.strip()]
        except Exception:
            return [s.strip().lower() for s in str(t).split(",") if s.strip()]

    if "/api/v1/stats" in endpoint_clean:
        if db_exists:
            df_jobs = _query_local_sqlite("SELECT COUNT(*) as count FROM silver_jobs")
            total_jobs = int(df_jobs.iloc[0]["count"]) if not df_jobs.empty else 0
            df_src = _query_local_sqlite("SELECT DISTINCT source FROM silver_jobs")
            sources = df_src["source"].str.lower().tolist() if not df_src.empty else ["kaggle"]
            df_countries = _query_local_sqlite("SELECT COUNT(DISTINCT country) as count FROM silver_jobs")
            total_countries = int(df_countries.iloc[0]["count"]) if not df_countries.empty else 0
            df_skills = _query_local_sqlite("SELECT COUNT(DISTINCT skill) as count FROM gold_skill_trends")
            total_skills = int(df_skills.iloc[0]["count"]) if not df_skills.empty else 0
            return MockResponse({
                "total_jobs": total_jobs,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "earliest_job": "2025-12-12",
                "latest_job": datetime.now().strftime("%Y-%m-%d"),
                "sources": sources,
                "total_countries": total_countries,
                "total_skills": total_skills,
                "total_dead_letters": 0
            }, 200)
        else:
            df = _get_fallback_silver_df()
            return MockResponse({
                "total_jobs": len(df),
                "last_updated": "2026-07-02 18:45:00",
                "earliest_job": "2025-12-12",
                "latest_job": "2026-07-02",
                "sources": ["kaggle"],
                "total_countries": df["country"].nunique() if "country" in df.columns else 0,
                "total_skills": 0,
                "total_dead_letters": 0
            }, 200)
        
    elif "/api/v1/trends/countries" in endpoint_clean:
        if db_exists:
            df = _query_local_sqlite("SELECT country, published_month, job_count FROM gold_country_trends ORDER BY job_count DESC")
            return MockResponse(df.to_dict("records"), 200)
        else:
            df = _get_fallback_silver_df()
            agg = df.groupby(["country", "published_month"])["job_id"].count().reset_index()
            agg.columns = ["country", "published_month", "job_count"]
            return MockResponse(agg.to_dict("records"), 200)
        
    elif "/api/v1/trends/skills" in endpoint_clean:
        if db_exists:
            df = _query_local_sqlite("SELECT skill, published_month, job_count FROM gold_skill_trends ORDER BY job_count DESC")
            return MockResponse(df.to_dict("records"), 200)
        else:
            df = _get_fallback_silver_df()
            exploded = df.explode("tags")
            exploded = exploded[exploded["tags"].notna() & (exploded["tags"] != "")]
            agg = exploded.groupby(["tags", "published_month"])["job_id"].count().reset_index()
            agg.columns = ["skill", "published_month", "job_count"]
            return MockResponse(agg.to_dict("records"), 200)
        
    elif "/api/v1/trends/roles" in endpoint_clean:
        if db_exists:
            df = _query_local_sqlite("SELECT role, published_month, job_count FROM gold_role_trends ORDER BY job_count DESC")
            return MockResponse(df.to_dict("records"), 200)
        else:
            df = _get_fallback_silver_df()
            agg = df.groupby(["role", "published_month"])["job_id"].count().reset_index()
            agg.columns = ["role", "published_month", "job_count"]
            return MockResponse(agg.to_dict("records"), 200)
        
    elif "/api/v1/trends/time" in endpoint_clean:
        if db_exists:
            df = _query_local_sqlite("SELECT published_month, job_count FROM gold_time_trends ORDER BY published_month ASC")
            return MockResponse(df.to_dict("records"), 200)
        else:
            df = _get_fallback_silver_df()
            agg = df.groupby("published_month")["job_id"].count().reset_index()
            agg.columns = ["published_month", "job_count"]
            return MockResponse(agg.sort_values("published_month").to_dict("records"), 200)
        
    elif "/api/v1/salary/currencies" in endpoint_clean:
        return MockResponse(["USD", "EUR", "GBP"], 200)
        
    elif "/api/v1/salary/by-role" in endpoint_clean:
        if db_exists:
            df = _query_local_sqlite("""
                SELECT 
                    title as role,
                    AVG((salary_min + salary_max)/2.0) as avg_salary,
                    MIN(salary_min) as min_salary,
                    MAX(salary_max) as max_salary,
                    COUNT(*) as job_count
                FROM silver_jobs
                WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
                GROUP BY title
                ORDER BY avg_salary DESC
            """)
            return MockResponse(df.to_dict("records"), 200)
        else:
            df = _get_fallback_silver_df()
            valid_sal = df[df["salary_min"].notna() & df["salary_max"].notna()].copy()
            if valid_sal.empty:
                return MockResponse([], 200)
            valid_sal["avg"] = (valid_sal["salary_min"] + valid_sal["salary_max"]) / 2
            agg = valid_sal.groupby("role").agg(
                avg_salary=("avg", "mean"),
                min_salary=("salary_min", "min"),
                max_salary=("salary_max", "max"),
                job_count=("job_id", "count")
            ).reset_index()
            return MockResponse(agg.to_dict("records"), 200)
        
    elif "/api/v1/salary/by-country" in endpoint_clean:
        if db_exists:
            df = _query_local_sqlite("""
                SELECT 
                    country,
                    AVG((salary_min + salary_max)/2.0) as avg_salary,
                    MIN(salary_min) as min_salary,
                    MAX(salary_max) as max_salary,
                    COUNT(*) as job_count
                FROM silver_jobs
                WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
                GROUP BY country
                ORDER BY avg_salary DESC
            """)
            return MockResponse(df.to_dict("records"), 200)
        else:
            df = _get_fallback_silver_df()
            valid_sal = df[df["salary_min"].notna() & df["salary_max"].notna()].copy()
            if valid_sal.empty:
                return MockResponse([], 200)
            valid_sal["avg"] = (valid_sal["salary_min"] + valid_sal["salary_max"]) / 2
            agg = valid_sal.groupby("country").agg(
                avg_salary=("avg", "mean"),
                min_salary=("salary_min", "min"),
                max_salary=("salary_max", "max"),
                job_count=("job_id", "count")
            ).reset_index()
            return MockResponse(agg.to_dict("records"), 200)
        
    elif "/api/v1/jobs" in endpoint_clean:
        if db_exists:
            where_clauses = ["1=1"]
            query_params = []
            if params:
                if params.get("source") and params["source"] != "All":
                    where_clauses.append("s.source = ?")
                    query_params.append(params["source"].lower())
                if params.get("seniority") and params["seniority"] != "All":
                    where_clauses.append("s.seniority = ?")
                    query_params.append(params["seniority"])
                if params.get("min_salary") and float(params["min_salary"]) > 0:
                    where_clauses.append("(s.salary_min >= ? OR s.salary_max >= ?)")
                    query_params.append(float(params["min_salary"]))
                    query_params.append(float(params["min_salary"]))
                    
            sql = f"""SELECT s.job_id AS id, s.source, s.title, s.company_name, s.category, s.role,
                      s.country, s.tags, s.publication_date, s.published_month, s.salary_min, s.salary_max,
                      s.salary_currency, s.seniority, coalesce(b.url, '') AS url
                      FROM silver_jobs s
                      LEFT JOIN bronze_jobs b ON s.job_id = b.id
                      WHERE {' AND '.join(where_clauses)} LIMIT 100"""
            df = _query_local_sqlite(sql, tuple(query_params))
            if "tags" in df.columns:
                df["tags"] = df["tags"].apply(parse_tags)
            return MockResponse(df.to_dict("records"), 200)
        else:
            df = _get_fallback_silver_df()
            if params:
                if params.get("source") and params["source"] != "All":
                    df = df[df["source"] == params["source"].lower()]
                if params.get("seniority") and params["seniority"] != "All":
                    df = df[df["seniority"] == params["seniority"]]
                if params.get("min_salary") and float(params["min_salary"]) > 0:
                    df = df[(df["salary_min"] >= float(params["min_salary"])) | (df["salary_max"] >= float(params["min_salary"]))]
            if "job_id" in df.columns and "id" not in df.columns:
                df = df.rename(columns={"job_id": "id"})
            if "url" not in df.columns:
                df["url"] = ""
            return MockResponse(df.to_dict("records"), 200)
        
    elif "/api/v1/bookmarks" in endpoint_clean:
        if method == "GET":
            return MockResponse(st.session_state.bookmarks, 200)
        elif method == "POST":
            job_id = json_data.get("job_id") if json_data else None
            if db_exists:
                df = _query_local_sqlite("""SELECT s.job_id AS id, s.source, s.title, s.company_name,
                                            coalesce(b.url, '') AS url
                                            FROM silver_jobs s
                                            LEFT JOIN bronze_jobs b ON s.job_id = b.id
                                            WHERE s.job_id = ?""", (job_id,))
            else:
                df = _get_fallback_silver_df()
                df = df[df["job_id"] == job_id]
            if not df.empty:
                job_dict = df.iloc[0].to_dict()
                b_item = {
                    "id": len(st.session_state.bookmarks) + 1,
                    "job_id": job_id,
                    "title": job_dict["title"],
                    "company_name": job_dict["company_name"],
                    "notes": "",
                    "source": job_dict.get("source", ""),
                    "url": job_dict.get("url", ""),
                    "bookmarked_at": datetime.now().isoformat()
                }
                st.session_state.bookmarks.append(b_item)
                return MockResponse(b_item, 201)
            return MockResponse({"detail": "Job not found"}, 404)
        elif method == "PUT":
            b_id = int(endpoint_clean.split("/")[-1])
            for b in st.session_state.bookmarks:
                if b["id"] == b_id or b["job_id"] == b_id:
                    b["notes"] = json_data.get("notes", "") if json_data else ""
                    return MockResponse(b, 200)
            return MockResponse({"detail": "Bookmark not found"}, 404)
        elif method == "DELETE":
            b_id = int(endpoint_clean.split("/")[-1])
            st.session_state.bookmarks = [b for b in st.session_state.bookmarks if b["id"] != b_id and b["job_id"] != b_id]
            return MockResponse({"message": "Deleted"}, 200)
            
    elif "/api/v1/subscriptions" in endpoint_clean:
        if "unsubscribe" in endpoint_clean:
            email = json_data.get("email") if json_data else ""
            st.session_state.subscriptions = [s for s in st.session_state.subscriptions if s["email"] != email]
            return MockResponse({"message": "Unsubscribed"}, 200)
        elif "trigger" in endpoint_clean:
            return MockResponse({"message": "Alerts cycle triggered successfully (simulated)"}, 200)
        else:
            sub = {
                "name": json_data.get("name"),
                "email": json_data.get("email"),
                "skills": json_data.get("skills", [])
            }
            st.session_state.subscriptions.append(sub)
            return MockResponse(sub, 201)
            
    elif "/api/v1/ai/recommend" in endpoint_clean:
        resume_text = json_data.get("resume_text", "")
        techs = ["python", "sql", "aws", "docker", "kubernetes", "fastapi", "react", "golang", "machine learning", "dbt", "spark", "airflow", "pandas", "numpy", "java", "javascript", "html", "css", "linux", "git", "github"]
        extracted = []
        for t in techs:
            if re.search(r'\b' + re.escape(t) + r'\b', resume_text.lower()):
                extracted.append(t)
        if not extracted:
            extracted = ["python", "sql"]
            
        if db_exists:
            like_clauses = " OR ".join(["s.title LIKE ?" for _ in extracted] + ["s.tags LIKE ?" for _ in extracted])
            like_params = [f"%{e}%" for e in extracted] * 2
            sql = f"""SELECT s.job_id AS id, s.source, s.title, s.company_name, s.category, s.role,
                      s.country, s.tags, s.publication_date, s.published_month, s.salary_min, s.salary_max,
                      s.salary_currency, s.seniority, coalesce(b.url, '') AS url
                      FROM silver_jobs s
                      LEFT JOIN bronze_jobs b ON s.job_id = b.id
                      WHERE {like_clauses} LIMIT 50"""
            df = _query_local_sqlite(sql, tuple(like_params))
            if df.empty:
                df = _query_local_sqlite("""SELECT s.job_id AS id, s.source, s.title, s.company_name, s.category, s.role,
                                            s.country, s.tags, s.publication_date, s.published_month, s.salary_min, s.salary_max,
                                            s.salary_currency, s.seniority, coalesce(b.url, '') AS url
                                            FROM silver_jobs s
                                            LEFT JOIN bronze_jobs b ON s.job_id = b.id
                                            LIMIT 10""")
        else:
            df = _get_fallback_silver_df()
            if "job_id" in df.columns and "id" not in df.columns:
                df = df.rename(columns={"job_id": "id"})
            if "url" not in df.columns:
                df["url"] = ""
        
        def calc_score(row):
            title_tags = (str(row.get("title", "")) + " " + str(row.get("tags", "")) + " " + str(row.get("category", ""))).lower()
            matches = [e for e in extracted if e in title_tags]
            return int((len(matches) / len(extracted)) * 100)
            
        df["match_score"] = df.apply(calc_score, axis=1)
        df = df[df["match_score"] > 0].sort_values("match_score", ascending=False).head(10)
        
        if "tags" in df.columns:
            df["tags"] = df["tags"].apply(parse_tags)
            
        return MockResponse({
            "ai_summary": f"Based on your profile, you exhibit solid expertise in: {', '.join(extracted).upper()}. We recommend targeting remote jobs matching these keywords.",
            "extracted_skills": extracted,
            "recommended_roles": ["Developer", "Data Analyst"],
            "matched_jobs": df.to_dict("records")
        }, 200)
        
    return MockResponse({}, 404)

# Save the original requests module to avoid infinite recursion when proxying
_real_requests = requests

def _api_request(method: str, url: str, json_data: dict | None = None, params: dict | None = None, timeout: int = 15, _fallback: bool = False):
    """Executes a network request to the API backend, falling back to local simulation on connection failure."""
    endpoint = url.replace(BASE, "")
    
    if _fallback:
        return _simulate_api(method, endpoint, json_data, params)
        
    try:
        r = _real_requests.request(method, url, json=json_data, params=params, timeout=timeout)
        return r
    except _real_requests.RequestException:
        return _simulate_api(method, endpoint, json_data, params)

@st.cache_data(ttl=60, show_spinner=False)
def _fetch(endpoint: str, params_str: str = "{}", _fallback: bool = False) -> pd.DataFrame:
    """Fetch JSON data from the CareerLens API and return as a DataFrame."""
    params = json.loads(params_str) if params_str else {}
    r = _api_request("GET", f"{BASE}{endpoint}", params=params, _fallback=_fallback)
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data) if data else pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_stats(_fallback: bool = False) -> dict:
    r = _api_request("GET", f"{BASE}/api/v1/stats", _fallback=_fallback)
    r.raise_for_status()
    return r.json()

# Monkey patch requests internally for this module to route through _api_request
class CustomRequestsProxy:
    def get(self, url, params=None, **kwargs):
        return _api_request("GET", url, params=params, **kwargs)
    def post(self, url, json=None, params=None, **kwargs):
        return _api_request("POST", url, json_data=json, params=params, **kwargs)
    def put(self, url, json=None, params=None, **kwargs):
        return _api_request("PUT", url, json_data=json, params=params, **kwargs)
    def delete(self, url, **kwargs):
        return _api_request("DELETE", url, **kwargs)
    def request(self, method, url, **kwargs):
        return _api_request(method, url, **kwargs)
    
    @property
    def exceptions(self):
        return _real_requests.exceptions
        
    RequestException = _real_requests.RequestException

requests = CustomRequestsProxy()


def _safe_fetch(endpoint: str, params: dict | None = None) -> pd.DataFrame:
    """Safely fetch data from the API and handle exceptions by returning an empty DataFrame."""
    try:
        # Request up to 500 records to capture full historical trends
        if params is None:
            params = {}
        if "limit" not in params and "trends" in endpoint:
            params["limit"] = 500
        fallback = st.session_state.get("api_fallback", True)
        params_str = json.dumps(params, sort_keys=True)
        return _fetch(endpoint, params_str, _fallback=fallback)
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
                    <a href="{job.get('url', '#')}" class="job-title" target="_blank">{job.get('title','Unknown')}</a>
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
# Authentication helpers — call FastAPI /auth/* endpoints
# ---------------------------------------------------------------------------
def _call_auth(endpoint: str, payload: dict) -> dict | None:
    """POST to an auth endpoint and return JSON on success, or set auth_error."""
    import requests as _req
    try:
        r = _req.post(f"{BASE}{endpoint}", json=payload, timeout=10)
        if r.status_code in (200, 201):
            return r.json()
        data = r.json() if r.text else {}
        st.session_state.auth_error = data.get("detail", f"Error {r.status_code}")
        return None
    except Exception as exc:
        st.session_state.auth_error = f"Could not reach API server: {exc}"
        return None


def _do_login(username: str, password: str) -> bool:
    """Attempt login. On success, persist token & role in session state."""
    # 1. Reset auth error
    st.session_state.auth_error = None
    
    # 2. Try the live API server first if not explicitly forced fallback
    if not st.session_state.api_fallback:
        result = _call_auth("/auth/login", {"username": username, "password": password})
        if result:
            st.session_state.authenticated = True
            st.session_state.token = result["access_token"]
            st.session_state.username = result["username"]
            st.session_state.role = result["role"]
            st.session_state.auth_error = None
            return True
            
    # 3. Fall back to local mock user state if API is unreachable or offline fallback is active
    if st.session_state.api_fallback or (st.session_state.auth_error and "Could not reach API server" in st.session_state.auth_error):
        local_user = st.session_state.local_users.get(username)
        if local_user:
            if not local_user.get("is_active", True):
                st.session_state.auth_error = "Account is deactivated (offline mode)."
                return False
            if local_user["password"] == password:
                st.session_state.authenticated = True
                st.session_state.token = "mock-jwt-token-for-local-session"
                st.session_state.username = username
                st.session_state.role = local_user["role"]
                st.session_state.auth_error = None
                # Auto-enable fallback since API server is down
                st.session_state.api_fallback = True
                return True
            else:
                st.session_state.auth_error = "Invalid username or password (offline mode)."
                return False
        else:
            st.session_state.auth_error = "User not found (offline mode)."
            return False
            
    return False


def _do_register(username: str, email: str, password: str) -> bool:
    """Attempt registration. On success, auto-login."""
    st.session_state.auth_error = None
    
    # 1. Try real API
    if not st.session_state.api_fallback:
        result = _call_auth("/auth/register", {"username": username, "email": email, "password": password})
        if result:
            st.session_state.authenticated = True
            st.session_state.token = result["access_token"]
            st.session_state.username = result["username"]
            st.session_state.role = result["role"]
            st.session_state.auth_error = None
            return True

    # 2. Fall back to local mock user state if API is unreachable or offline
    if st.session_state.api_fallback or (st.session_state.auth_error and "Could not reach API server" in st.session_state.auth_error):
        if username in st.session_state.local_users:
            st.session_state.auth_error = "Username already taken (offline mode)."
            return False
        # Save to local session registry
        st.session_state.local_users[username] = {
            "password": password,
            "role": "user",
            "email": email,
            "is_active": True
        }
        # Auto-login
        st.session_state.authenticated = True
        st.session_state.token = "mock-jwt-token-for-local-session"
        st.session_state.username = username
        st.session_state.role = "user"
        st.session_state.auth_error = None
        st.session_state.api_fallback = True
        return True
        
    return False


def _do_logout() -> None:
    """Clear all authentication state."""
    for key in ("authenticated", "token", "username", "role", "auth_error"):
        st.session_state[key] = None
    st.session_state.authenticated = False


# ---------------------------------------------------------------------------
# Login / Register Gate — shown when not authenticated
# ---------------------------------------------------------------------------
def _render_auth_page() -> None:
    """Render the full-page login/register screen centered."""
    st.markdown(
        """
        <style>
        .auth-outer {
            display: flex; align-items: center; justify-content: center;
            min-height: 80vh; padding: 40px 0;
        }
        .auth-card {
            background: rgba(21, 18, 31, 0.85);
            backdrop-filter: blur(32px);
            -webkit-backdrop-filter: blur(32px);
            border: 1px solid rgba(139, 92, 246, 0.25);
            border-radius: 20px;
            padding: 48px 40px;
            max-width: 460px;
            width: 100%;
            box-shadow: 0 24px 64px rgba(5, 4, 12, 0.5), 0 4px 24px rgba(79, 70, 229, 0.15);
        }
        .auth-logo { text-align: center; margin-bottom: 32px; }
        .auth-logo-icon {
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            width: 64px; height: 64px; border-radius: 16px;
            display: inline-flex; align-items: center; justify-content: center;
            font-size: 2rem; box-shadow: 0 8px 24px rgba(79,70,229,0.35);
            margin-bottom: 16px;
        }
        .auth-title {
            font-size: 1.6rem; font-weight: 800;
            background: linear-gradient(135deg, #FFFFFF 30%, #8B5CF6 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: -0.03em;
        }
        .auth-subtitle { color: #94A3B8; font-size: 0.875rem; margin-top: 4px; }
        .auth-tab-row {
            display: flex; background: rgba(255,255,255,0.04);
            border-radius: 10px; padding: 4px; margin-bottom: 28px;
            border: 1px solid rgba(139,92,246,0.12);
        }
        .auth-tab {
            flex: 1; padding: 8px; text-align: center; border-radius: 7px;
            cursor: pointer; font-size: 0.875rem; font-weight: 600;
            transition: all 0.2s; color: #94A3B8;
        }
        .auth-tab.active {
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            color: white; box-shadow: 0 4px 12px rgba(79,70,229,0.3);
        }
        .auth-error {
            background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239,68,68,0.25);
            color: #F87171; border-radius: 8px; padding: 10px 14px;
            font-size: 0.82rem; margin-bottom: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Use centered column layout to fit nicely on widescreen
    col_l, col_mid, col_r = st.columns([1, 1.2, 1])
    
    with col_mid:
        # Brand header
        st.markdown(
            """
            <div class="auth-logo">
                <div class="auth-logo-icon">🌐</div>
                <div class="auth-title">CareerLens</div>
                <div class="auth-subtitle">Global Job Market Intelligence</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Tab switcher
        sub_col_l, sub_col_r = st.columns(2)
        with sub_col_l:
            if st.button("🔑  Login", use_container_width=True,
                         type="primary" if st.session_state.auth_tab == "login" else "secondary"):
                st.session_state.auth_tab = "login"
                st.session_state.auth_error = None
                st.rerun()
        with sub_col_r:
            if st.button("✨  Register", use_container_width=True,
                         type="primary" if st.session_state.auth_tab == "register" else "secondary"):
                st.session_state.auth_tab = "register"
                st.session_state.auth_error = None
                st.rerun()

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Error message
        if st.session_state.auth_error:
            st.markdown(
                f'<div class="auth-error">⚠️ {st.session_state.auth_error}</div>',
                unsafe_allow_html=True,
            )

        # --- LOGIN FORM ---
        if st.session_state.auth_tab == "login":
            with st.form("login_form", clear_on_submit=False):
                st.markdown("#### Welcome back")
                username = st.text_input("Username", placeholder="Enter your username", key="login_username")
                password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
                submitted = st.form_submit_button("Sign In →", use_container_width=True)
                if submitted:
                    if not username or not password:
                        st.session_state.auth_error = "Please fill in all fields."
                        st.rerun()
                    elif _do_login(username.strip(), password):
                        st.rerun()
                    else:
                        st.rerun()

            st.markdown(
                "<div style='text-align:center;color:#64748B;font-size:0.8rem;margin-top:20px;'>"
                "Don't have an account? Click <strong>Register</strong> above.</div>",
                unsafe_allow_html=True,
            )

        # --- REGISTER FORM ---
        else:
            with st.form("register_form", clear_on_submit=False):
                st.markdown("#### Create your account")
                username = st.text_input("Username", placeholder="Choose a username (min 3 chars)", key="reg_username")
                email = st.text_input("Email", placeholder="your@email.com", key="reg_email")
                password = st.text_input("Password", type="password", placeholder="Min 6 characters", key="reg_password")
                submitted = st.form_submit_button("Create Account →", use_container_width=True)
                if submitted:
                    if not username or not email or not password:
                        st.session_state.auth_error = "Please fill in all fields."
                        st.rerun()
                    elif len(password) < 6:
                        st.session_state.auth_error = "Password must be at least 6 characters."
                        st.rerun()
                    elif "@" not in email:
                        st.session_state.auth_error = "Please enter a valid email address."
                        st.rerun()
                    elif _do_register(username.strip(), email.strip(), password):
                        st.rerun()
                    else:
                        st.rerun()

            st.markdown(
                "<div style='text-align:center;color:#64748B;font-size:0.8rem;margin-top:20px;'>"
                "Already have an account? Click <strong>Login</strong> above.</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div style='text-align:center;color:#475569;font-size:0.7rem;margin-top:32px;'>"
            "Powered by FastAPI + Streamlit · CareerLens © 2026</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Auth gate — show login page if not authenticated
# ---------------------------------------------------------------------------
if not st.session_state.authenticated:
    _render_auth_page()
    st.stop()  # halt rendering of any further content


# ---------------------------------------------------------------------------
# Sidebar — shown only when authenticated
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-logo-text">🌐 CareerLens</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.8rem; color: var(--color-text-secondary); font-weight: 500; margin-top: -6px; margin-bottom: 12px;">Global Job Market Intelligence</div>', unsafe_allow_html=True)

    # User badge + logout
    _role_color = "#4F46E5" if st.session_state.role == "admin" else "#0D9488"
    _role_label = "🛡️ Admin" if st.session_state.role == "admin" else "👤 User"
    st.markdown(
        f"""
        <div style="background:rgba(21,18,31,0.9);border:1px solid rgba(139,92,246,0.2);
                    border-radius:10px;padding:10px 14px;margin-bottom:14px;display:flex;
                    align-items:center;gap:10px;justify-content:space-between;">
            <div>
                <div style="font-size:0.8rem;font-weight:700;color:#F8FAFC;">{st.session_state.username}</div>
                <div style="font-size:0.7rem;font-weight:600;color:{_role_color};margin-top:2px;">{_role_label}</div>
            </div>
            <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#4F46E5,#7C3AED);
                        display:flex;align-items:center;justify-content:center;font-size:1rem;">
                {"🛡️" if st.session_state.role == "admin" else "👤"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🚪 Logout", use_container_width=True):
        _do_logout()
        st.rerun()

    st.divider()

    st.markdown("### 🔧 Filters")
    top_n = st.slider("Top N results", min_value=5, max_value=50, value=15, step=5)
    seniority_filter = st.selectbox("Seniority Level", ["All", "Junior", "Mid-level", "Senior", "Lead"])
    min_salary_filter = st.number_input("Min Salary (USD)", min_value=0, value=0, step=10000)
    st.caption("_Filters apply to Browse Jobs, Data Quality & Email Alerts pages._")
    st.divider()

    st.markdown("### 📑 Navigation")
    _nav_options = [
        "📊 Overview",
        "🔍 Data Quality",
        "🌍 Countries",
        "🛠️ Skills",
        "💼 Roles",
        "📈 Time Trends",
        "💸 Salary Analysis",
        "🧠 Resume Matcher",
        "📧 Email Alerts",
        "🗂️ Browse Jobs",
        "🔖 Bookmarks",
    ]
    if st.session_state.role == "admin":
        _nav_options.append("🛡️ Admin Panel")

    page = st.radio(
        "View",
        options=_nav_options,
        label_visibility="collapsed",
    )
    st.divider()


    st.markdown("### 🔌 Connection Mode")
    live_mode = st.checkbox(
        "Connect to Live API",
        value=not st.session_state.api_fallback,
        help="Check this to connect to the local API server running on port 8000. Uncheck to run in offline Kaggle fallback mode."
    )
    if live_mode and st.session_state.api_fallback:
        st.session_state.api_fallback = False
        st.rerun()
    elif not live_mode and not st.session_state.api_fallback:
        st.session_state.api_fallback = True
        st.rerun()

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

    if st.session_state.api_fallback:
        st.markdown(
            """
            <div style="background-color: rgba(245, 158, 11, 0.1); color: #FBBF24; font-size: 0.72rem; padding: 10px; border-radius: 8px; border: 1px solid rgba(245, 158, 11, 0.2); text-align: center; font-weight: 600; margin-bottom: 12px; margin-top: 12px;">
                🔌 Offline Fallback Mode<br>
                <span style="font-size: 0.65rem; opacity: 0.8; font-weight: 400;">Serving pre-loaded Kaggle dataset</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        "<div style='color:var(--color-text-muted);font-size:0.7rem;text-align:center;margin-top:12px;'>"
        "Powered by Remotive API · Built with FastAPI + Streamlit"
        "</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Fetch stats upfront (lightweight, always needed for KPIs and source list)
# Other data is fetched lazily per page to avoid slow navigation.
# ---------------------------------------------------------------------------
try:
    _fallback_flag = st.session_state.get("api_fallback", True)
    # Auto-recovery: if in fallback but running locally, try to reconnect
    if _fallback_flag and ("localhost" in BASE or "127.0.0.1" in BASE):
        try:
            _real_requests.get(f"{BASE}/api/v1/stats", timeout=3.0)
            st.session_state.api_fallback = False
            _fallback_flag = False
            st.toast("🔌 Reconnected to local CareerLens API backend!", icon="✅")
        except Exception:
            pass
    stats = _fetch_stats(_fallback=_fallback_flag)
except requests.RequestException as exc:
    st.error(f"❌ Cannot reach the CareerLens API at **{BASE}**")
    st.code(str(exc))
    st.info("Make sure the API is running: `uvicorn src.serving.api.main:app --reload`")
    st.stop()

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _apply_layout(fig: go.Figure, **kwargs) -> go.Figure:
    layout = dict(_CHART_LAYOUT)
    for key, val in kwargs.items():
        if key in layout and isinstance(layout[key], dict) and isinstance(val, dict):
            layout[key] = {**layout[key], **val}
        else:
            layout[key] = val
    fig.update_layout(**layout)
    return fig


def _empty_chart(title: str) -> None:
    st.info(f"No data available for **{title}**. Run the pipeline to ingest some jobs.")


_ICON_JOBS = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>"""
_ICON_COUNTRIES = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>"""
_ICON_SKILLS = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>"""
_ICON_EARLIEST = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>"""
_ICON_LATEST = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line><path d="M12 14l2 2 4-4"></path></svg>"""

def _top_navbar(title: str = "CareerLens") -> None:
    st.markdown(
        f'<div class="top-navbar">'
        f'  <div class="nav-brand">'
        f'    <div class="nav-logo-wrap">'
        f'      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>'
        f'    </div>'
        f'    <span class="nav-title">{title}</span>'
        f'  </div>'
        f'  <div class="nav-actions">'
        f'    <span class="nav-badge">SaaS Analytics v2.0</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def _render_header(page_title: str, subtitle: str = "") -> None:
    _top_navbar()
    import re
    emoji = ""
    text = page_title
    match = re.match(r"^([\u2600-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF])\s*(.*)$", page_title)
    if match:
        emoji = match.group(1)
        text = match.group(2)
    
    badge_html = f'<div class="header-icon-badge">{emoji if emoji else "✨"}</div>'

    st.markdown(
        f'<div class="page-header-area">'
        f'  <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 8px;">'
        f'    {badge_html}'
        f'    <h1 class="page-title" style="margin: 0 !important; padding: 0 !important; display: inline-block;">{text}</h1>'
        f'    <span class="title-link-icon">'
        f'      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>'
        f'    </span>'
        f'  </div>'
        f'  {f"<p class=\'page-subtitle\'>{subtitle}</p>" if subtitle else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )

def _kpi(col, number: str | int, label: str, icon_svg: str = "", badge_bg: str = "#EEF2F6", icon_color: str = "#4B5563") -> None:
    is_real_svg = icon_svg and icon_svg.strip().startswith("<svg")
    lbl_lower = label.lower()
    
    if is_real_svg:
        svg_content = icon_svg
    elif "job" in lbl_lower:
        svg_content = _ICON_JOBS
    elif "countr" in lbl_lower:
        svg_content = _ICON_COUNTRIES
    elif "skill" in lbl_lower:
        svg_content = _ICON_SKILLS
    elif "earliest" in lbl_lower:
        svg_content = _ICON_EARLIEST
    elif "latest" in lbl_lower:
        svg_content = _ICON_LATEST
    elif "salary" in lbl_lower or "pay" in lbl_lower:
        svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>"""
    elif "peak" in lbl_lower or "month" in lbl_lower or "trend" in lbl_lower:
        svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>"""
    else:
        svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>"""

    gradient_class = "gradient-primary-theme"
    if any(k in lbl_lower for k in ["countr", "latest", "peak", "average", "fill", "salary", "pay"]):
        gradient_class = "gradient-secondary-theme"
        
    badge_html = f'<div class="kpi-icon-badge-wrap">{svg_content}</div>'

    col.markdown(
        f'<div class="kpi-card {gradient_class}">'
        f'  <div class="kpi-header-row">'
        f'    {badge_html}'
        f'    <div class="kpi-label">{label}</div>'
        f'  </div>'
        f'  <div class="kpi-number">{number}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# ══════════════════════════  PAGES  ══════════════════════════
# ---------------------------------------------------------------------------

# ---- Overview ----------------------------------------------------------------
if page == "📊 Overview":
    _render_header(
        "📊 CareerLens Overview",
        "Near-real-time snapshot of the global remote job market. Pipeline runs every 5 minutes; dashboard cache refreshes every 60 seconds."
    )

    # Lazily fetch only the data required for Overview page
    countries_df = _safe_fetch("/api/v1/trends/countries")
    skills_df = _safe_fetch("/api/v1/trends/skills")

    # Pipeline health — inline status toolbar
    dead = stats.get("total_dead_letters", 0)
    sources = stats.get("sources", [])
    pill_class = "pill-ok" if dead == 0 else "pill-warn"
    status_text = "Clean" if dead == 0 else f"{dead} unresolved"
    source_pills_html = "".join(
        f'<span class="source-pill">{s}</span>'
        for s in sources
    )
    st.markdown(
        f'<div class="status-toolbar">'
        f'  <div style="display:flex;align-items:center;gap:8px;">'
        f'    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
        f'    <span style="font-size:0.82rem;font-weight:600;color:#334155;">Dead-letter queue</span>'
        f'    <span class="{pill_class}">{status_text}</span>'
        f'  </div>'
        f'  <div style="width:1px;height:16px;background:#e5e7eb;"></div>'
        f'  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
        f'    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path><line x1="4" y1="22" x2="4" y2="15"></line></svg>'
        f'    <span style="font-size:0.82rem;font-weight:600;color:#334155;">Active Sources</span>'
        f'    {source_pills_html}'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # KPI row — icon badge variant
    c1, c2, c3, c4, c5 = st.columns(5)
    _kpi(c1, f"{stats.get('total_jobs', 0):,}", "Total Jobs", _ICON_JOBS, "rgba(79,70,229,0.08)", "#4F46E5")
    _kpi(c2, f"{stats.get('total_countries', 0):,}", "Countries", _ICON_COUNTRIES, "rgba(16,185,129,0.08)", "#10B981")
    _kpi(c3, f"{stats.get('total_skills', 0):,}", "Skills", _ICON_SKILLS, "rgba(139,92,246,0.08)", "#8B5CF6")
    _kpi(c4, stats.get("earliest_job", "—") or "—", "Earliest Job", _ICON_EARLIEST, "rgba(245,158,11,0.08)", "#F59E0B")
    _kpi(c5, stats.get("latest_job", "—") or "—", "Latest Job", _ICON_LATEST, "rgba(236,72,153,0.08)", "#EC4899")

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick charts: top countries + top skills side by side
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section-header">Top Countries</div>', unsafe_allow_html=True)
        if not countries_df.empty:
            top_c = countries_df.groupby("country")["job_count"].sum().nlargest(top_n).reset_index()
            top_c = top_c.sort_values("job_count", ascending=False)
            n = len(top_c)
            indigo_scale = ["#4F46E5", "#7C3AED"]
            fig = px.bar(
                top_c,
                x="job_count",
                y="country",
                orientation="h",
                color="job_count",
                color_continuous_scale=indigo_scale,
                template=_PLOTLY_THEME,
                labels={"job_count": "", "country": ""},
                text="job_count",
            )
            fig.update_traces(
                texttemplate="%{text:,}",
                textposition="outside",
                textfont=dict(size=11, color="#FFFFFF", family="Inter, sans-serif"),
                marker_line_width=0,
            )
            fig.update_coloraxes(showscale=False)
            _apply_layout(fig,
                yaxis={"categoryorder": "total ascending", "showgrid": False},
                xaxis={"showgrid": False, "showticklabels": False, "zeroline": False},
                margin=dict(l=8, r=64, t=24, b=8),
            )
            st.plotly_chart(fig, theme=None, use_container_width=True)
        else:
            _empty_chart("Countries")

    with right:
        st.markdown('<div class="section-header">Top Skills</div>', unsafe_allow_html=True)
        if not skills_df.empty:
            top_s = skills_df.groupby("skill")["job_count"].sum().nlargest(top_n).reset_index()
            top_s = top_s.sort_values("job_count", ascending=False)
            teal_scale = ["#2563EB", "#06B6D4"]
            fig = px.bar(
                top_s,
                x="job_count",
                y="skill",
                orientation="h",
                color="job_count",
                color_continuous_scale=teal_scale,
                template=_PLOTLY_THEME,
                labels={"job_count": "", "skill": ""},
                text="job_count",
            )
            fig.update_traces(
                texttemplate="%{text:,}",
                textposition="outside",
                textfont=dict(size=11, color="#FFFFFF", family="Inter, sans-serif"),
                marker_line_width=0,
            )
            fig.update_coloraxes(showscale=False)
            _apply_layout(fig,
                yaxis={"categoryorder": "total ascending", "showgrid": False},
                xaxis={"showgrid": False, "showticklabels": False, "zeroline": False},
                margin=dict(l=8, r=64, t=24, b=8),
            )
            st.plotly_chart(fig, theme=None, use_container_width=True)
        else:
            _empty_chart("Skills")

# ---- Countries ---------------------------------------------------------------
elif page == "🌍 Countries":
    _render_header(
        "🌍 Countries",
        "Regional breakdown of remote job postings across the global market."
    )

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
        _apply_layout(fig_map, geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False))
        st.plotly_chart(fig_map, theme=None, use_container_width=True)

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
            _apply_layout(fig, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True))
            st.plotly_chart(fig, theme=None, use_container_width=True)

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
    _render_header(
        "🛠️ Skills",
        "Technology skill demand trends extracted from live remote job postings."
    )

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
        _apply_layout(fig_tree)
        st.plotly_chart(fig_tree, theme=None, use_container_width=True)

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
            _apply_layout(fig, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True))
            st.plotly_chart(fig, theme=None, use_container_width=True)

# ---- Roles -------------------------------------------------------------------
elif page == "💼 Roles":
    _render_header(
        "💼 Roles",
        "Breakdown of the most in-demand job roles in the remote job market."
    )

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
        _apply_layout(fig, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, theme=None, use_container_width=True)

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
            _apply_layout(fig_hm)
            st.plotly_chart(fig_hm, theme=None, use_container_width=True)

# ---- Time Trends -------------------------------------------------------------
elif page == "📈 Time Trends":
    _render_header(
        "📈 Time Trends",
        "Monthly hiring velocity and historical volume of remote job postings over time."
    )

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
                marker=dict(size=8, color=_ACCENT, line=dict(width=2, color="#ffffff")),
                fill="tozeroy",
                fillcolor="rgba(37,99,235,0.08)",
                text=time_df["job_count"],
                textposition="top center",
                textfont=dict(size=10, color="#FFFFFF"),
            )
        )
        _apply_layout(
            fig,
            xaxis_title="Month",
            yaxis_title="Job Count",
            showlegend=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True),
        )
        st.plotly_chart(fig, theme=None, use_container_width=True)

        st.divider()

        # Stats
        total = int(time_df["job_count"].sum())
        peak_row = time_df.loc[time_df["job_count"].idxmax()]
        c1, c2, c3 = st.columns(3)
        _kpi(c1, f"{total:,}", "Total Jobs (all time)", "#3b82f6")
        _kpi(c2, str(peak_row["published_month"]), "Peak Month", "#8b5cf6")
        _kpi(c3, f"{int(peak_row['job_count']):,}", "Peak Month Jobs", "#ec4899")

# ---- Salary Analysis ---------------------------------------------------------
elif page == "💸 Salary Analysis":
    _render_header(
        "💸 Salary Analysis",
        "Dynamic salary aggregation and market intelligence parsed directly from our job trends database."
    )
    st.markdown("") 

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

        _kpi(c1, f"{selected_currency} {int(avg_sal_role):,}", "Average Role Salary", "#3b82f6")
        _kpi(c2, f"{highest_paying_role}", f"Top Role ({selected_currency} {int(highest_paying_val):,})", "#10b981")
        _kpi(c3, f"{int(total_sal_jobs):,}", "Jobs Analysed", "#8b5cf6")

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
            _apply_layout(fig_role, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_role, theme=None, use_container_width=True)

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
                _apply_layout(fig_country, yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig_country, theme=None, use_container_width=True)
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
    _render_header(
        "🧠 Resume Matcher",
        "Provide your resume or skills. Gemini AI will build a professional summary, extract key skills, suggest roles, and recommend the best-matching remote jobs."
    )
    st.markdown("") 

    # Two input methods: File Uploader or Text Area
    st.markdown("### 📤 Input Method")
    input_method = st.radio("Choose how to provide your profile:", ["Upload Resume (PDF)", "Paste Resume Text"], horizontal=True)

    resume_text = ""

    if input_method == "Upload Resume (PDF)":
        uploaded_file = st.file_uploader("Upload your resume in PDF format:", type=["pdf"])
        if uploaded_file is not None:
            with st.spinner("📄 Reading PDF resume..."):
                try:
                    import pypdf
                    reader = pypdf.PdfReader(uploaded_file)
                    extracted_text_list = []
                    for page_num in range(len(reader.pages)):
                        text = reader.pages[page_num].extract_text()
                        if text:
                            extracted_text_list.append(text)
                    resume_text = "\n".join(extracted_text_list).strip()
                    if resume_text:
                        st.success(f"Successfully extracted {len(resume_text)} characters of text from '{uploaded_file.name}'!")
                        with st.expander("🔍 Preview Extracted Text"):
                            st.text(resume_text[:600] + "...")
                    else:
                        st.error("No text could be extracted from this PDF. Please check if it is scanned or use the text area method.")
                except Exception as e:
                    st.error(f"Error parsing PDF: {e}")
    else:
        resume_text = st.text_area(
            "Paste your resume or skills details below:",
            placeholder="e.g. Senior Data Engineer with 5 years experience in Python, PostgreSQL, AWS, Apache Spark, Airflow, and building data pipelines.",
            height=150,
        ).strip()

    if resume_text:
        if len(resume_text) < 10:
            st.warning("Please provide a longer description (at least 10 characters).")
        else:
            with st.spinner("🧠 Gemini AI is analysing your resume..."):
                payload = {
                    "resume_text": resume_text,
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
                            <div style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); border: none; border-radius: 12px; padding: 20px; box-shadow: var(--shadow-card); margin-bottom: 24px;">
                                <p style="font-size: 1.05rem; line-height: 1.6; color: #ffffff; font-style: italic; margin: 0; font-weight: 500;">
                                    "{result['ai_summary']}"
                                </p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        # Render extracted skills
                        st.subheader("🛠️ Extracted Technical Skills")
                        skills_html = "".join(
                            f'<span style="background-color: rgba(139, 92, 246, 0.15); color: #C4B5FD; font-weight: 600; font-size: 0.85rem; padding: 4px 12px; border-radius: 16px; margin-right: 8px; margin-bottom: 8px; display: inline-block; border: 1px solid rgba(139, 92, 246, 0.30);">{s}</span>'
                            for s in result["extracted_skills"]
                        )
                        st.markdown(skills_html, unsafe_allow_html=True)
                        st.write("")

                        # Render recommended roles if any
                        if result.get("recommended_roles"):
                            st.subheader("💼 Recommended Positions")
                            roles_html = "".join(
                                f'<span style="background-color: rgba(245, 158, 11, 0.08); color: #D97706; font-weight: 600; font-size: 0.85rem; padding: 4px 12px; border-radius: 16px; margin-right: 8px; margin-bottom: 8px; display: inline-block; border: 1px solid rgba(245, 158, 11, 0.18);">{r}</span>'
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

                                match_score = job.get("match_score", 0)
                                if match_score >= 75:
                                    score_color = "#10b981"  # green
                                    score_bg = "rgba(16, 185, 129, 0.08)"
                                    score_border = "rgba(16, 185, 129, 0.18)"
                                elif match_score >= 40:
                                    score_color = "#f59e0b"  # orange
                                    score_bg = "rgba(245, 158, 11, 0.08)"
                                    score_border = "rgba(245, 158, 11, 0.18)"
                                else:
                                    score_color = "#ef4444"  # red
                                    score_bg = "rgba(239, 68, 68, 0.08)"
                                    score_border = "rgba(239, 68, 68, 0.18)"

                                with st.container():
                                    st.markdown(
                                        f"""
                                        <div class="premium-card">
                                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                                                <h4 style="margin: 0; font-size: 1.1rem; color: #F8FAFC;"><a href="{url}" target="_blank" style="color: #818CF8; text-decoration: none; font-weight: 700;">{title}</a></h4>
                                                <div>
                                                    <span style="background-color: {score_bg}; color: {score_color}; font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; font-weight: 700; border: 1px solid {score_border}; margin-right: 6px;">🎯 {match_score}% MATCH</span>
                                                    <span style="background-color: rgba(6, 182, 212, 0.12); color: #22D3EE; font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; font-weight: 600; text-transform: uppercase; border: 1px solid rgba(6, 182, 212, 0.25);">{source}</span>
                                                    <span style="background-color: rgba(245, 158, 11, 0.12); color: #FCD34D; font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; font-weight: 600; text-transform: uppercase; margin-left: 6px; border: 1px solid rgba(245, 158, 11, 0.25);">{seniority}</span>
                                                </div>
                                            </div>
                                            <div style="color: #CBD5E1; font-weight: 600; font-size: 0.95rem; margin-top: 6px;">{company}</div>
                                            <div style="color: #94A3B8; font-size: 0.8rem; margin-top: 8px;">
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
    _render_header(
        "📧 Email Alerts",
        "Set up a customized daily email digest of newly ingested remote jobs matching your skills."
    )
    st.markdown("") 

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
            _preview_params = {"page_size": 100}
            if seniority_filter != "All":
                _preview_params["seniority"] = seniority_filter
            if min_salary_filter > 0:
                _preview_params["min_salary"] = min_salary_filter
            preview_jobs_df = _safe_fetch("/api/v1/jobs", _preview_params)
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
    _render_header(
        "🗂️ Browse Jobs",
        "Raw bronze-layer job records from the ingestion pipeline."
    )

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
        # Only show columns that actually exist in the dataframe
        desired_cols = ["id", "title", "company_name", "country", "seniority",
                        "salary_min", "salary_max", "salary_currency",
                        "source", "publication_date", "url"]
        show_cols = [c for c in desired_cols if c in display_df.columns]
        st.dataframe(
            display_df[show_cols],
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


# ---- Data Quality Page --------------------------------------------------------
elif page == "🔍 Data Quality":
    _render_header(
        "🔍 Data Quality",
        "A live observability and auditing dashboard checking data completeness and schema integrity. Evaluates the 200 most recent ingested job postings."
    )

    # Fetch jobs with active sidebar filters
    _dq_params = {"page_size": 200}
    if seniority_filter != "All":
        _dq_params["seniority"] = seniority_filter
    if min_salary_filter > 0:
        _dq_params["min_salary"] = min_salary_filter
    dq_df = _safe_fetch("/api/v1/jobs", _dq_params)

    if dq_df.empty:
        st.warning("No job records found to analyze. Run the ingestion pipeline first!")
    else:
        # 1. Calculate metrics
        total_analyzed = len(dq_df)
        
        # Location fill rate
        location_filled = dq_df["country"].apply(lambda c: str(c).strip().lower() not in ["unknown", "none", "nan", ""])
        loc_fill_rate = (location_filled.sum() / total_analyzed) * 100
        
        # Salary fill rate
        salary_filled = dq_df["salary_min"].notna() & dq_df["salary_max"].notna()
        salary_fill_rate = (salary_filled.sum() / total_analyzed) * 100
        
        # Tags fill rate
        tags_filled = dq_df["tags"].apply(lambda t: isinstance(t, list) and len(t) > 0)
        tags_fill_rate = (tags_filled.sum() / total_analyzed) * 100
        
        # Average tags per job
        avg_tags = dq_df["tags"].apply(lambda t: len(t) if isinstance(t, list) else 0).mean()

        # Render KPI Cards
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        _kpi(col_m1, f"{total_analyzed}", "Analyzed Jobs", "#3b82f6")
        _kpi(col_m2, f"{loc_fill_rate:.1f}%", "Location Fill Rate", "#10b981")
        _kpi(col_m3, f"{salary_fill_rate:.1f}%", "Salary Fill Rate", "#f59e0b")
        _kpi(col_m4, f"{avg_tags:.1f}", "Avg Tags / Job", "#8b5cf6")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Quality distribution details
        st.markdown('<div class="section-header">Data Completeness Audit</div>', unsafe_allow_html=True)
        left_dq, right_dq = st.columns(2)
        
        with left_dq:
            st.markdown("#### Schema Nullability Metrics")
            # Create nullability dataframe
            nullability_data = {
                "Field": ["Salary Info", "Country / Location", "Skill Tags", "Company Name", "Job URL", "Job Category"],
                "Completeness %": [
                    salary_fill_rate,
                    loc_fill_rate,
                    tags_fill_rate,
                    (dq_df["company_name"].notna().sum() / total_analyzed) * 100,
                    (dq_df["url"].notna().sum() / total_analyzed) * 100 if "url" in dq_df.columns else 0,
                    (dq_df["category"].apply(lambda x: str(x).strip().lower() not in ["none", "nan", "unknown", ""]).sum() / total_analyzed) * 100 if "category" in dq_df.columns else 0
                ]
            }
            null_df = pd.DataFrame(nullability_data)
            fig_null = px.bar(
                null_df,
                x="Completeness %",
                y="Field",
                orientation="h",
                text="Completeness %",
                color="Completeness %",
                color_continuous_scale="Blues",
                template=_PLOTLY_THEME
            )
            fig_null.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            _apply_layout(fig_null, yaxis={"categoryorder": "total ascending"})
            fig_null.update_coloraxes(showscale=False)
            st.plotly_chart(fig_null, theme=None, use_container_width=True)

        with right_dq:
            st.markdown("#### Ingestion Sources Distribution")
            source_counts = dq_df["source"].value_counts().reset_index()
            source_counts.columns = ["source", "count"]
            fig_source = px.pie(
                source_counts,
                names="source",
                values="count",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Blues_r,
                template=_PLOTLY_THEME
            )
            _apply_layout(fig_source)
            st.plotly_chart(fig_source, theme=None, use_container_width=True)

        st.divider()

        # Detailed Seniority vs Salary quality analysis
        left_sal, right_sal = st.columns(2)
        with left_sal:
            st.markdown('<div class="section-header">Seniority Tag Distribution</div>', unsafe_allow_html=True)
            seniority_counts = dq_df["seniority"].value_counts().reset_index()
            seniority_counts.columns = ["seniority", "count"]
            fig_sen = px.bar(
                seniority_counts,
                x="seniority",
                y="count",
                color="count",
                color_continuous_scale="Blues",
                template=_PLOTLY_THEME,
                labels={"count": "Job Postings", "seniority": "Seniority Level"}
            )
            _apply_layout(fig_sen, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True))
            fig_sen.update_coloraxes(showscale=False)
            st.plotly_chart(fig_sen, theme=None, use_container_width=True)
            
        with right_sal:
            st.markdown('<div class="section-header">Salary Range Data Integrity</div>', unsafe_allow_html=True)
            valid_sal_df = dq_df[dq_df["salary_min"].notna() & dq_df["salary_max"].notna()]
            if not valid_sal_df.empty:
                fig_scatter = px.scatter(
                    valid_sal_df,
                    x="salary_min",
                    y="salary_max",
                    color="seniority",
                    hover_data=["title", "company_name"],
                    template=_PLOTLY_THEME,
                    labels={"salary_min": "Minimum Salary (USD)", "salary_max": "Maximum Salary (USD)"}
                )
                _apply_layout(fig_scatter, xaxis=dict(showgrid=True), yaxis=dict(showgrid=True))
                st.plotly_chart(fig_scatter, theme=None, use_container_width=True)
            else:
                st.info("No salary details available in the current batch to plot salary range integrity.")


# ---- Bookmarks Page -----------------------------------------------------------
elif page == "🔖 Bookmarks":
    _render_header(
        "🔖 Bookmarks",
        "Your saved remote job opportunities with personal notes."
    )

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
                    <div class="premium-card">
                        <span style="background-color: rgba(139,92,246,0.15); color: #C4B5FD; font-size: 0.7rem; font-weight: 700; padding: 2px 8px; border-radius: 12px; margin-right: 8px; border: 1px solid rgba(139,92,246,0.30);">ID: {job_id}</span>
                        <span style="background-color: rgba(6,182,212,0.12); color: #22D3EE; font-size: 0.7rem; font-weight: 600; padding: 2px 8px; border-radius: 12px; border: 1px solid rgba(6,182,212,0.25);">{source}</span>
                        <h3 style="margin: 10px 0 2px 0; color: #F8FAFC;"><a href="{url}" target="_blank" style="color: #818CF8; text-decoration: none; font-weight: 700;">{title}</a></h3>
                        <div style="color: #CBD5E1; font-weight: 600; font-size: 0.9rem; margin-bottom: 6px;">{company}</div>
                        <div style="font-size: 0.75rem; color: #94A3B8; margin-bottom: 4px;">Saved on {bookmarked_at}</div>
                        {f'<div style="font-size: 0.82rem; color: #CBD5E1; margin-top: 6px; padding: 6px 10px; background: rgba(139,92,246,0.08); border-radius: 6px; border-left: 3px solid #8B5CF6;">📝 {notes}</div>' if notes else ''}
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
                
                st.markdown("<hr style='margin: 16px 0; border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(79,70,229,0.15), transparent);'>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 🛡️ Admin Panel
# ---------------------------------------------------------------------------
elif page == "🛡️ Admin Panel":
    if st.session_state.role != "admin":
        st.error("🚫 Access denied. This page requires administrator privileges.")
        st.stop()

    st.markdown(
        """
        <div class="page-header-area">
            <div style="display:flex;align-items:center;gap:14px;">
                <div class="header-icon-badge">🛡️</div>
                <div>
                    <div class="page-title">Admin Panel</div>
                    <div class="page-subtitle">Manage user accounts, roles, and system operations.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Fetch users list from API ──
    import requests as _admin_req
    _auth_headers = {"Authorization": f"Bearer {st.session_state.token}"}

    def _admin_get_users():
        if st.session_state.api_fallback:
            return [
                {
                    "id": i + 1,
                    "username": uname,
                    "email": uinfo["email"],
                    "role": uinfo["role"],
                    "is_active": uinfo.get("is_active", True),
                    "created_at": "2026-07-10T00:00:00"
                }
                for i, (uname, uinfo) in enumerate(st.session_state.local_users.items())
            ]
        try:
            r = _admin_req.get(f"{BASE}/admin/users", headers=_auth_headers, timeout=10)
            if r.status_code == 200:
                return r.json()
            st.error(f"Could not fetch users: {r.json().get('detail', r.status_code)}")
        except Exception as exc:
            st.error(f"API error: {exc}")
        return []

    users_list = _admin_get_users()

    # ── KPI row ──
    col1, col2, col3 = st.columns(3)
    total_users = len(users_list)
    admin_count = sum(1 for u in users_list if u["role"] == "admin")
    active_count = sum(1 for u in users_list if u["is_active"])

    with col1:
        st.markdown(
            f"""<div class="kpi-card gradient-primary-theme">
                <div class="kpi-header-row"><div class="kpi-icon-badge-wrap"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg></div>
                <span class="kpi-label">Total Users</span></div>
                <div class="kpi-number">{total_users}</div></div>""",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""<div class="kpi-card gradient-secondary-theme">
                <div class="kpi-header-row"><div class="kpi-icon-badge-wrap"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div>
                <span class="kpi-label">Admins</span></div>
                <div class="kpi-number">{admin_count}</div></div>""",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""<div class="kpi-card gradient-primary-theme">
                <div class="kpi-header-row"><div class="kpi-icon-badge-wrap"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg></div>
                <span class="kpi-label">Active Accounts</span></div>
                <div class="kpi-number">{active_count}</div></div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── User management table ──
    st.markdown("### 👥 User Accounts")
    if not users_list:
        st.info("No users found.")
    else:
        for u in users_list:
            uid = u["id"]
            uname = u["username"]
            uemail = u["email"]
            urole = u["role"]
            uactive = u["is_active"]
            ucreated = u["created_at"][:10]
            is_self = uname == st.session_state.username

            role_badge_color = "#4F46E5" if urole == "admin" else "#0D9488"
            active_badge = (
                '<span style="background:rgba(16,185,129,0.12);color:#10B981;border:1px solid rgba(16,185,129,0.25);'
                'border-radius:12px;padding:2px 10px;font-size:0.72rem;font-weight:700;">✓ Active</span>'
                if uactive else
                '<span style="background:rgba(239,68,68,0.1);color:#F87171;border:1px solid rgba(239,68,68,0.25);'
                'border-radius:12px;padding:2px 10px;font-size:0.72rem;font-weight:700;">✗ Inactive</span>'
            )

            with st.container():
                st.markdown(
                    f"""
                    <div class="premium-card" style="margin-bottom:8px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
                            <div>
                                <span style="font-size:1rem;font-weight:800;color:#F8FAFC;">
                                    {"🛡️" if urole == "admin" else "👤"} {uname}
                                    {"<span style='font-size:0.7rem;color:#94A3B8;margin-left:6px;'>(you)</span>" if is_self else ""}
                                </span>
                                <span style="font-size:0.75rem;color:#94A3B8;margin-left:12px;">{uemail}</span>
                            </div>
                            <div style="display:flex;align-items:center;gap:8px;">
                                <span style="background:rgba({('79,70,229' if urole == 'admin' else '13,148,136')},0.12);
                                    color:{role_badge_color};border:1px solid rgba({('79,70,229' if urole == 'admin' else '13,148,136')},0.3);
                                    border-radius:12px;padding:2px 12px;font-size:0.72rem;font-weight:700;">
                                    {urole.upper()}
                                </span>
                                {active_badge}
                                <span style="font-size:0.72rem;color:#64748B;">Joined {ucreated}</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if not is_self:
                    btn_col1, btn_col2, _ = st.columns([2, 2, 6])
                    with btn_col1:
                        new_role = "user" if urole == "admin" else "admin"
                        btn_label = f"⬆️ Make Admin" if urole == "user" else "⬇️ Make User"
                        if st.button(btn_label, key=f"role_{uid}", use_container_width=True):
                            if st.session_state.api_fallback:
                                if uname in st.session_state.local_users:
                                    st.session_state.local_users[uname]["role"] = new_role
                                    st.success(f"Role updated to {new_role}! (offline)")
                                    st.rerun()
                            else:
                                try:
                                    resp = _admin_req.put(
                                        f"{BASE}/admin/users/{uid}/role",
                                        json={"role": new_role},
                                        headers=_auth_headers,
                                        timeout=10,
                                    )
                                    if resp.status_code == 200:
                                        st.success(f"Role updated to {new_role}!")
                                        st.rerun()
                                    else:
                                        st.error(resp.json().get("detail", "Failed"))
                                except Exception as exc:
                                    st.error(f"Error: {exc}")
                    with btn_col2:
                        toggle_label = "🔴 Deactivate" if uactive else "🟢 Activate"
                        if st.button(toggle_label, key=f"toggle_{uid}", use_container_width=True):
                            if st.session_state.api_fallback:
                                if uname in st.session_state.local_users:
                                    st.session_state.local_users[uname]["is_active"] = not uactive
                                    status_str = "deactivated" if uactive else "activated"
                                    st.success(f"User {uname} {status_str}! (offline)")
                                    st.rerun()
                            else:
                                try:
                                    resp = _admin_req.put(
                                        f"{BASE}/admin/users/{uid}/toggle",
                                        headers=_auth_headers,
                                        timeout=10,
                                    )
                                    if resp.status_code == 200:
                                        status_str = "deactivated" if uactive else "activated"
                                        st.success(f"User {uname} {status_str}.")
                                        st.rerun()
                                    else:
                                        st.error(resp.json().get("detail", "Failed"))
                                except Exception as exc:
                                    st.error(f"Error: {exc}")


                st.markdown(
                    "<div style='height:4px'></div>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── System Operations ──
    st.markdown("### ⚙️ System Operations")
    op_col1, op_col2 = st.columns(2)
    with op_col1:
        st.markdown(
            """<div class="premium-card">
                <div style="font-size:0.8rem;font-weight:700;color:#F8FAFC;margin-bottom:6px;">📧 Email Alert Cycle</div>
                <div style="font-size:0.78rem;color:#94A3B8;margin-bottom:12px;">
                    Manually trigger the daily job-alert digest to all active subscribers.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("🚀 Trigger Email Alerts", use_container_width=True):
            try:
                resp = _admin_req.post(
                    f"{BASE}/api/v1/subscriptions/trigger?force=true",
                    headers=_auth_headers,
                    timeout=20,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"✅ {data.get('message', 'Alerts sent!')}")
                else:
                    st.error(f"Error: {resp.json().get('detail', resp.status_code)}")
            except Exception as exc:
                st.error(f"Error: {exc}")
    with op_col2:
        st.markdown(
            """<div class="premium-card">
                <div style="font-size:0.8rem;font-weight:700;color:#F8FAFC;margin-bottom:6px;">🔄 API Health Check</div>
                <div style="font-size:0.78rem;color:#94A3B8;margin-bottom:12px;">
                    Verify the FastAPI backend is reachable and responding correctly.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("🔍 Check API Health", use_container_width=True):
            try:
                resp = _admin_req.get(f"{BASE}/health", timeout=5)
                if resp.status_code == 200:
                    st.success("✅ API is healthy and responding!")
                else:
                    st.warning(f"API returned status {resp.status_code}")
            except Exception as exc:
                st.error(f"API unreachable: {exc}")


# ---------------------------------------------------------------------------
# Auto-refresh — non-blocking refresh using streamlit-autorefresh
# ---------------------------------------------------------------------------
if auto_refresh:
    st_autorefresh(interval=60000, key="auto_refresh_timer")
