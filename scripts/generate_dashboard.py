#!/usr/bin/env python3
"""
generate_dashboard.py — 從處理後的資料生成靜態 HTML dashboard
Generates a self-contained static HTML dashboard → docs/index.html
(Deploy via GitHub Pages: Settings → Pages → Source: /docs)

Usage:
    python scripts/generate_dashboard.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

DATA_PARQUET = ROOT / "data" / "processed" / "battery_trade.parquet"
DATA_CSV     = ROOT / "data" / "processed" / "battery_trade.csv"
OUT_HTML     = ROOT / "docs" / "index.html"
OUT_HTML.parent.mkdir(parents=True, exist_ok=True)

from config import HS_CODES, HS_FLAT

# ── Plotly config: no toolbar clutter, responsive ─────────────────────────────
PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}
CHART_HEIGHT = 420

# ── Color palette ─────────────────────────────────────────────────────────────
# Anchored to observed DSET brand colors (blues + coral red + orange badge)
# then extended with green / yellow / purple for chart distinguishability.
DSET_COLORS = [
    "#093A8C",  # DSET dark navy
    "#D65740",  # DSET coral red  (energy section)
    "#314F78",  # DSET medium navy
    "#F0943A",  # DSET orange     (category badges)
    "#859BD5",  # DSET periwinkle
    "#2E7D5E",  # forest green
    "#99C0D3",  # DSET light teal
    "#F2C94C",  # warm yellow
    "#5B5EA6",  # slate purple
    "#2B3A52",  # DSET footer slate
    "#4A9B8E",  # teal green
    "#E8892A",  # amber
]
DSET_BG   = "#D9EBF7"
DSET_NAVY = "#093A8C"
COUNTRY_RED = "#C0392B"
COUNTRY_BLUE = "#1F5AA6"
COUNTRY_OTHER_GRAY = "#9CA3AF"
COUNTRY_PALETTE = [
    "#E8892A",
    "#2E7D5E",
    "#5B5EA6",
    "#D65740",
    "#4A9B8E",
    "#F2C94C",
    "#314F78",
    "#859BD5",
    "#B56576",
    "#7A9E7E",
    "#A36F5C",
    "#3A7CA5",
]


def load_data() -> pd.DataFrame:
    if DATA_PARQUET.exists():
        df = pd.read_parquet(DATA_PARQUET)
    elif DATA_CSV.exists():
        df = pd.read_csv(DATA_CSV, parse_dates=["date"])
    else:
        raise FileNotFoundError(
            "No processed data found. Run: python scripts/process_data.py"
        )
    df["date"] = pd.to_datetime(df["date"])
    return df


def chart_html(fig, fixed_height: int = None, fixed_width: int = None) -> str:
    """Return plotly figure as an embeddable <div>.
    Pass fixed_height / fixed_width to lock the chart size."""
    cfg = PLOTLY_CONFIG
    if fixed_height or fixed_width:
        layout_updates = {"autosize": False}
        if fixed_height:
            layout_updates["height"] = fixed_height
        if fixed_width:
            layout_updates["width"] = fixed_width
        fig.update_layout(**layout_updates)
        cfg = {**PLOTLY_CONFIG, "responsive": False}
    return pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=False,
        config=cfg,
        div_id=None,
    )


def country_color_map(countries: "list[str]") -> "dict[str, str]":
    """Assign stable colors for destination-country charts."""
    color_map = {}
    palette_idx = 0
    for country in countries:
        if country == "中國大陸":
            color_map[country] = COUNTRY_RED
        elif country == "美國":
            color_map[country] = COUNTRY_BLUE
        elif country == "其他":
            color_map[country] = COUNTRY_OTHER_GRAY
        else:
            color_map[country] = COUNTRY_PALETTE[palette_idx % len(COUNTRY_PALETTE)]
            palette_idx += 1
    return color_map


# ══════════════════════════════════════════════════════════════════════════════
# Chart builders
# ══════════════════════════════════════════════════════════════════════════════

def build_import_charts(df: pd.DataFrame) -> "dict[str, str]":
    """Return dict of chart HTML strings for import analysis."""
    df_i = df[df["direction"] == "I"].copy()
    charts = {}

    # 1. Monthly trend by category (area chart)
    monthly_cat = (
        df_i.groupby(["date", "category"])["value_kusd"]
        .sum().reset_index().sort_values("date")
    )
    monthly_cat["value_usd"] = monthly_cat["value_kusd"] * 1_000
    fig = px.area(
        monthly_cat, x="date", y="value_usd", color="category",
        color_discrete_sequence=DSET_COLORS,
        labels={"value_usd": "金額 (USD)", "date": "年月", "category": "類別"},
        title="月進口值 — 依類別",
        height=CHART_HEIGHT,
    )
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.25, font_size=11))
    charts["import_area"] = chart_html(fig)

    # 2. Monthly trend by HS code (line chart, top 8 by total)
    top8 = df_i.groupby("hs6")["value_kusd"].sum().nlargest(8).index.tolist()
    monthly_hs = (
        df_i[df_i["hs6"].isin(top8)]
        .groupby(["date", "hs6", "en_name"])["value_kusd"]
        .sum().reset_index().sort_values("date")
    )
    monthly_hs["label"] = monthly_hs["hs6"] + " " + monthly_hs["en_name"]
    monthly_hs["value_usd"] = monthly_hs["value_kusd"] * 1_000
    fig2 = px.line(
        monthly_hs, x="date", y="value_usd", color="label",
        color_discrete_sequence=DSET_COLORS,
        labels={"value_usd": "金額 (USD)", "date": "年月", "label": "HS Code"},
        title="月進口值 — 依 HS Code（前8大）",
        height=CHART_HEIGHT,
    )
    fig2.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.35, font_size=10))
    charts["import_lines"] = chart_html(fig2)

    return charts


def build_export_charts(df: pd.DataFrame) -> "dict[str, str]":
    df_e = df[df["direction"] == "E"].copy()
    if df_e.empty:
        return {}
    charts = {}

    monthly_cat = (
        df_e.groupby(["date", "category"])["value_kusd"]
        .sum().reset_index().sort_values("date")
    )
    monthly_cat["value_usd"] = monthly_cat["value_kusd"] * 1_000
    fig = px.area(
        monthly_cat, x="date", y="value_usd", color="category",
        color_discrete_sequence=DSET_COLORS,
        labels={"value_usd": "金額 (USD)", "date": "年月", "category": "類別"},
        title="月出口值 — 依類別",
        height=CHART_HEIGHT,
    )
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.25, font_size=11))
    charts["export_area"] = chart_html(fig)
    return charts


def build_china_charts(df: pd.DataFrame) -> "dict[str, str]":
    df_i = df[df["direction"] == "I"].copy()
    charts = {}

    # Bar chart: China share per HS code
    by_hs = df_i.groupby(["hs6", "en_name", "is_china"])["value_kusd"].sum().reset_index()
    total_hs = by_hs.groupby("hs6")["value_kusd"].sum().rename("total")
    china_hs = by_hs[by_hs["is_china"]].groupby("hs6")["value_kusd"].sum().rename("china")
    china_share = (
        pd.concat([total_hs, china_hs], axis=1).fillna(0)
        .assign(china_pct=lambda x: x["china"] / x["total"].replace(0, float("nan")) * 100)
        .reset_index()
        .merge(df_i[["hs6", "en_name", "category"]].drop_duplicates("hs6"), on="hs6", how="left")
        .sort_values("china_pct", ascending=True)
    )
    n_bars = china_share.dropna(subset=["china_pct"]).shape[0]
    bar_height = max(560, n_bars * 52 + 140)
    fig = px.bar(
        china_share.dropna(subset=["china_pct"]),
        x="china_pct", y="en_name", color="category", orientation="h",
        color_discrete_sequence=DSET_COLORS,
        labels={"china_pct": "中國佔比 (%)", "en_name": "商品", "category": "類別"},
        title="對中國進口依賴度（累計期間）",
    )
    fig.update_traces(
        hovertemplate="商品=%{y}<br>中國佔比=%{x:.1f}%<extra></extra>",
    )
    fig.update_layout(
        xaxis_range=[0, 118],
        yaxis=dict(tickfont=dict(size=13)),
        margin=dict(l=10, r=100, t=50, b=40),
        bargap=0.35,
        legend=dict(orientation="h", y=-0.08, font_size=11),
    )
    charts["china_bar"] = chart_html(fig, fixed_height=bar_height)

    # Line: China % trend for top 4 HS codes by value
    top4 = df_i.groupby("hs6")["value_kusd"].sum().nlargest(4).index.tolist()
    df_top4 = df_i[df_i["hs6"].isin(top4)].copy()
    mc = df_top4.groupby(["date", "hs6", "is_china"])["value_kusd"].sum().reset_index()
    tot_m = mc.groupby(["date", "hs6"])["value_kusd"].sum().rename("total").reset_index()
    chi_m = mc[mc["is_china"]].groupby(["date", "hs6"])["value_kusd"].sum().rename("china").reset_index()
    tc = tot_m.merge(chi_m, on=["date", "hs6"], how="left").fillna(0)
    tc["china_pct"] = tc["china"] / tc["total"].replace(0, float("nan")) * 100
    tc = tc.merge(df_i[["hs6", "en_name"]].drop_duplicates("hs6"), on="hs6", how="left")
    fig2 = px.line(
        tc.dropna(subset=["china_pct"]),
        x="date", y="china_pct", color="en_name",
        color_discrete_sequence=DSET_COLORS,
        labels={"china_pct": "中國佔比 (%)", "date": "年月", "en_name": "HS Code"},
        title="月對中依賴度趨勢（前4大 HS Code by value）",
        height=CHART_HEIGHT,
    )
    fig2.update_layout(
        hovermode="x unified",
        yaxis=dict(ticksuffix="%", range=[0, 110]),
        legend=dict(orientation="h", y=-0.3, font_size=10),
    )
    charts["china_trend"] = chart_html(fig2)

    return charts


def build_detail_charts(df: pd.DataFrame) -> "dict[str, str]":
    """One chart per HS code: annual trade partner breakdown."""
    df_i = df[df["direction"] == "I"].copy()
    charts = {}

    for hs6, info in HS_FLAT.items():
        df_hs = df_i[df_i["hs6"] == hs6]
        if df_hs.empty:
            continue

        top5 = (
            df_hs.groupby("country")["value_kusd"].sum()
            .nlargest(5).index.tolist()
        )
        df_hs2 = df_hs.copy()
        df_hs2["partner"] = df_hs2["country"].where(
            df_hs2["country"].isin(top5), other="其他"
        )
        partner_order = top5 + (["其他"] if "其他" in df_hs2["partner"].values else [])
        partner_color_map = country_color_map(partner_order)
        annual = (
            df_hs2.assign(year_label=df_hs2["date"].dt.year.astype(str))
            .groupby(["year_label", "partner"])["value_kusd"]
            .sum().reset_index()
        )
        annual["value_usd"] = annual["value_kusd"] * 1_000

        fig = px.bar(
            annual, x="year_label", y="value_usd", color="partner",
            color_discrete_map=partner_color_map,
            labels={"value_usd": "USD", "year_label": "年份", "partner": "貿易夥伴"},
            barmode="stack",
            height=320,
        )
        fig.update_layout(
            legend=dict(orientation="h", y=-0.3, font_size=10),
            margin=dict(t=10, b=10),
        )
        charts[hs6] = chart_html(fig, fixed_width=640)

    return charts


# ══════════════════════════════════════════════════════════════════════════════
# Export destination charts (battery finished goods: 850760 + 850790)
# ══════════════════════════════════════════════════════════════════════════════

BATTERY_HS = ["850760", "850790"]


def build_export_destination_charts(df: pd.DataFrame) -> "dict[str, str]":
    df_e = df[(df["direction"] == "E") & (df["hs6"].isin(BATTERY_HS))].copy()
    if df_e.empty:
        return {}

    charts = {}
    start_label = df_e["date"].min().strftime("%Y-%m")
    end_label = df_e["date"].max().strftime("%Y-%m")
    cutoff_12m = df_e["date"].max() - pd.DateOffset(months=11)

    # ── Top destinations bar chart (cumulative) ───────────────────────────────
    by_country = (
        df_e.groupby("country")["value_kusd"].sum()
        .sort_values(ascending=False)
        .head(15)
        .reset_index()
    )
    by_country["value_usd_bn"] = by_country["value_kusd"] * 1_000 / 1_000_000_000
    bar_countries = by_country["country"].tolist()
    bar_color_map = country_color_map(bar_countries)
    fig_bar = px.bar(
        by_country,
        x="value_usd_bn", y="country",
        orientation="h",
        color="country",
        color_discrete_map=bar_color_map,
        labels={"value_usd_bn": "出口值 (billion USD)", "country": "目的地"},
        title=f"台灣電池出口目的地（前15，累計：{start_label} – {end_label}）",
        height=460,
    )
    fig_bar.update_layout(
        yaxis={"categoryorder": "total ascending"},
        showlegend=False,
    )
    fig_bar.update_traces(
        hovertemplate="目的地=%{y}<br>出口值=%{x:.2f} billion USD<extra></extra>",
    )
    charts["export_dest_bar"] = chart_html(fig_bar)

    # ── Top destinations bar chart (last 12 months) ───────────────────────────
    by_country_12m = (
        df_e[df_e["date"] >= cutoff_12m]
        .groupby("country")["value_kusd"].sum()
        .sort_values(ascending=False)
        .head(15)
        .reset_index()
    )
    by_country_12m["value_usd_bn"] = by_country_12m["value_kusd"] * 1_000 / 1_000_000_000
    bar_12m_countries = by_country_12m["country"].tolist()
    bar_12m_color_map = country_color_map(bar_12m_countries)
    fig_bar_12m = px.bar(
        by_country_12m,
        x="value_usd_bn", y="country",
        orientation="h",
        color="country",
        color_discrete_map=bar_12m_color_map,
        labels={"value_usd_bn": "出口值 (billion USD)", "country": "目的地"},
        title=f"台灣電池出口目的地（前15，近12個月：{cutoff_12m.strftime('%Y-%m')} – {end_label}）",
        height=460,
    )
    fig_bar_12m.update_layout(
        yaxis={"categoryorder": "total ascending"},
        showlegend=False,
    )
    fig_bar_12m.update_traces(
        hovertemplate="目的地=%{y}<br>出口值=%{x:.2f} billion USD<extra></extra>",
    )
    charts["export_dest_bar_12m"] = chart_html(fig_bar_12m)

    # ── Monthly stacked bar by top 6 countries ────────────────────────────────
    top6 = by_country["country"].head(6).tolist()
    df_e["partner"] = df_e["country"].where(df_e["country"].isin(top6), other="其他")
    partner_order = top6 + (["其他"] if "其他" in df_e["partner"].values else [])
    partner_color_map = country_color_map(partner_order)
    monthly = (
        df_e.groupby(["date", "partner"])["value_kusd"]
        .sum().reset_index().sort_values("date")
    )
    monthly["value_usd"] = monthly["value_kusd"] * 1_000
    fig_monthly = px.bar(
        monthly,
        x="date", y="value_usd", color="partner",
        color_discrete_map=partner_color_map,
        labels={"value_usd": "出口值 (USD)", "date": "年月", "partner": "目的地"},
        title="台灣電池月出口值 — 依目的地",
        barmode="stack",
        height=CHART_HEIGHT,
    )
    fig_monthly.update_layout(legend=dict(orientation="h", y=-0.25, font_size=11))
    charts["export_monthly"] = chart_html(fig_monthly)

    # ── Annual comparison: top 6 countries ────────────────────────────────────
    df_e["year_label"] = df_e["date"].dt.year.astype(str)
    annual = (
        df_e.groupby(["year_label", "partner"])["value_kusd"]
        .sum().reset_index()
    )
    annual["value_usd"] = annual["value_kusd"] * 1_000
    fig_annual = px.bar(
        annual,
        x="year_label", y="value_usd", color="partner",
        color_discrete_map=partner_color_map,
        labels={"value_usd": "出口值 (USD)", "year_label": "年份", "partner": "目的地"},
        title="台灣電池年出口值 — 依目的地",
        barmode="stack",
        height=CHART_HEIGHT,
    )
    fig_annual.update_layout(legend=dict(orientation="h", y=-0.25, font_size=11))
    charts["export_annual"] = chart_html(fig_annual)

    # ── Line chart: top 6 countries trend ────────────────────────────────────
    monthly_line = (
        df_e[df_e["partner"] != "其他"]
        .groupby(["date", "partner"])["value_kusd"]
        .sum().reset_index().sort_values("date")
    )
    monthly_line["value_usd"] = monthly_line["value_kusd"] * 1_000
    fig_line = px.line(
        monthly_line,
        x="date", y="value_usd", color="partner",
        color_discrete_map=partner_color_map,
        labels={"value_usd": "出口值 (USD)", "date": "年月", "partner": "目的地"},
        title="主要出口目的地月趨勢（前6）",
        height=CHART_HEIGHT,
    )
    fig_line.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.25, font_size=11),
    )
    charts["export_lines"] = chart_html(fig_line)

    return charts


# ══════════════════════════════════════════════════════════════════════════════
# KPI summary table
# ══════════════════════════════════════════════════════════════════════════════

def build_kpi_table(df: pd.DataFrame) -> str:
    df_i = df[df["direction"] == "I"]
    df_e = df[df["direction"] == "E"]
    latest = df_i["date"].max()
    cutoff = latest - pd.DateOffset(months=11)
    df_12m = df_i[df_i["date"] >= cutoff]
    df_e_12m = df_e[df_e["date"] >= cutoff]

    rows = []
    for hs6, info in HS_FLAT.items():
        sub = df_i[df_i["hs6"] == hs6]
        sub12 = df_12m[df_12m["hs6"] == hs6]
        if sub.empty:
            continue
        total = sub["value_kusd"].sum()
        china = sub[sub["is_china"]]["value_kusd"].sum()
        pct = china / total * 100 if total > 0 else 0
        t12 = sub12["value_kusd"].sum()
        c12 = sub12[sub12["is_china"]]["value_kusd"].sum()
        p12 = c12 / t12 * 100 if t12 > 0 else 0
        e12 = df_e_12m[df_e_12m["hs6"] == hs6]["value_kusd"].sum()
        rows.append({
            "類別": info["category"].split("(")[0].strip(),
            "HS Code": hs6,
            "品名": info["tw_name"],
            "近12月進口值 (USD)": f"{int(t12 * 1_000):,}",
            "近12個月出口值 (USD)": f"{int(e12 * 1_000):,}",
            "近12月對中依賴": f"{p12:.1f}%",
        })
    if not rows:
        return "<p>No data</p>"

    def pct_style(val: str) -> str:
        try:
            v = float(val.replace("%", ""))
        except Exception:
            return ""
        if v >= 70:
            return "background-color:#fca5a5"
        elif v >= 40:
            return "background-color:#fde68a"
        return "background-color:#bbf7d0"

    PCT_COLS = {"近12月對中依賴"}
    NUMERIC_COLS = {"近12月進口值 (USD)", "近12個月出口值 (USD)"}
    cols = list(rows[0].keys())
    html = ['<table class="kpi-table"><thead><tr>']
    for c in cols:
        html.append(f"<th>{c}</th>")
    html.append("</tr></thead><tbody>")
    for row in rows:
        html.append("<tr>")
        for c in cols:
            styles = []
            if c in PCT_COLS:
                pct_css = pct_style(row[c])
                if pct_css:
                    styles.append(pct_css)
            if c in NUMERIC_COLS:
                styles.append("text-align:right")
            style = f' style="{";".join(styles)}"' if styles else ""
            html.append(f"<td{style}>{row[c]}</td>")
        html.append("</tr>")
    html.append("</tbody></table>")
    return "".join(html)


# ══════════════════════════════════════════════════════════════════════════════
# HTML template
# ══════════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🔋 台灣電池供應鏈進出口 Dashboard</title>
<!-- Plotly.js -->
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {{
    --accent:  #093A8C;
    --accent2: #314F78;
    --bg:      #D9EBF7;
    --card:    #ffffff;
    --border:  #99C0D3;
    --text:    #314F78;
    --muted:   #B5C3CE;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 1.5rem;
  }}
  h1 {{ font-size: 1.6rem; font-weight: 700; margin-bottom: .25rem; }}
  .subtitle {{ color: var(--muted); font-size: .85rem; margin-bottom: 1.5rem; }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
  }}
  .kpi-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
  }}
  .kpi-label {{ font-size: .78rem; color: var(--accent2); font-weight: 600; margin-bottom: .3rem; }}
  .kpi-value {{ font-size: 1.5rem; font-weight: 700; color: var(--accent); }}
  .kpi-sub {{ font-size: .8rem; color: var(--muted); margin-top: .15rem; }}

  /* Tabs */
  .tab-nav {{
    display: flex; gap: .5rem; flex-wrap: wrap;
    border-bottom: 2px solid var(--border);
    margin-bottom: 1.2rem;
  }}
  .tab-btn {{
    padding: .55rem 1.1rem;
    border: none; background: none; cursor: pointer;
    font-size: .9rem; color: var(--muted);
    border-bottom: 3px solid transparent;
    transition: all .15s;
    margin-bottom: -2px;
  }}
  .tab-btn:hover {{ color: var(--accent); }}
  .tab-btn.active {{ color: var(--accent); font-weight: 600; border-bottom-color: var(--accent); }}
  .tab-pane {{ display: none; }}
  .tab-pane.active {{ display: block; }}

  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
  }}
  .card h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: .8rem; color: var(--text); }}

  /* HS detail grid */
  .detail-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 1rem;
  }}
  .detail-chart-frame {{
    width: 100%;
    margin: 0 auto;
    overflow: hidden;
    display: flex;
    justify-content: center;
  }}

  /* KPI table */
  .kpi-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: .82rem;
  }}
  .kpi-table th, .kpi-table td {{
    padding: .55rem .75rem;
    border: 1px solid var(--border);
    text-align: left;
    white-space: nowrap;
  }}
  .kpi-table th {{ background: #D7E9F6; font-weight: 600; color: var(--accent2); }}
  .kpi-table tr:hover td {{ background: #f1f5f9; }}

  .updated {{ font-size: .8rem; color: var(--muted); margin-top: 2rem; text-align: right; }}
  a {{ color: var(--accent); }}
</style>
</head>
<body>

<h1>🔋 台灣電池供應鏈進出口</h1>
<p class="subtitle">
  資料來源：<a href="https://portal.sw.nat.gov.tw/APGA/GA30" target="_blank">財政部關務署統計資料查詢平台</a>
  &nbsp;|&nbsp; 資料期間：{date_range}
  &nbsp;|&nbsp; Dashboard 更新：{updated}
</p>

<!-- KPI cards -->
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">QoQ 出口電池成長最大</div>
    <div class="kpi-value">{kpi_qoq_country}</div>
    <div class="kpi-sub">季增率 {kpi_qoq_pct}　（鋰電池出口，最新季 vs 前季）</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">近12月出口值最高國別</div>
    <div class="kpi-value">{kpi_top_export_country}</div>
    <div class="kpi-sub">USD {kpi_top_export_value}　（鋰電池成品）</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">近12月進口原料總值</div>
    <div class="kpi-value">USD {kpi_material_import_b}B</div>
    <div class="kpi-sub">電池相關原物料（含 850790，不含 850760）</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">近12月原料進口中國佔比</div>
    <div class="kpi-value">{kpi_china_material_pct}%</div>
    <div class="kpi-sub">中國大陸佔原料進口值</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">近12個月進口鋰離子蓄電池總值</div>
    <div class="kpi-value">USD {kpi_li_ion_import_b}B</div>
    <div class="kpi-sub">HS 850760</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">近12個月出口鋰離子蓄電池總值</div>
    <div class="kpi-value">USD {kpi_li_ion_export_b}B</div>
    <div class="kpi-sub">HS 850760</div>
  </div>
</div>

<!-- Tab navigation -->
<div class="tab-nav">
  <button class="tab-btn active" onclick="showTab('summary')">📋 彙總表</button>
  <button class="tab-btn" onclick="showTab('import-trend')">📈 進口月趨勢</button>
  <button class="tab-btn" onclick="showTab('export-dest')">📤 電池出口目的地</button>
  <button class="tab-btn" onclick="showTab('china')">🇨🇳 中國依賴度</button>
  <button class="tab-btn" onclick="showTab('detail')">🏷️ HS Code 細目</button>
</div>

<!-- Tab: Summary -->
<div id="tab-summary" class="tab-pane active">
  <div class="card">
    <h3>各 HS Code 進口彙總（含對中依賴度）</h3>
    <div style="overflow-x:auto">{kpi_table}</div>
    <p style="font-size:.75rem;color:var(--muted);margin-top:.6rem">
      🟢 對中 &lt; 40%　🟡 40–70%　🔴 ≥ 70%
    </p>
  </div>
</div>

<!-- Tab: Import Trend -->
<div id="tab-import-trend" class="tab-pane">
  <div class="card">{import_area}</div>
  <div class="card">{import_lines}</div>
</div>

<!-- Tab: Export Destination -->
<div id="tab-export-dest" class="tab-pane">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
    <div class="card">{export_dest_bar}</div>
    <div class="card">{export_dest_bar_12m}</div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
    <div class="card">{export_annual}</div>
    <div class="card">{export_lines}</div>
  </div>
  <div class="card">{export_monthly}</div>
</div>

<!-- Tab: China Dependency -->
<div id="tab-china" class="tab-pane">
  <div class="card" style="overflow:visible">{china_bar}</div>
  <div class="card">{china_trend}</div>
</div>

<!-- Tab: HS Code Detail -->
<div id="tab-detail" class="tab-pane">
  <div class="detail-grid">
    {detail_cards}
  </div>
</div>

<p class="updated">Dashboard generated {updated} · <a href="https://github.com/deeper747/TWbattery" target="_blank">GitHub</a></p>

<script>
function showTab(name) {{
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}}
</script>
</body>
</html>
"""


def calc_kpis(df: pd.DataFrame) -> dict:
    """Calculate the headline KPI values."""
    latest = df["date"].max()

    # ── KPI 1: QoQ battery export growth — country with highest % growth ──────
    df_e_bat = df[(df["direction"] == "E") & (df["hs6"].isin(BATTERY_HS))].copy()
    kpi_qoq_country, kpi_qoq_pct = "—", "—"
    if not df_e_bat.empty:
        q_latest_start = latest - pd.DateOffset(months=2)   # latest 3-month window
        q_prev_start   = latest - pd.DateOffset(months=5)   # prior 3-month window
        q_prev_end     = latest - pd.DateOffset(months=3)

        q1 = df_e_bat[df_e_bat["date"] >= q_latest_start].groupby("country")["value_kusd"].sum()
        q0 = df_e_bat[
            (df_e_bat["date"] >= q_prev_start) & (df_e_bat["date"] <= q_prev_end)
        ].groupby("country")["value_kusd"].sum()

        combined = pd.concat([q0.rename("prev"), q1.rename("curr")], axis=1).fillna(0)
        combined = combined[combined["prev"] > 0]   # need non-zero base
        if not combined.empty:
            combined["qoq"] = (combined["curr"] - combined["prev"]) / combined["prev"] * 100
            best = combined["qoq"].idxmax()
            kpi_qoq_country = best
            kpi_qoq_pct = f"{combined.loc[best, 'qoq']:+.1f}%"

    # ── KPI 2: Top export country (battery, last 12m) ─────────────────────────
    cutoff_12m = latest - pd.DateOffset(months=11)
    df_e_12m = df_e_bat[df_e_bat["date"] >= cutoff_12m] if not df_e_bat.empty else pd.DataFrame()
    kpi_top_export_country, kpi_top_export_value = "—", "—"
    if not df_e_12m.empty:
        by_c = df_e_12m.groupby("country")["value_kusd"].sum()
        top_c = by_c.idxmax()
        kpi_top_export_country = top_c
        kpi_top_export_value = f"{int(by_c[top_c]):,}K"

    # ── KPI 3: Raw material imports last 12m (exclude lithium-ion batteries) ──
    RAW_HS = [h for h in df["hs6"].unique() if h != "850760"]
    df_raw_12m = df[
        (df["direction"] == "I") &
        (df["hs6"].isin(RAW_HS)) &
        (df["date"] >= cutoff_12m)
    ]
    raw_total = df_raw_12m["value_kusd"].sum()
    kpi_material_import_b = f"{raw_total/1_000_000:.2f}" if raw_total else "—"

    # ── KPI 4: China share of raw material imports last 12m ───────────────────
    raw_china = df_raw_12m[df_raw_12m["is_china"]]["value_kusd"].sum()
    kpi_china_material_pct = f"{raw_china/raw_total*100:.1f}" if raw_total else "—"

    # ── KPI 5-6: Lithium-ion batteries last 12m (HS 850760) ──────────────────
    df_li_ion_import_12m = df[
        (df["direction"] == "I") &
        (df["hs6"] == "850760") &
        (df["date"] >= cutoff_12m)
    ]
    df_li_ion_export_12m = df[
        (df["direction"] == "E") &
        (df["hs6"] == "850760") &
        (df["date"] >= cutoff_12m)
    ]
    li_ion_import_total = df_li_ion_import_12m["value_kusd"].sum()
    li_ion_export_total = df_li_ion_export_12m["value_kusd"].sum()
    kpi_li_ion_import_b = f"{li_ion_import_total/1_000_000:.2f}" if li_ion_import_total else "—"
    kpi_li_ion_export_b = f"{li_ion_export_total/1_000_000:.2f}" if li_ion_export_total else "—"

    return dict(
        kpi_qoq_country=kpi_qoq_country,
        kpi_qoq_pct=kpi_qoq_pct,
        kpi_top_export_country=kpi_top_export_country,
        kpi_top_export_value=kpi_top_export_value,
        kpi_material_import_b=kpi_material_import_b,
        kpi_china_material_pct=kpi_china_material_pct,
        kpi_li_ion_import_b=kpi_li_ion_import_b,
        kpi_li_ion_export_b=kpi_li_ion_export_b,
    )


def main():
    print("Loading processed data...")
    df = load_data()

    df_i = df[df["direction"] == "I"]
    latest = df["date"].max()
    earliest = df_i["date"].min()

    print("Building charts...")
    imp_charts = build_import_charts(df)
    china_charts = build_china_charts(df)
    detail_charts = build_detail_charts(df)
    exp_dest_charts = build_export_destination_charts(df)

    no_data_card = '<div class="card"><p style="color:var(--muted);padding:1rem">尚無出口資料。請下載出口 CSV 後重新處理。</p></div>'

    detail_cards_html = ""
    for hs6, chart in detail_charts.items():
        info = HS_FLAT.get(hs6, {})
        detail_cards_html += (
            f'<div class="card"><h3>{hs6} {info.get("tw_name","")}</h3>'
            f'<div class="detail-chart-frame">{chart}</div></div>\n'
        )

    updated = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_range = f"{earliest.strftime('%Y-%m')} – {latest.strftime('%Y-%m')}"
    kpis = calc_kpis(df)

    html = HTML_TEMPLATE.format(
        date_range=date_range,
        updated=updated,
        kpi_table=build_kpi_table(df),
        import_area=imp_charts.get("import_area", ""),
        import_lines=imp_charts.get("import_lines", ""),
        export_dest_bar=exp_dest_charts.get("export_dest_bar", no_data_card),
        export_dest_bar_12m=exp_dest_charts.get("export_dest_bar_12m", no_data_card),
        export_annual=exp_dest_charts.get("export_annual", ""),
        export_lines=exp_dest_charts.get("export_lines", ""),
        export_monthly=exp_dest_charts.get("export_monthly", ""),
        china_bar=china_charts.get("china_bar", ""),
        china_trend=china_charts.get("china_trend", ""),
        detail_cards=detail_cards_html,
        **kpis,
    )

    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"\n✅ Dashboard written → {OUT_HTML}")
    print(f"   Commit & push, then enable GitHub Pages (source: /docs) to share.")
    print(f"   Local preview: open docs/index.html in browser.")


if __name__ == "__main__":
    main()
