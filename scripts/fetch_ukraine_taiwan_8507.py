"""
Ukraine imports from Taiwan — HS code 8507 (electric accumulators)
Source files: data/raw/country_goods/
Units: Import value = thousands USD; Net weight = metric tons

Taiwan in Ukrainian: Тайвань, провінція Китаю
"""

import os
import re
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "country_goods")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "ukraine_taiwan_8507.csv")

TAIWAN_KEYWORD = "Тайвань"
HS_PREFIX = "8507"

# Ukrainian → English translations
COUNTRY_EN = {
    "Тайвань, провінція Китаю": "Taiwan, Province of China",
}

DESC_EN = {
    "Акумулятори електричні та сепаратори для них": "Electric accumulators and separators therefor",
}

# Column indices (0-based, header=None)
COL_COUNTRY  = 0
COL_HS       = 3
COL_DESC     = 4
COL_IMP_VAL  = 5   # Import value (thousands USD)
COL_IMP_WT   = 7   # Import net weight (metric tons)


def parse_year_from_filename(fname):
    """Extract year from filenames like '12 month_2024_country_goods.xlsx'."""
    m = re.search(r"(\d{4})", fname)
    return int(m.group(1)) if m else None


def parse_period_label(fname):
    """Extract period label, e.g. '12 month' or '03 month'."""
    m = re.match(r"^(\d+\s*month)", fname, re.IGNORECASE)
    return m.group(1) if m else "?"


def load_file(path):
    """Load Excel file, forward-fill country column, return DataFrame."""
    df = pd.read_excel(path, dtype=str, header=None)
    # Skip header rows (rows 0-3); data starts at row 4
    df = df.iloc[4:].reset_index(drop=True)
    # Forward-fill country name (only appears on first row of each country block)
    df[COL_COUNTRY] = df[COL_COUNTRY].ffill()
    return df


def filter_taiwan_8507(df):
    """Return rows where country contains Тайвань and HS code starts with 8507."""
    mask_tw = df[COL_COUNTRY].astype(str).str.contains(TAIWAN_KEYWORD, na=False)
    mask_hs = df[COL_HS].astype(str).str.startswith(HS_PREFIX)
    return df[mask_tw & mask_hs].copy()


def to_number(series):
    """Convert string series to numeric, stripping spaces and commas."""
    return pd.to_numeric(
        series.astype(str).str.replace(",", "").str.replace(" ", "").str.strip(),
        errors="coerce"
    )


def main():
    files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx"))
    if not files:
        print(f"No .xlsx files found in {DATA_DIR}")
        return

    records = []

    for fname in files:
        year = parse_year_from_filename(fname)
        period = parse_period_label(fname)
        if year is None:
            continue

        path = os.path.join(DATA_DIR, fname)
        print(f"Reading {fname} ...")

        df = load_file(path)
        filtered = filter_taiwan_8507(df)

        if filtered.empty:
            print(f"  -> No Taiwan 8507 rows found")
            continue

        for _, row in filtered.iterrows():
            country_raw = str(row[COL_COUNTRY]).strip()
            desc_raw    = str(row[COL_DESC]).strip()
            records.append({
                "Year":               year,
                "Period":             period,
                "Country":            COUNTRY_EN.get(country_raw, country_raw),
                "HS_Code":            str(row[COL_HS]).strip(),
                "Description":        DESC_EN.get(desc_raw, desc_raw),
                "Import_Value_TUSD":  row[COL_IMP_VAL],   # thousands USD
                "Import_NetWeight_t": row[COL_IMP_WT],    # metric tons
            })
            print(f"  HS {row[COL_HS]} | value={row[COL_IMP_VAL]} TUSD | weight={row[COL_IMP_WT]} t")

    if not records:
        print("\nNo data found across all files.")
        return

    result = pd.DataFrame(records)
    result["Import_Value_TUSD"]  = to_number(result["Import_Value_TUSD"])
    result["Import_NetWeight_t"] = to_number(result["Import_NetWeight_t"])

    # Sort
    result = result.sort_values(["Year", "HS_Code"]).reset_index(drop=True)

    # ── Summary table ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Ukraine Imports from Taiwan — HS 8507 (Electric Accumulators)")
    print("Value: thousands USD  |  Net Weight: metric tons")
    print("=" * 70)

    # Aggregate by year (sum across HS sub-codes if any)
    summary = (
        result
        .groupby(["Year", "Period"], as_index=False)
        .agg(
            Import_Value_TUSD  = ("Import_Value_TUSD",  "sum"),
            Import_NetWeight_t = ("Import_NetWeight_t", "sum"),
            HS_Codes           = ("HS_Code", lambda x: ", ".join(sorted(x.unique()))),
        )
        .sort_values("Year")
    )

    summary["Import_Value_USD_M"] = (summary["Import_Value_TUSD"] / 1000).round(3)

    print(
        summary[["Year", "Period", "HS_Codes",
                  "Import_Value_TUSD", "Import_Value_USD_M",
                  "Import_NetWeight_t"]]
        .rename(columns={
            "Import_Value_TUSD":  "Value (TUSD)",
            "Import_Value_USD_M": "Value (M USD)",
            "Import_NetWeight_t": "Net Weight (t)",
        })
        .to_string(index=False)
    )

    # ── Detail table ───────────────────────────────────────────────────────────
    print("\n── Detail (all sub-codes) ──")
    print(
        result[["Year", "Period", "HS_Code", "Description",
                 "Import_Value_TUSD", "Import_NetWeight_t"]]
        .to_string(index=False)
    )

    # ── Save ───────────────────────────────────────────────────────────────────
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\nSaved detail to: {OUTPUT_FILE}")

    summary_path = OUTPUT_FILE.replace(".csv", "_summary.csv")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"Saved summary to: {summary_path}")


if __name__ == "__main__":
    main()
