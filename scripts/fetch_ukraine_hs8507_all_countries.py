"""
Ukraine imports of HS 8507 (electric accumulators) — all source countries
Source files: data/raw/country_goods/
Outputs:
  - data/processed/ukraine_hs8507_all_countries.csv   (full detail)
  - data/processed/ukraine_hs8507_by_country_year.csv (pivoted summary)
  - data/processed/ukraine_hs8507_stacked_value.png
  - data/processed/ukraine_hs8507_stacked_weight.png
"""

import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "country_goods")
OUT_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(OUT_DIR, exist_ok=True)

HS_PREFIX = "8507"

# ── Color palette — mirrors DSET_COLORS in generate_dashboard.py ──────────────
# Fixed per-country assignment so all 4 charts are consistent
COUNTRY_COLORS = {
    "China":          "#D65740",  # coral red  — dominant supplier
    "Vietnam":        "#093A8C",  # DSET dark navy
    "Taiwan":         "#F0943A",  # DSET orange — highlight
    "Czech Republic": "#314F78",  # DSET medium navy
    "Italy":          "#2E7D5E",  # forest green
    "Poland":         "#859BD5",  # DSET periwinkle
    "USA":            "#F2C94C",  # warm yellow
    "Bulgaria":       "#5B5EA6",  # slate purple
    "Germany":        "#4A9B8E",  # teal green
    "Slovenia":       "#E8892A",  # amber
    "Kazakhstan":     "#99C0D3",  # DSET light teal
    "Turkey":         "#2B3A52",  # DSET footer slate
    "South Korea":    "#B56576",  # muted rose
    "Malaysia":       "#7A9E7E",  # sage green
    "Others":         "#9CA3AF",  # neutral grey
}

COL_COUNTRY = 0
COL_HS      = 3
COL_DESC    = 4
COL_IMP_VAL = 5   # thousands USD
COL_IMP_WT  = 7   # metric tons

# ── Ukrainian → English country names ─────────────────────────────────────────
COUNTRY_EN = {
    "Австралія": "Australia",
    "Австрія": "Austria",
    "Азербайджан": "Azerbaijan",
    "Афганістан": "Afghanistan",
    "Беліз": "Belize",
    "Бельгія": "Belgium",
    "Болгарія": "Bulgaria",
    "Велика Британія": "United Kingdom",
    "В'єтнам": "Vietnam",
    "Вірменія": "Armenia",
    "Гана": "Ghana",
    "Гонконг": "Hong Kong",
    "Греція": "Greece",
    "Грузія": "Georgia",
    "Данія": "Denmark",
    "Естонія": "Estonia",
    "Єгипет": "Egypt",
    "Ізраїль": "Israel",
    "Індія": "India",
    "Індонезія": "Indonesia",
    "Ірландiя": "Ireland",
    "Іспанія": "Spain",
    "Італiя": "Italy",
    "Казахстан": "Kazakhstan",
    "Канада": "Canada",
    "Китай": "China",
    "Кіпр": "Cyprus",
    "Корея, Республіка": "South Korea",
    "Корея, Республіка ": "South Korea",
    "Латвія": "Latvia",
    "Литва": "Lithuania",
    "Люксембург": "Luxembourg",
    "Малайзія": "Malaysia",
    "Марокко": "Morocco",
    "Мексика": "Mexico",
    "Молдова, Республіка": "Moldova",
    "Нідерланди": "Netherlands",
    "Німеччина": "Germany",
    "Норвегія": "Norway",
    "Польща": "Poland",
    "Португалія": "Portugal",
    "Республіка Північна Македонія": "North Macedonia",
    "Румунія": "Romania",
    "Сербія": "Serbia",
    "Сингапур": "Singapore",
    "Словаччина": "Slovakia",
    "Словенія": "Slovenia",
    "США": "USA",
    "Таїланд": "Thailand",
    "Тайвань, провінція Китаю": "Taiwan",
    "Туреччина": "Turkey",
    "Угорщина": "Hungary",
    "Узбекистан": "Uzbekistan",
    "Україна": "Ukraine",
    "Філіппіни": "Philippines",
    "Фінляндія": "Finland",
    "Франція": "France",
    "Хорватія": "Croatia",
    "Чехія": "Czech Republic",
    "Швейцарія": "Switzerland",
    "Швеція": "Sweden",
    "Шри-Ланка": "Sri Lanka",
    "Японія": "Japan",
    "Південна Африка": "South Africa",
    "Білорусь": "Belarus",
    "Об'єднані Арабські Емірати": "UAE",
    "Саудівська Аравія": "Saudi Arabia",
    "Маршаллові острови": "Marshall Islands",
    "Танзанія, Об'єднана Республіка": "Tanzania",
    "Конго, Демократична Республіка": "DR Congo",
    "Центральноафриканська Республіка": "CAR",
    "Республіка Північна Македонія": "North Macedonia",
    "Палау ": "Palau",
    "Чорногорія": "Montenegro",
    "Чилі": "Chile",
    "Перу": "Peru",
    "Куба": "Cuba",
    "Ірак": "Iraq",
    "Туніс": "Tunisia",
    "Уганда": "Uganda",
    "Малі": "Mali",
    "Гана": "Ghana",
    "Вірменія": "Armenia",
    "Грузія": "Georgia",
    "Нова Зеландія": "New Zealand",
    "Захiдна Сахара": "Western Sahara",
    "Західна Сахара": "Western Sahara",
}


def translate_country(name):
    name = str(name).strip()
    return COUNTRY_EN.get(name, name)


def parse_year(fname):
    m = re.search(r"(\d{4})", fname)
    return int(m.group(1)) if m else None


def parse_period(fname):
    m = re.match(r"^(\d+)\s*month", fname, re.IGNORECASE)
    months = int(m.group(1)) if m else 12
    return months


def load_file(path):
    df = pd.read_excel(path, dtype=str, header=None)
    df = df.iloc[4:].reset_index(drop=True)
    df[COL_COUNTRY] = df[COL_COUNTRY].ffill()
    return df


def to_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "").str.replace(" ", "").str.strip(),
        errors="coerce"
    ).fillna(0)


# ── Load all files ─────────────────────────────────────────────────────────────
files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx"))
records = []

for fname in files:
    year = parse_year(fname)
    months = parse_period(fname)
    if year is None:
        continue

    path = os.path.join(DATA_DIR, fname)
    print(f"Reading {fname} ...")

    df = load_file(path)
    mask_hs = df[COL_HS].astype(str).str.startswith(HS_PREFIX)
    filtered = df[mask_hs].copy()

    print(f"  -> {len(filtered)} HS 8507 rows")

    for _, row in filtered.iterrows():
        country_ua = str(row[COL_COUNTRY]).strip()
        records.append({
            "Year":              year,
            "Months":            months,
            "Country_UA":        country_ua,
            "Country":           translate_country(country_ua),
            "HS_Code":           str(row[COL_HS]).strip(),
            "Import_Value_TUSD": row[COL_IMP_VAL],
            "Import_NetWt_t":    row[COL_IMP_WT],
        })

# ── Build DataFrame ────────────────────────────────────────────────────────────
df_all = pd.DataFrame(records)
df_all["Import_Value_TUSD"] = to_num(df_all["Import_Value_TUSD"])
df_all["Import_NetWt_t"]    = to_num(df_all["Import_NetWt_t"])

# Remove zero rows (countries with no trade)
df_all = df_all[(df_all["Import_Value_TUSD"] > 0) | (df_all["Import_NetWt_t"] > 0)]

# Save full detail
detail_path = os.path.join(OUT_DIR, "ukraine_hs8507_all_countries.csv")
df_all.to_csv(detail_path, index=False, encoding="utf-8-sig")
print(f"\nSaved detail: {detail_path}")

# ── Pivot by Country × Year ────────────────────────────────────────────────────
piv_val = (
    df_all.groupby(["Country", "Year"])["Import_Value_TUSD"]
    .sum().reset_index()
    .pivot(index="Country", columns="Year", values="Import_Value_TUSD")
    .fillna(0)
)
piv_wt = (
    df_all.groupby(["Country", "Year"])["Import_NetWt_t"]
    .sum().reset_index()
    .pivot(index="Country", columns="Year", values="Import_NetWt_t")
    .fillna(0)
)

pivot_path = os.path.join(OUT_DIR, "ukraine_hs8507_by_country_year.csv")
piv_val.to_csv(pivot_path, encoding="utf-8-sig")
print(f"Saved pivot (value): {pivot_path}")

# ── Stacked bar chart helper ───────────────────────────────────────────────────
TOP_N = 10   # show top N countries per year

def make_stacked_bar(piv, unit_label, filename, ylabel, title):
    # Pick top N countries from the most recent full year of this metric
    years = sorted(piv.columns)
    last_full_year = max(y for y in years if y < 2026)
    featured = (
        piv[last_full_year]
        .sort_values(ascending=False)
        .head(TOP_N)
        .index.tolist()
    )

    other_countries = piv.index.difference(featured)

    data = piv.loc[featured].copy()
    if len(other_countries) > 0:
        data.loc["Others"] = piv.loc[other_countries].sum()

    # Order: featured sorted by last full year (descending), Others last
    order = featured + (["Others"] if len(other_countries) > 0 else [])
    data = data.loc[order]

    years = sorted(piv.columns)
    data = data[years]

    # ── Colors ────────────────────────────────────────────────────────────────
    fallback = plt.get_cmap("tab20")
    colors = [
        COUNTRY_COLORS.get(c, fallback(i / max(len(data), 1)))
        for i, c in enumerate(data.index)
    ]

    # ── Build year labels (add * for partial year) ─────────────────────────────
    partial_years = (
        df_all[df_all["Months"] < 12]["Year"].unique().tolist()
    )
    xlabels = [
        f"{y}*" if y in partial_years else str(y) for y in years
    ]

    fig, ax = plt.subplots(figsize=(12, 6))

    bottom = [0] * len(years)
    bars = []
    for i, country in enumerate(data.index):
        vals = data.loc[country, years].values.astype(float)
        b = ax.bar(xlabels, vals, bottom=bottom, color=colors[i],
                   label=country, width=0.6)
        bars.append(b)
        bottom = [bottom[j] + vals[j] for j in range(len(years))]

    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Year  (* = partial year)", fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{x:,.0f}"
    ))
    ax.legend(
        loc="upper left", fontsize=8,
        framealpha=0.9, ncol=2
    )
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, filename)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved chart: {out_path}")


def make_ranking_table(df_src, metric_col, metric_label, filename):
    """
    For each year: top 3 countries + Taiwan, with rank and value.
    Saves a wide CSV with columns:
      Year | #1 Country | #1 Value | #2 Country | #2 Value | #3 Country | #3 Value
           | Taiwan Rank | Taiwan Value
    """
    rows = []
    for year, grp in df_src.groupby("Year"):
        ranked = (
            grp.groupby("Country")[metric_col]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        ranked["Rank"] = ranked.index + 1

        top3 = ranked.head(3)
        taiwan_row = ranked[ranked["Country"] == "Taiwan"]

        row = {"Year": year}
        for i, r in top3.iterrows():
            n = r["Rank"]
            row[f"#{n} Country"] = r["Country"]
            row[f"#{n} {metric_label}"] = r[metric_col]

        if not taiwan_row.empty:
            row["Taiwan Rank"] = int(taiwan_row.iloc[0]["Rank"])
            row[f"Taiwan {metric_label}"] = taiwan_row.iloc[0][metric_col]
        else:
            row["Taiwan Rank"] = "N/A"
            row[f"Taiwan {metric_label}"] = 0

        rows.append(row)

    out = pd.DataFrame(rows).sort_values("Year").reset_index(drop=True)
    path = os.path.join(OUT_DIR, filename)
    out.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Saved ranking table: {path}")
    print(out.to_string(index=False))
    print()
    return out


print("\n── Ranking Table: Import Value (thousand USD) ──")
make_ranking_table(
    df_all, "Import_Value_TUSD", "Value (TUSD)",
    "ukraine_hs8507_ranking_value.csv",
)

print("── Ranking Table: Net Weight (metric tons) ──")
make_ranking_table(
    df_all, "Import_NetWt_t", "Weight (t)",
    "ukraine_hs8507_ranking_weight.csv",
)


make_stacked_bar(
    piv_val,
    unit_label="TUSD",
    filename="ukraine_hs8507_stacked_value.png",
    ylabel="Import Value (thousand USD)",
    title="Ukraine Imports of HS 8507 (Electric Accumulators) by Source Country\n"
          "Import Value (thousand USD)",
)

make_stacked_bar(
    piv_wt,
    unit_label="tonnes",
    filename="ukraine_hs8507_stacked_weight.png",
    ylabel="Net Weight (metric tons)",
    title="Ukraine Imports of HS 8507 (Electric Accumulators) by Source Country\n"
          "Net Weight (metric tons)",
)

def make_line_chart(piv, filename, ylabel, title, log_scale=False):
    # Exclude partial years (2026)
    partial_years = df_all[df_all["Months"] < 12]["Year"].unique().tolist()
    years = [y for y in sorted(piv.columns) if y not in partial_years]

    last_full_year = max(years)
    featured = (
        piv[last_full_year]
        .sort_values(ascending=False)
        .head(TOP_N)
        .index.tolist()
    )

    xlabels = [str(y) for y in years]

    fallback = plt.get_cmap("tab10")
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, country in enumerate(featured):
        vals = piv.loc[country, years].values.astype(float)
        if log_scale:
            vals = vals.clip(min=1)  # avoid log(0)
        color = COUNTRY_COLORS.get(country, fallback(i / max(len(featured), 1)))
        ax.plot(xlabels, vals, label=country, color=color,
                linewidth=2.5 if country == "Taiwan" else 1.5,
                marker="o", markersize=5,
                zorder=3 if country == "Taiwan" else 2)

    if log_scale:
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f"{x:,.0f}"
        ))
    else:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f"{x:,.0f}"
        ))

    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Year", fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9, ncol=2)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, filename)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved chart: {out_path}")


make_line_chart(
    piv_val,
    filename="ukraine_hs8507_line_value.png",
    ylabel="Import Value (thousand USD, log scale)",
    title="Ukraine Imports of HS 8507 (Electric Accumulators) by Source Country\n"
          "Import Value (thousand USD)",
    log_scale=True,
)

make_line_chart(
    piv_wt,
    filename="ukraine_hs8507_line_weight.png",
    ylabel="Net Weight (metric tons)",
    title="Ukraine Imports of HS 8507 (Electric Accumulators) by Source Country\n"
          "Net Weight (metric tons)",
)

print("\nDone.")
