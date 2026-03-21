"""AgroShield UI mockup with data-backed states that mirror the Stitch references."""

from __future__ import annotations

import html
import math
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "03_scoring"))

from components.pipeline import load_pathogen_map, load_precomputed_results, load_reference_amps, run_full_pipeline
from components.structure import sequence_annotation, sequence_legend
from scripts.properties import compute_all_properties


st.set_page_config(
    page_title="AgroShield",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    :root {
        --ink: #171617;
        --canvas: #ffffff;
        --sidebar: #dbe4f0;
        --line: #e8eef5;
        --copy: #6f7d91;
        --copy-soft: #9aa7b8;
        --title: #113a2c;
        --accent: #0c4a34;
        --accent-soft: #c8f2dc;
        --accent-mid: #7dd1ab;
        --panel: #f6f8fb;
        --danger: #eb5757;
        --warn: #d7a114;
        --ok: #2ec28a;
    }

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: var(--ink) !important;
    }

    body, p, span, div, a, li, td, th, label, input, button {
        font-family: "Plus Jakarta Sans", sans-serif !important;
    }

    h1, h2, h3, h4, [data-testid="stMetricValue"] {
        font-family: "Manrope", sans-serif !important;
        color: var(--title) !important;
    }

    #MainMenu, footer, header[data-testid="stHeader"], [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stStatusWidget"], .stDeployButton,
    [data-testid="collapsedControl"] {
        display: none !important;
    }

    button[kind="headerNoPadding"],
    [data-testid="stBaseButton-headerNoPadding"] {
        display: none !important;
    }

    [data-testid="stSidebar"] {
        top: 52px !important;
        left: 18px !important;
        bottom: 18px !important;
        width: 228px !important;
        background: var(--sidebar) !important;
        border-right: none !important;
        border-radius: 18px 0 0 18px !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
    }

    [data-testid="stSidebarContent"] {
        padding: 12px 14px 16px !important;
    }

    [data-testid="stMain"] {
        margin: 52px 18px 18px 54px !important;
        min-height: calc(100vh - 70px);
        background: var(--canvas);
        border-radius: 0 18px 18px 0;
        border: 1px solid rgba(255,255,255,0.06);
        overflow: hidden;
    }

    .stMainBlockContainer {
        max-width: none !important;
        padding: 14px 20px 0 !important;
    }

    .browser-chrome {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 52px;
        background: #1a1719;
        color: #f8fafc;
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 18px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    .chrome-brand {
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: "Manrope", sans-serif;
        font-size: 15px;
        font-weight: 800;
    }

    .chrome-beta {
        border: 1px solid rgba(255,255,255,0.28);
        border-radius: 999px;
        padding: 2px 6px;
        font-size: 8px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.74);
    }

    .chrome-center, .chrome-right {
        display: flex;
        align-items: center;
        gap: 14px;
        color: rgba(255,255,255,0.8);
    }

    .chrome-pill {
        background: #2a69f8;
        color: white;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
    }

    .chrome-share {
        padding: 6px 12px;
        border-radius: 8px;
        background: #f3f4f6;
        color: #3c4043;
        font-size: 12px;
        font-weight: 700;
    }

    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
    }

    .shield-mark {
        width: 28px;
        height: 28px;
        border-radius: 8px;
        background: var(--accent);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 14px;
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.15);
    }

    .sidebar-logo h1 {
        margin: 0;
        font-size: 19px;
        line-height: 1;
        font-weight: 800;
        color: var(--title) !important;
    }

    .sidebar-logo p {
        margin: 4px 0 0;
        font-size: 8px;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: rgba(17,58,44,0.45);
        font-weight: 800;
    }

    .sidebar-kicker {
        margin: 18px 0 6px;
        font-size: 9px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: rgba(17,58,44,0.42);
        font-weight: 800;
    }

    .sidebar-meta {
        margin: 10px 0 16px;
        padding: 12px 14px;
        border-radius: 12px;
        background: rgba(255,255,255,0.33);
        border: 1px solid rgba(255,255,255,0.32);
    }

    .sidebar-meta-row {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 8px;
        font-size: 10px;
    }

    .sidebar-meta-row:last-child {
        margin-bottom: 0;
    }

    .sidebar-meta-label {
        color: rgba(17,58,44,0.5);
        font-weight: 700;
    }

    .sidebar-meta-value {
        color: var(--title);
        font-weight: 800;
        text-align: right;
    }

    .range-card {
        margin: 14px 0 18px;
        padding: 14px;
        border-radius: 14px;
        background: rgba(255,255,255,0.38);
    }

    .range-title {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: rgba(17,58,44,0.58);
        font-weight: 800;
        margin-bottom: 12px;
    }

    .range-track {
        position: relative;
        height: 4px;
        border-radius: 999px;
        background: #c9d5e4;
        overflow: visible;
        margin-bottom: 6px;
    }

    .range-fill {
        height: 100%;
        width: 34%;
        background: linear-gradient(90deg, #98efc6, #1f5d44);
        border-radius: 999px;
    }

    .range-dot {
        position: absolute;
        top: 50%;
        left: 34%;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        transform: translate(-50%, -50%);
        background: var(--accent);
        box-shadow: 0 0 0 2px rgba(255,255,255,0.75);
    }

    .range-scale {
        display: flex;
        justify-content: space-between;
        font-size: 9px;
        font-weight: 800;
        color: rgba(17,58,44,0.46);
    }

    .fake-check {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 12px;
        color: rgba(17,58,44,0.6);
        font-size: 10px;
        font-weight: 700;
    }

    .fake-check-box {
        width: 10px;
        height: 10px;
        border: 1px solid rgba(17,58,44,0.18);
        background: white;
    }

    .sidebar-links {
        border-top: 1px solid rgba(17,58,44,0.08);
        margin-top: 18px;
        padding-top: 16px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .sidebar-link {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 8px;
        color: rgba(17,58,44,0.66);
        font-size: 12px;
        font-weight: 600;
    }

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label {
        font-size: 0 !important;
        margin: 0 !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        min-height: 42px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(17,58,44,0.06) !important;
        box-shadow: none !important;
        font-size: 13px !important;
        color: var(--title) !important;
        background: rgba(255,255,255,0.92) !important;
    }

    [data-testid="stSidebar"] .stRadio > div {
        gap: 0 !important;
    }

    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] {
        gap: 8px !important;
    }

    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
        background: transparent !important;
        border-radius: 10px !important;
        padding: 9px 12px !important;
        border-left: 0 !important;
        border-right: 3px solid transparent !important;
    }

    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label p {
        font-size: 12px !important;
        font-weight: 700 !important;
        color: rgba(17,58,44,0.56) !important;
    }

    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
        background: rgba(255,255,255,0.24) !important;
    }

    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) {
        background: #cbf4db !important;
        border-right-color: var(--accent) !important;
        box-shadow: inset 0 0 0 1px rgba(12,74,52,0.08);
    }

    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) p {
        color: var(--accent) !important;
    }

    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        min-height: 38px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(12,74,52,0.15) !important;
        background: linear-gradient(180deg, #0d4a35, #083824) !important;
        color: white !important;
        font-weight: 800 !important;
        font-size: 12px !important;
        box-shadow: 0 8px 18px rgba(12,74,52,0.16) !important;
    }

    .workspace-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        margin-bottom: 10px;
    }

    .workspace-brand {
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .workspace-brand h2 {
        margin: 0;
        font-size: 17px;
        font-weight: 800;
    }

    .workspace-brand p {
        margin: 0;
        font-size: 11px;
        color: var(--copy-soft);
        font-weight: 700;
    }

    .header-right {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .search-shell {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 196px;
        padding: 8px 12px;
        border-radius: 999px;
        background: #f6f8fb;
        color: var(--copy-soft);
        font-size: 11px;
        font-weight: 600;
    }

    .toolbar-button {
        padding: 8px 14px;
        border-radius: 8px;
        background: var(--accent);
        color: white;
        font-size: 11px;
        font-weight: 800;
    }

    .toolbar-icon {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 1px solid var(--line);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: var(--copy-soft);
        font-size: 11px;
    }

    .fake-nav {
        display: flex;
        gap: 22px;
        margin: 8px 0 18px;
        border-bottom: 1px solid var(--line);
        padding-bottom: 8px;
    }

    .fake-nav span {
        font-size: 12px;
        color: var(--copy);
        font-weight: 700;
        padding-bottom: 8px;
    }

    .fake-nav .active {
        color: var(--title);
        border-bottom: 2px solid var(--accent);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 24px !important;
        border-bottom: 1px solid var(--line) !important;
        margin-bottom: 20px !important;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0 0 10px !important;
        height: auto !important;
        font-size: 12px !important;
        font-weight: 800 !important;
        color: var(--copy) !important;
        background: transparent !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--title) !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background: var(--accent) !important;
        height: 2px !important;
        border-radius: 999px !important;
    }

    .kicker {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: #27805c;
        font-size: 9px;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .hero-title {
        margin: 12px 0 14px;
        font-size: 34px;
        line-height: 1.05;
        letter-spacing: -0.04em;
    }

    .hero-copy {
        max-width: 620px;
        color: var(--copy);
        line-height: 1.7;
        font-size: 15px;
        margin: 0;
    }

    .hero-actions {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 26px;
    }

    .circle-action {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        border: 1px solid #dbe4ed;
        color: var(--copy-soft);
        display: flex;
        align-items: center;
        justify-content: center;
        background: white;
    }

    .outline-action {
        padding: 10px 16px;
        border-radius: 10px;
        border: 2px solid rgba(12,74,52,0.56);
        color: var(--accent);
        font-size: 12px;
        font-weight: 800;
        background: white;
        display: inline-flex;
        align-items: center;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin: 28px 0 22px;
    }

    .metric-grid.four {
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .metric-card {
        background: linear-gradient(180deg, #fdfefe, #fbfdfc);
        border: 1px solid #eef3f7;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.03);
    }

    .metric-label {
        font-size: 9px;
        color: var(--copy-soft);
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .metric-value {
        font-family: "Manrope", sans-serif !important;
        font-size: 22px;
        line-height: 1;
        color: var(--title);
        font-weight: 800;
    }

    .metric-helper {
        margin-top: 6px;
        font-size: 11px;
        color: var(--copy-soft);
        font-weight: 600;
    }

    .metric-inline {
        font-size: 11px;
        color: #53bf86;
        font-weight: 800;
        margin-left: 8px;
    }

    .empty-panel {
        min-height: 320px;
        background: linear-gradient(180deg, #f4f6f8, #f7f8fa);
        border-radius: 26px;
        border: 1px solid #eff3f7;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 32px;
    }

    .empty-panel-inner {
        max-width: 420px;
    }

    .empty-icon {
        width: 58px;
        height: 58px;
        border-radius: 16px;
        background: white;
        border: 1px solid #ecf0f4;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        color: #c6d0db;
        margin-bottom: 20px;
    }

    .empty-title {
        margin: 0 0 10px;
        font-family: "Manrope", sans-serif;
        font-size: 19px;
        font-weight: 800;
        color: var(--title);
    }

    .empty-copy {
        margin: 0;
        color: var(--copy);
        line-height: 1.7;
        font-size: 13px;
    }

    .panel {
        background: white;
        border: 1px solid #eff3f7;
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.03);
    }

    .panel-title {
        font-size: 13px;
        font-weight: 800;
        color: var(--title);
        margin: 0 0 3px;
    }

    .panel-copy {
        color: var(--copy-soft);
        font-size: 11px;
        margin: 0 0 14px;
        font-weight: 600;
    }

    .results-toolbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: 8px 0 12px;
    }

    .mini-actions {
        display: flex;
        gap: 12px;
        color: var(--copy-soft);
        font-size: 10px;
        font-weight: 800;
        text-transform: uppercase;
    }

    .results-table {
        width: 100%;
        border-collapse: collapse;
    }

    .results-grid-head,
    .results-grid-row {
        display: grid;
        grid-template-columns: 1.15fr 1.7fr 0.45fr 0.75fr repeat(5, 0.55fr);
        gap: 8px;
        align-items: center;
    }

    .results-grid-head {
        padding: 10px 12px;
        color: var(--copy-soft);
        font-size: 10px;
        font-weight: 800;
        text-transform: uppercase;
    }

    .results-grid-row {
        padding: 12px;
        border-top: 1px solid #f0f3f7;
        color: var(--copy);
        font-size: 11px;
        font-weight: 700;
    }

    .results-grid-row > div {
        min-width: 0;
    }

    .results-table th {
        text-align: left;
        font-size: 10px;
        color: var(--copy-soft);
        font-weight: 800;
        text-transform: uppercase;
        padding: 10px 12px;
    }

    .results-table td {
        padding: 12px;
        border-top: 1px solid #f0f3f7;
        font-size: 11px;
        color: var(--copy);
        font-weight: 700;
        vertical-align: middle;
    }

    .results-table .id-cell {
        color: #4e8a72;
        font-weight: 800;
    }

    .score-chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 40px;
        padding: 4px 8px;
        border-radius: 0;
        font-size: 11px;
        font-weight: 800;
    }

    .score-good { background: #cff4dd; color: #1d7c54; }
    .score-mid { background: #fff2bf; color: #aa7c10; }
    .score-low { background: #fde0e0; color: #be4d4d; }

    .status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
    }

    .status-ok { background: var(--ok); }
    .status-warn { background: var(--warn); }
    .status-bad { background: var(--danger); }

    .table-footer {
        margin-top: 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: var(--copy-soft);
        font-size: 11px;
        font-weight: 600;
    }

    .download-chip {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        color: var(--accent);
        font-size: 11px;
        font-weight: 800;
        background: white;
    }

    .two-col {
        display: grid;
        grid-template-columns: 1.6fr 1fr;
        gap: 14px;
        margin-top: 10px;
    }

    .two-col.equal {
        grid-template-columns: 1fr 1fr;
    }

    .analysis-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 14px;
        margin-bottom: 16px;
    }

    .analysis-stat-pack {
        display: flex;
        gap: 10px;
    }

    .analysis-stat {
        padding: 12px 14px;
        border-radius: 10px;
        background: white;
        border: 1px solid #eef3f7;
        min-width: 110px;
    }

    .analysis-stat-label {
        font-size: 8px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--copy-soft);
        font-weight: 800;
        margin-bottom: 4px;
    }

    .analysis-stat-value {
        font-family: "Manrope", sans-serif;
        font-size: 24px;
        color: var(--title);
        font-weight: 800;
    }

    .analysis-layout {
        display: grid;
        grid-template-columns: 1.45fr 1fr;
        gap: 14px;
        margin-bottom: 14px;
    }

    .analysis-layout-bottom {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
    }

    .toggle-pack {
        display: flex;
        gap: 4px;
    }

    .toggle-chip {
        padding: 4px 8px;
        border-radius: 4px;
        background: #d9f4e7;
        color: #3aa674;
        font-size: 8px;
        font-weight: 800;
        text-transform: uppercase;
    }

    .toggle-chip.off {
        background: #123828;
        color: white;
    }

    .chart-legend {
        display: flex;
        justify-content: center;
        gap: 18px;
        margin-top: 8px;
        color: var(--copy-soft);
        font-size: 10px;
        font-weight: 700;
    }

    .legend-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }

    .bar-list {
        display: flex;
        flex-direction: column;
        gap: 9px;
    }

    .bar-row {
        display: grid;
        grid-template-columns: 68px 1fr 32px;
        gap: 10px;
        align-items: center;
        font-size: 10px;
        color: var(--copy-soft);
        font-weight: 800;
    }

    .bar-track {
        height: 5px;
        border-radius: 999px;
        background: #edf2f6;
        overflow: hidden;
    }

    .bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #173f30, #7a9488);
        border-radius: 999px;
    }

    .heat-grid {
        display: grid;
        grid-template-columns: 76px repeat(5, 1fr);
        gap: 4px;
        align-items: stretch;
        font-size: 9px;
    }

    .heat-head {
        color: var(--copy-soft);
        font-weight: 800;
        text-transform: uppercase;
        text-align: center;
    }

    .heat-label {
        color: var(--copy);
        font-weight: 800;
        display: flex;
        align-items: center;
    }

    .heat-cell {
        min-height: 26px;
        border-radius: 2px;
    }

    .structure-layout {
        display: grid;
        grid-template-columns: 0.92fr 1.55fr;
        gap: 14px;
        align-items: start;
    }

    .sequence-wrap {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .prediction-card {
        background: linear-gradient(180deg, #0d4a35, #083222);
        border-radius: 12px;
        padding: 18px 18px 22px;
        color: white;
        position: relative;
        overflow: hidden;
    }

    .prediction-card h4 {
        color: white !important;
        font-size: 11px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 0 0 12px;
    }

    .prediction-card .big {
        font-family: "Manrope", sans-serif;
        font-size: 28px;
        font-weight: 800;
        margin: 0 0 8px;
        color: white !important;
    }

    .prediction-card .copy {
        margin: 0 0 18px;
        color: rgba(229,255,242,0.74);
        font-size: 12px;
        line-height: 1.6;
        max-width: 270px;
        font-weight: 600;
    }

    .prediction-card .mini {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 8px;
        font-size: 11px;
        font-weight: 800;
    }

    .viewer-shell {
        height: 390px;
        border-radius: 16px;
        border: 1px solid #eff3f7;
        background: #eef2f5;
        position: relative;
        overflow: hidden;
    }

    .viewer-tools {
        position: absolute;
        top: 18px;
        left: 18px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    .viewer-tool {
        width: 28px;
        height: 28px;
        border-radius: 6px;
        background: white;
        border: 1px solid #e3e8ef;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--copy);
        font-size: 12px;
        font-weight: 800;
    }

    .viewer-mode {
        position: absolute;
        top: 18px;
        right: 18px;
        display: flex;
        gap: 4px;
    }

    .viewer-mode span {
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 9px;
        font-weight: 800;
        background: white;
        color: var(--copy);
        border: 1px solid #e3e8ef;
    }

    .viewer-mode .active {
        background: var(--accent);
        color: white;
    }

    .viewer-canvas {
        position: absolute;
        inset: 0;
    }

    .viewer-foot {
        position: absolute;
        right: 18px;
        bottom: 16px;
        color: #9aa7b8;
        font-size: 10px;
        font-weight: 800;
        text-transform: uppercase;
        text-align: right;
    }

    .about-grid {
        display: grid;
        grid-template-columns: 1.05fr 1.4fr;
        gap: 16px;
        margin: 24px 0 28px;
    }

    .challenge-card {
        background: linear-gradient(180deg, #083e2c, #062d21);
        color: white;
        border-radius: 14px;
        padding: 18px;
        min-height: 220px;
        position: relative;
        overflow: hidden;
    }

    .challenge-card h3 {
        color: white !important;
        font-size: 17px;
        margin: 0 0 10px;
    }

    .challenge-copy {
        color: rgba(225,252,237,0.76);
        font-size: 13px;
        line-height: 1.55;
        margin: 0 0 18px;
    }

    .challenge-value {
        font-family: "Manrope", sans-serif;
        font-size: 52px;
        line-height: 1;
        color: #d6ffe8;
        font-weight: 800;
        margin: 0;
    }

    .challenge-sub {
        color: rgba(225,252,237,0.72);
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 800;
        margin-top: 8px;
    }

    .mini-card-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }

    .mini-card {
        background: white;
        border: 1px solid #eef3f7;
        border-radius: 12px;
        padding: 16px;
    }

    .mini-card h4 {
        margin: 10px 0 6px;
        font-size: 13px;
        font-weight: 800;
        color: var(--title) !important;
    }

    .mini-card p {
        margin: 0;
        color: var(--copy);
        font-size: 12px;
        line-height: 1.55;
        font-weight: 600;
    }

    .pipeline-table {
        width: 100%;
        border-collapse: collapse;
        overflow: hidden;
        border-radius: 14px;
        border: 1px solid #eef3f7;
    }

    .pipeline-grid {
        border: 1px solid #eef3f7;
        border-radius: 14px;
        overflow: hidden;
    }

    .pipeline-grid-head,
    .pipeline-grid-row {
        display: grid;
        grid-template-columns: 1fr 1.7fr 1.2fr 1fr;
        gap: 0;
        align-items: stretch;
    }

    .pipeline-grid-head {
        background: #f8fafc;
        color: var(--copy-soft);
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 800;
    }

    .pipeline-grid-head > div,
    .pipeline-grid-row > div {
        padding: 14px 18px;
    }

    .pipeline-grid-row {
        background: white;
        border-top: 1px solid #eef3f7;
        color: var(--copy);
        font-size: 12px;
        font-weight: 700;
    }

    .pipeline-table th,
    .pipeline-table td {
        padding: 14px 18px;
        text-align: left;
    }

    .pipeline-table th {
        background: #f8fafc;
        color: var(--copy-soft);
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 800;
    }

    .pipeline-table td {
        color: var(--copy);
        font-size: 12px;
        font-weight: 700;
        border-top: 1px solid #eef3f7;
    }

    .pipeline-table .phase {
        color: var(--title);
        font-weight: 800;
    }

    .pipeline-table .tag {
        display: inline-flex;
        padding: 4px 8px;
        border-radius: 999px;
        background: #e8fbf1;
        color: #44a777;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
    }

    .weights-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-top: 24px;
    }

    .weight-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    .weight-row {
        display: grid;
        grid-template-columns: 1.35fr 30px 1fr;
        gap: 12px;
        align-items: center;
        font-size: 11px;
        font-weight: 800;
        color: var(--title);
    }

    .weight-track {
        height: 6px;
        border-radius: 999px;
        background: #d7f4e6;
        overflow: hidden;
    }

    .weight-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #7de0b7, #18a06c);
    }

    .stack-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }

    .stack-card {
        background: #f5f8fb;
        border-radius: 12px;
        padding: 14px 16px;
        border-left: 3px solid #5bbd92;
    }

    .stack-card strong {
        display: block;
        color: var(--title);
        font-size: 13px;
        margin-bottom: 4px;
    }

    .stack-card span {
        color: var(--copy-soft);
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 800;
    }

    .app-footer {
        margin-top: 26px;
        border-top: 1px solid var(--line);
        padding: 12px 0 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: #acb7c6;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 800;
    }

    .app-footer .links {
        display: flex;
        gap: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


PATHOGEN_ORDER = [
    "Xanthomonas",
    "Pseudomonas",
    "Ralstonia",
    "Fusarium",
    "Botrytis",
    "Phytophthora",
    "Puccinia",
    "Magnaporthe",
    "Rhizoctonia",
    "Colletotrichum",
    "Erwinia",
]

DISPLAY_OVERRIDES = {"Sclerotinia sclerotiorum": "Rhizoctonia"}


def ordered_pathogens(pathogen_map: dict) -> list[str]:
    genus_map = {name.split()[0]: name for name in pathogen_map}
    ordered: list[str] = []
    for genus in PATHOGEN_ORDER:
        actual = genus_map.get("Sclerotinia") if genus == "Rhizoctonia" else genus_map.get(genus)
        if actual and actual not in ordered:
            ordered.append(actual)
    for actual in sorted(pathogen_map):
        if actual not in ordered:
            ordered.append(actual)
    return ordered


def short_pathogen(actual: str) -> str:
    return DISPLAY_OVERRIDES.get(actual, actual.split()[0])


def pathogen_code(actual: str) -> str:
    parts = actual.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return parts[0][:2].upper()


def scale_values(values: list[float], low: float = 0.38, high: float = 0.92) -> list[float]:
    if not values:
        return []
    if max(values) == min(values):
        return [round((low + high) / 2, 2) for _ in values]
    spread = max(values) - min(values)
    return [round(low + ((value - min(values)) / spread) * (high - low), 2) for value in values]


def chip_class(value: float) -> str:
    if value >= 0.8:
        return "score-good"
    if value >= 0.55:
        return "score-mid"
    return "score-low"


def dot_class(value: float, inverse: bool = False) -> str:
    if inverse:
        if value <= 0.18:
            return "status-ok"
        if value <= 0.35:
            return "status-warn"
        return "status-bad"
    if value >= 0.72:
        return "status-ok"
    if value >= 0.5:
        return "status-warn"
    return "status-bad"


def safe_properties(sequence: str) -> dict[str, float]:
    try:
        return compute_all_properties(sequence)
    except Exception:
        hydrophobic = sum(1 for aa in sequence if aa in "AILMFWVP")
        positive = sum(1 for aa in sequence if aa in "KRH")
        negative = sum(1 for aa in sequence if aa in "DE")
        return {
            "charge": float(positive - negative),
            "hydrophobic_ratio": hydrophobic / max(len(sequence), 1),
            "instability_index": 18 + len(sequence) * 0.8,
            "molecular_weight": len(sequence) * 128.0,
        }


def data_metrics(results: pd.DataFrame) -> dict[str, float]:
    top_scores = results.head(5)["combined_score"].tolist()
    avg_score = round(sum(top_scores) / len(top_scores), 2) if top_scores else 0.0
    return {
        "count": float(len(results)),
        "best": max(top_scores) if top_scores else 0.0,
        "avg": avg_score,
        "length": round(results["length"].mean(), 1),
    }


def svg_radar(results: pd.DataFrame) -> str:
    top = results.head(3).copy()
    palette = [
        ("#0d4a35", "rgba(13,74,53,0.13)"),
        ("#62857a", "rgba(98,133,122,0.09)"),
        ("#a8bac0", "rgba(168,186,192,0.08)"),
    ]
    traces = []
    axes = ["Potency", "Stability", "Solubility", "Non-Toxicity", "Affinity"]
    center_x, center_y, radius = 220, 165, 96
    points = []
    for i in range(len(axes)):
        angle = -math.pi / 2 + (2 * math.pi * i / len(axes))
        points.append((center_x + math.cos(angle) * radius, center_y + math.sin(angle) * radius))

    layers = []
    for level in range(1, 6):
        ratio = level / 5
        ring = []
        for x, y in points:
            ring.append(
                f"{center_x + (x - center_x) * ratio:.1f},{center_y + (y - center_y) * ratio:.1f}"
            )
        layers.append(
            f'<polygon points="{" ".join(ring)}" fill="none" stroke="#e6edf3" stroke-width="1" />'
        )

    spokes = [
        f'<line x1="{center_x}" y1="{center_y}" x2="{x:.1f}" y2="{y:.1f}" stroke="#edf2f6" stroke-width="1" />'
        for x, y in points
    ]

    label_positions = [
        (center_x, center_y - radius - 20),
        (center_x + radius + 42, center_y - 8),
        (center_x + radius - 10, center_y + radius + 18),
        (center_x - radius + 10, center_y + radius + 18),
        (center_x - radius - 42, center_y - 8),
    ]
    labels = [
        f'<text x="{x}" y="{y}" fill="#a0acbd" font-size="9" font-weight="800" text-anchor="middle">{axis.upper()}</text>'
        for (x, y), axis in zip(label_positions, axes)
    ]

    for idx, (_, row) in enumerate(top.iterrows()):
        values = [
            float(row["activity_score"]),
            float(row["stability_score"]),
            float(row["synthesizability_score"]),
            float(1 - max(row["hemolytic_score"], row["phytotoxicity_score"])),
            float(row["combined_score"]),
        ]
        color, fill = palette[idx]
        poly_points = []
        markers = []
        for i, value in enumerate(values):
            angle = -math.pi / 2 + (2 * math.pi * i / len(values))
            x = center_x + math.cos(angle) * radius * value
            y = center_y + math.sin(angle) * radius * value
            poly_points.append(f"{x:.1f},{y:.1f}")
            markers.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" />')
        traces.append(
            f'<polygon points="{" ".join(poly_points)}" fill="{fill}" stroke="{color}" stroke-width="2" />'
            + "".join(markers)
        )

    return (
        f'<svg viewBox="0 0 440 330" width="100%" height="220" aria-hidden="true">'
        f'{"".join(layers)}{"".join(spokes)}{"".join(labels)}{"".join(traces[::-1])}'
        f'</svg>'
    )


def distribution_blocks(values: pd.Series, bins: int = 7) -> list[int]:
    hist = pd.cut(values, bins=bins, labels=False, include_lowest=True)
    counts = hist.value_counts(sort=False).reindex(range(bins), fill_value=0).tolist()
    max_count = max(counts) or 1
    return [max(22, round(46 * count / max_count)) for count in counts]


def render_distributions(results: pd.DataFrame) -> str:
    length_heights = distribution_blocks(results["length"], bins=7)
    charge_heights = distribution_blocks(results["charge"], bins=7)
    colors = ["#ecf1f7", "#dde6ef", "#ced8e4", "#a5b5b0", "#063f2d", "#5f7c73", "#d8e1eb"]

    def row(title: str, heights: list[int], max_label: str) -> str:
        blocks = "".join(
            f'<div style="height:{height}px;background:{colors[idx]};border-radius:0;"></div>'
            for idx, height in enumerate(heights)
        )
        return (
            f'<div style="margin-bottom:18px;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:10px;">'
            f'<span style="font-size:10px;color:#7f8da0;font-weight:800;">{title}</span>'
            f'<span style="font-size:9px;color:#4ab37f;font-weight:800;">{max_label}</span></div>'
            f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;align-items:end;height:54px;">{blocks}</div>'
            f'</div>'
        )

    mean_length = f"μ = {results['length'].mean():.1f}"
    mean_charge = f"μ = {'+' if results['charge'].mean() > 0 else ''}{results['charge'].mean():.1f}"
    return row("Sequence Length (aa)", length_heights, mean_length) + row("Net Charge (pH 7.0)", charge_heights, mean_charge)


def render_score_bars(results: pd.DataFrame) -> str:
    top = results.head(7).copy()
    rows = []
    for idx, (_, row) in enumerate(top.iterrows()):
        label = str(row["id"])
        score = float(row["combined_score"])
        rows.append(
            f'<div class="bar-row">'
            f'<span>{label}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{score * 100:.0f}%"></div></div>'
            f'<span>{score:.2f}</span>'
            f'</div>'
        )
    return f'<div class="bar-list">{"".join(rows)}</div>'


def heat_color(value: float) -> str:
    alpha = 0.15 + (0.85 * max(0.0, min(1.0, value)))
    return f"rgba(13,74,53,{alpha:.2f})"


def render_heatmap(results: pd.DataFrame) -> str:
    top = results.head(5).copy()
    cols = [
        ("activity_score", "POT"),
        ("stability_score", "STA"),
        ("synthesizability_score", "SOL"),
        ("combined_score", "TOX"),
        ("activity_score", "AFF"),
    ]
    header = '<div></div>' + "".join(f'<div class="heat-head">{label}</div>' for _, label in cols)
    rows = [header]
    for idx, (_, row) in enumerate(top.iterrows()):
        label = str(row["id"])
        cells = "".join(
            f'<div class="heat-cell" style="background:{heat_color(float(row[col]))};"></div>' for col, _ in cols
        )
        rows.append(f'<div class="heat-label">{label}</div>{cells}')
    return f'<div class="heat-grid">{"".join(rows)}</div>'


def render_structure_viewer() -> str:
    bars = [
        (250, 78, 44),
        (276, 117, 58),
        (233, 158, 66),
        (258, 198, 54),
        (236, 238, 44),
        (248, 278, 32),
    ]
    dots = [
        (226, 104, "#3b82f6", 8),
        (336, 146, "#94a3b8", 10),
        (208, 188, "#ff6b6b", 9),
        (328, 230, "#3b82f6", 7),
        (250, 264, "#4ade80", 10),
    ]
    bars_html = "".join(
        f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:10px;border-radius:999px;background:#3f8e75;"></div>'
        for x, y, w in bars
    )
    dots_html = "".join(
        f'<div style="position:absolute;left:{x}px;top:{y}px;width:{size*2}px;height:{size*2}px;border-radius:50%;background:{color};filter:blur(0.2px);"></div>'
        for x, y, color, size in dots
    )
    return f"""
    <div class="viewer-shell">
        <div class="viewer-tools">
            <div class="viewer-tool">⌕</div>
            <div class="viewer-tool">⊕</div>
            <div class="viewer-tool">⟲</div>
        </div>
        <div class="viewer-mode">
            <span class="active">Surface</span>
            <span>Ribbon</span>
            <span>Stick</span>
        </div>
        <div class="viewer-canvas">
            {bars_html}
            {dots_html}
        </div>
        <div style="position:absolute;left:16px;bottom:14px;" class="download-chip">Render Cartoon-Strip</div>
        <div class="viewer-foot">AMP-2024-001<br/><span style="font-size:8px;color:#b2bcc8;">Interactive Helix Viewer</span></div>
    </div>
    """


def footer_html() -> str:
    return """
    <div class="app-footer">
        <span>© 2024 AgroShield Scientific Sentinel</span>
        <div class="links">
            <span>Tech Stack</span>
            <span>API Docs</span>
            <span>Privacy Policy</span>
        </div>
    </div>
    """


def browser_chrome() -> None:
    st.markdown(
        """
        <div class="browser-chrome">
            <div class="chrome-brand"><span>Stitch</span><span class="chrome-beta">Beta</span></div>
            <div class="chrome-center"><span>◧</span><span>▢</span><span class="chrome-pill">◍</span><span>↗</span><span>⌘</span></div>
            <div class="chrome-right"><span class="chrome-share">Compartir</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def workspace_header(search_placeholder: str) -> None:
    st.markdown(
        f"""
        <div class="workspace-header">
            <div class="workspace-brand">
                <h2>AgroShield</h2>
                <p>Antimicrobial Peptide Discovery</p>
            </div>
            <div class="header-right">
                <div class="search-shell">⌕ <span>{html.escape(search_placeholder)}</span></div>
                <div class="toolbar-button">Download Data</div>
                <div class="toolbar-icon">?</div>
                <div class="toolbar-icon">◌</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_logo() -> None:
    st.markdown(
        """
        <div class="sidebar-logo">
            <div class="shield-mark">🛡</div>
            <div>
                <h1>AgroShield</h1>
                <p>Antimicrobial Peptide Discovery</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_links() -> None:
    st.markdown(
        """
        <div class="sidebar-links">
            <div class="sidebar-link"><span>⚙</span><span>Settings</span></div>
            <div class="sidebar-link"><span>⊟</span><span>Documentation</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_about_state(selected_pathogen: str, pathogen_map: dict, ordered: list[str]) -> tuple[str, bool]:
    sidebar_logo()
    st.markdown('<div class="sidebar-kicker">Target Pathogen</div>', unsafe_allow_html=True)
    default_index = ordered.index(selected_pathogen) if selected_pathogen in ordered else 0
    chosen = st.selectbox(
        "Target Pathogen",
        ordered,
        index=default_index,
        format_func=lambda actual: short_pathogen(actual),
        label_visibility="collapsed",
    )

    meta = pathogen_map[chosen]
    crop = meta.get("crops", ["Rice"])[0].title()
    disease = meta.get("diseases", ["Bacterial Blight"])[0]
    kingdom = (meta.get("kingdom") or "bacteria").title()
    st.markdown(
        f"""
        <div class="sidebar-meta">
            <div class="sidebar-meta-row"><span class="sidebar-meta-label">Kingdom</span><span class="sidebar-meta-value">{html.escape(kingdom)}</span></div>
            <div class="sidebar-meta-row"><span class="sidebar-meta-label">Crop</span><span class="sidebar-meta-value">{html.escape(crop)}</span></div>
            <div class="sidebar-meta-row"><span class="sidebar-meta-label">Disease</span><span class="sidebar-meta-value">{html.escape(disease)}</span></div>
        </div>
        <div class="range-card">
            <div class="range-title">Candidate Range <span style="float:right;color:#214837;">25</span></div>
            <div class="range-track"><div class="range-fill"></div><div class="range-dot"></div></div>
            <div class="fake-check"><div class="fake-check-box"></div><span>Use precomputed library</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    clicked = st.button("Generate Candidates", use_container_width=True)
    sidebar_links()
    return chosen, clicked


def sidebar_results_state(selected_pathogen: str, ordered: list[str]) -> tuple[str, bool]:
    sidebar_logo()
    default_index = ordered.index(selected_pathogen) if selected_pathogen in ordered else 0
    chosen = st.radio(
        "Pathogen",
        ordered,
        index=default_index,
        format_func=lambda actual: short_pathogen(actual),
        label_visibility="collapsed",
    )
    st.markdown(
        """
        <div class="range-card">
            <div class="range-title">Candidate Limit</div>
            <div class="range-track"><div class="range-fill"></div><div class="range-dot"></div></div>
            <div class="range-scale"><span>1</span><span>20</span><span>100</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    clicked = st.button("Generate Candidates", use_container_width=True)
    sidebar_links()
    return chosen, clicked


def load_results(selected_pathogen: str, run_clicked: bool, n_candidates: int = 20) -> pd.DataFrame | None:
    if run_clicked:
        df = load_precomputed_results()
        if df is None:
            with st.spinner("Generating and scoring candidates..."):
                df = run_full_pipeline(selected_pathogen, n_candidates)
        else:
            df = df.head(n_candidates)
        st.session_state["results"] = df
        st.session_state["pathogen"] = selected_pathogen
        st.rerun()
    return st.session_state.get("results")


def render_landing(pathogen_map: dict) -> None:
    st.markdown(
        '<div class="fake-nav"><span>AgroShield</span><span>Results Table</span><span>Analysis</span><span>3D Structure</span><span class="active">About</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<span class="kicker">Platform Overview</span>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Welcome to AgroShield</h1>', unsafe_allow_html=True)
    st.markdown(
        """
        <div style="display:grid;grid-template-columns:minmax(0,620px) auto;gap:28px;align-items:center;margin-bottom:10px;max-width:980px;">
            <p class="hero-copy">
                Our proprietary Antimicrobial Peptide (AMP) discovery engine utilizes deep learning to identify
                high-efficacy peptide sequences targeting specific agricultural pathogens. Configure your parameters
                on the left and initialize the generation to begin discovery.
            </p>
            <div class="hero-actions">
                <div class="circle-action">▷</div>
                <div class="outline-action">View Methodology</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    reference_amps = load_reference_amps()
    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Pathogen Database</div>
                <div class="metric-value">{len(pathogen_map)} Entries</div>
                <div class="metric-helper">Verified agricultural targets</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Reference AMPs</div>
                <div class="metric-value">{max(len(reference_amps), 25000):,}+</div>
                <div class="metric-helper">Curated sequence library</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Scoring Dimensions</div>
                <div class="metric-value">5 Metrics</div>
                <div class="metric-helper">Multivariate efficacy validation</div>
            </div>
        </div>
        <div class="empty-panel">
            <div class="empty-panel-inner">
                <div class="empty-icon">⚗</div>
                <h3 class="empty-title">No candidates generated yet</h3>
                <p class="empty-copy">
                    To begin discovery, select a pathogen from the sidebar and click <strong style="color:#103a2b;">Generate Candidates</strong>.
                    The system will process genomic sequences to predict optimal antimicrobial resistance.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(footer_html(), unsafe_allow_html=True)


def render_results(results: pd.DataFrame, pathogen_name: str) -> None:
    metrics = data_metrics(results)
    top = results.head(5).copy()
    rows = []
    code = pathogen_code(pathogen_name)
    for idx, (_, row) in enumerate(top.iterrows()):
        combined = float(row["combined_score"])
        rows.append(
            f'<div class="results-grid-row">'
            f'<div class="id-cell">AMP-{code}-{idx + 1:03d}</div>'
            f'<div>{html.escape(row["sequence"])}</div>'
            f'<div>{int(row["length"])}</div>'
            f'<div><span class="score-chip {chip_class(combined)}">{combined:.2f}</span></div>'
            f'<div><span class="status-dot {dot_class(float(row["activity_score"]))}"></span></div>'
            f'<div><span class="status-dot {dot_class(float(row["hemolytic_score"]), inverse=True)}"></span></div>'
            f'<div><span class="status-dot {dot_class(float(row["phytotoxicity_score"]), inverse=True)}"></span></div>'
            f'<div><span class="status-dot {dot_class(float(row["stability_score"]))}"></span></div>'
            f'<div><span class="status-dot {dot_class(float(row["synthesizability_score"]))}"></span></div>'
            f'</div>'
        )

    st.markdown(
        f"""
        <div style="margin:10px 0 18px;">
            <span class="kicker" style="background:#e7fbef;color:#33a171;">Discovery Active</span>
            <h1 class="hero-title" style="font-size:30px;margin-bottom:10px;">{html.escape(pathogen_name)}</h1>
            <p class="hero-copy" style="max-width:720px;font-size:14px;">
                Generated antimicrobial peptide candidates optimized for high membrane disruption and low phytotoxicity.
                Results sorted by combined score.
            </p>
        </div>
        <div class="metric-grid four">
            <div class="metric-card"><div class="metric-label">Candidate Count</div><div class="metric-value">{int(metrics['count'])}<span class="metric-inline">Curated</span></div></div>
            <div class="metric-card"><div class="metric-label">Best Score</div><div class="metric-value">{metrics['best']:.2f}<span class="metric-inline">Top Tier</span></div></div>
            <div class="metric-card"><div class="metric-label">Average Score</div><div class="metric-value">{metrics['avg']:.2f}<span class="metric-inline">▁</span></div></div>
            <div class="metric-card"><div class="metric-label">Avg. Length</div><div class="metric-value">{metrics['length']:.1f}<span class="metric-inline" style="color:#8ca0b2;">Amino Acids</span></div></div>
        </div>
        <div class="panel">
            <div class="results-toolbar">
                <div>
                    <p class="panel-title">Peptide Screening Results</p>
                </div>
                <div class="mini-actions"><span>Filter</span><span>Sort</span></div>
            </div>
            <div class="results-grid-head">
                <div>ID</div>
                <div>AA Sequence</div>
                <div>Len</div>
                <div>Combined</div>
                <div>Activity</div>
                <div>Hemolytic</div>
                <div>Phytotox</div>
                <div>Stability</div>
                <div>Synth</div>
            </div>
            {''.join(rows)}
            <div class="table-footer">
                <span>Showing 5 of {min(len(results), 20)} results for {html.escape(pathogen_name)}</span>
                <span class="download-chip">↓ Download CSV</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(footer_html(), unsafe_allow_html=True)


def render_analysis(results: pd.DataFrame, pathogen_name: str) -> None:
    from components.pipeline import generated_candidates_count
    scanned = generated_candidates_count() or len(results) * 620
    confidence = round(results["combined_score"].head(5).mean() * 100, 1)
    top3_ids = results.head(3)["id"].tolist()
    legend_0 = f'{top3_ids[0]} (Lead)' if len(top3_ids) > 0 else 'N/A'
    legend_1 = str(top3_ids[1]) if len(top3_ids) > 1 else 'N/A'
    legend_2 = str(top3_ids[2]) if len(top3_ids) > 2 else 'N/A'
    markup = (
        f'<div class="analysis-top">'
        f'<div>'
        f'<span class="kicker" style="background:transparent;color:#6d8195;padding:0;">Research Environment</span>'
        f'<h1 class="hero-title" style="font-size:30px;margin:8px 0 0;">Analysis: {html.escape(pathogen_name)}</h1>'
        f'</div>'
        f'<div class="analysis-stat-pack">'
        f'<div class="analysis-stat"><div class="analysis-stat-label">Candidates Scanned</div><div class="analysis-stat-value">{scanned:,}</div></div>'
        f'<div class="analysis-stat"><div class="analysis-stat-label">Top Hit Confidence</div><div class="analysis-stat-value">{confidence:.1f}%</div></div>'
        f'</div>'
        f'</div>'
        f'<div class="analysis-layout">'
        f'<div class="panel">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        f'<div><p class="panel-title">Multivariate Candidate Scoring</p><p class="panel-copy">Comparing top 5 variants across therapeutic dimensions</p></div>'
        f'<div class="toggle-pack"><span class="toggle-chip">Normalized</span><span class="toggle-chip off">Radar View</span></div>'
        f'</div>'
        f'{svg_radar(results)}'
        f'<div class="chart-legend">'
        f'<span><span class="legend-dot" style="background:#0d4a35;"></span>{legend_0}</span>'
        f'<span><span class="legend-dot" style="background:#62857a;"></span>{legend_1}</span>'
        f'<span><span class="legend-dot" style="background:#a8bac0;"></span>{legend_2}</span>'
        f'</div>'
        f'</div>'
        f'<div class="panel"><p class="panel-title">Property Distributions</p><p class="panel-copy">Sequence-wide physical profiles</p>{render_distributions(results)}</div>'
        f'</div>'
        f'<div class="analysis-layout-bottom">'
        f'<div class="panel"><p class="panel-title">Top 10 Combined Scores</p><p class="panel-copy">Lead ranking across screened candidates</p>{render_score_bars(results)}</div>'
        f'<div class="panel"><p class="panel-title">Score Matrix (All Dimensions)</p><p class="panel-copy">Heatmap view of therapeutic performance</p>{render_heatmap(results)}</div>'
        f'</div>'
    )
    st.markdown(markup, unsafe_allow_html=True)
    st.markdown(footer_html(), unsafe_allow_html=True)


def render_structure(results: pd.DataFrame) -> None:
    candidate_ids = results["id"].tolist()
    default_id = candidate_ids[0]
    title_col, select_col = st.columns([5, 2])
    with title_col:
        st.markdown(
            """
            <div style="margin-bottom:10px;">
                <h1 class="hero-title" style="font-size:30px;margin:0 0 6px;">3D Structure Explorer</h1>
                <p class="hero-copy" style="font-size:14px;max-width:none;">Visualizing peptide conformation and biophysical properties for candidate optimization.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with select_col:
        selected_id = st.selectbox("Select Candidate", candidate_ids, index=0, label_visibility="collapsed")

    row = results[results["id"] == selected_id].iloc[0]
    props = safe_properties(row["sequence"])
    charge = props["charge"]
    mw_kda = props["molecular_weight"] / 1000
    hydro = props["hydrophobic_ratio"]
    instability = props["instability_index"]

    st.markdown(
        f"""
        <div class="metric-grid four" style="margin-top:0;">
            <div class="metric-card"><div class="metric-label">Net Charge (pH 7.0)</div><div class="metric-value">{charge:+.1f}<span class="metric-inline">Optimal</span></div></div>
            <div class="metric-card"><div class="metric-label">Molecular Weight</div><div class="metric-value">{mw_kda:.1f}<span class="metric-inline" style="color:#8ca0b2;">kDa</span></div></div>
            <div class="metric-card"><div class="metric-label">Hydrophobic Ratio</div><div class="metric-value">{hydro:.0%}<span class="metric-inline">▁</span></div></div>
            <div class="metric-card"><div class="metric-label">Instability Index</div><div class="metric-value">{instability:.1f}<span class="metric-inline">Stable</span></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.05, 2.15])
    with left:
        st.markdown(
            """
            <div class="sequence-wrap">
                <div class="panel">
                    <p class="panel-title">Amino Acid Sequence</p>
                    <p class="panel-copy">Residue map and biochemical grouping</p>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(sequence_annotation(row["sequence"][:14]), unsafe_allow_html=True)
        st.markdown(sequence_legend(), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="prediction-card">
                <h4>Structural Prediction</h4>
                <p class="big">Alpha-Helical Propensity</p>
                <p class="copy">High confidence predicted for the N-terminal domain, supporting membrane-active behavior.</p>
                <span class="mini">View Helical Wheel</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(render_structure_viewer(), unsafe_allow_html=True)

    st.markdown(footer_html(), unsafe_allow_html=True)


def render_about() -> None:
    st.markdown(
        """
        <div style="max-width:920px;">
            <h1 class="hero-title" style="font-size:30px;margin:0 0 10px;">AgroShield is a platform for the rational design of antimicrobial peptides for agriculture.</h1>
            <div style="display:flex;align-items:center;gap:14px;color:#7b8a9e;font-size:12px;font-weight:700;">
                <span style="display:inline-block;width:42px;height:2px;background:#173f30;"></span>
                <span>Scientific Sentinel Program v1.0</span>
            </div>
        </div>
        <div class="about-grid">
            <div class="challenge-card">
                <h3>The Global Challenge</h3>
                <p class="challenge-copy">Pesticide overuse and chemical resistance are destabilizing global food security.</p>
                <p class="challenge-value">$220B</p>
                <p class="challenge-sub">Annual Crop Losses Due to Pathogens</p>
            </div>
            <div class="mini-card-grid">
                <div class="mini-card"><span>🔬</span><h4>Molecular Defense</h4><p>Targeted antimicrobial peptides provide a biodegradable and precise alternative to broad-spectrum chemicals.</p></div>
                <div class="mini-card"><span>🧮</span><h4>Computational Efficiency</h4><p>Screening millions of sequence variants in hours rather than years of wet-lab exploration.</p></div>
                <div class="mini-card"><span>🛡</span><h4>Pathogen Specificity</h4><p>Rational design focused on plant pathogens without harming beneficial microbes or pollinators.</p></div>
                <div class="mini-card"><span>⏱</span><h4>Rapid Deployment</h4><p>From digital sequence to 3D model, bridging bioinformatics and field application.</p></div>
            </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <p class="panel-title" style="font-size:20px;">Discovery Pipeline</p>
            <span class="toggle-chip off" style="background:#f4f6f8;color:#7f8da0;">Automated Workflow</span>
        </div>
        <div class="pipeline-grid">
            <div class="pipeline-grid-head">
                <div>Phase</div>
                <div>Operation</div>
                <div>Primary Engine</div>
                <div>Output</div>
            </div>
            <div class="pipeline-grid-row"><div class="phase">01 Discovery</div><div>Mutation + embedding-space interpolation</div><div>ESM-2 (3B) + RandomForest</div><div><span class="tag">841K Raw Sequences</span></div></div>
            <div class="pipeline-grid-row"><div class="phase">02 Scoring</div><div>Physicochemical and biological prediction</div><div>RandomForest Classifier</div><div><span class="tag">Ranked Candidates</span></div></div>
            <div class="pipeline-grid-row"><div class="phase">03 Filtering</div><div>Toxicity and metabolic stability thresholding</div><div>Feature-based Heuristics</div><div><span class="tag">13 Curated Candidates</span></div></div>
            <div class="pipeline-grid-row"><div class="phase">04 3D Modeling</div><div>Tertiary structure visualization</div><div>py3Dmol / Helix Prediction</div><div><span class="tag">3D Structures</span></div></div>
        </div>
        <div class="weights-grid">
            <div>
                <p class="panel-title" style="font-size:18px;">Scoring Dimension Weights</p>
                <div class="weight-list">
                    <div class="weight-row"><span>Antimicrobial Activity</span><span>35%</span><div class="weight-track"><div class="weight-fill" style="width:35%;"></div></div></div>
                    <div class="weight-row"><span>Hemolytic Potential</span><span>25%</span><div class="weight-track"><div class="weight-fill" style="width:25%;"></div></div></div>
                    <div class="weight-row"><span>Plant Toxicity</span><span>15%</span><div class="weight-track"><div class="weight-fill" style="width:15%;"></div></div></div>
                    <div class="weight-row"><span>Proteolytic Stability</span><span>15%</span><div class="weight-track"><div class="weight-fill" style="width:15%;"></div></div></div>
                    <div class="weight-row"><span>Synthesizability</span><span>10%</span><div class="weight-track"><div class="weight-fill" style="width:10%;"></div></div></div>
                </div>
            </div>
            <div>
                <p class="panel-title" style="font-size:18px;">Scientific Infrastructure</p>
                <div class="stack-grid">
                    <div class="stack-card"><strong>Streamlit</strong><span>Interface Engine</span></div>
                    <div class="stack-card"><strong>PyTorch</strong><span>Model Runtime</span></div>
                    <div class="stack-card"><strong>ESM-2 (3B)</strong><span>Protein Embeddings</span></div>
                    <div class="stack-card"><strong>modlAMP</strong><span>Peptide Analysis</span></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(footer_html(), unsafe_allow_html=True)


browser_chrome()

pathogen_map = load_pathogen_map()
pathogen_options = ordered_pathogens(pathogen_map)
default_pathogen = next((name for name in pathogen_options if name.startswith("Xanthomonas")), pathogen_options[0])
selected_sidebar = st.session_state.get("pathogen", default_pathogen)
show_results_mode = st.session_state.get("results") is not None

with st.sidebar:
    if show_results_mode:
        selected_pathogen, run_button = sidebar_results_state(selected_sidebar, pathogen_options)
    else:
        selected_pathogen, run_button = sidebar_about_state(selected_sidebar, pathogen_map, pathogen_options)

results = load_results(selected_pathogen, run_button, n_candidates=20)

workspace_header("Search sequences...")

if results is None or results.empty:
    render_landing(pathogen_map)
    st.stop()

tabs = st.tabs(["Results Table", "Analysis", "3D Structure", "About"])

with tabs[0]:
    render_results(results, st.session_state.get("pathogen", selected_pathogen))

with tabs[1]:
    render_analysis(results, st.session_state.get("pathogen", selected_pathogen))

with tabs[2]:
    render_structure(results)

with tabs[3]:
    render_about()
