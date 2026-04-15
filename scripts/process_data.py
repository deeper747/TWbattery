#!/usr/bin/env python3
"""
process_data.py — 處理從關務署下載的 CSV，輸出標準化資料供 dashboard 使用
Processes raw Taiwan Customs CSV files into a clean, combined dataset.

Output: data/processed/battery_trade.parquet (+ .csv backup)
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import HS_FLAT, CHINA_LABELS

RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Column name normalisation ──────────────────────────────────────────────────
# The customs portal may use slightly different header text depending on
# query settings. COLUMN_MAP maps known variants → our standard names.
COLUMN_MAP = {
    # Direction (進出口別 column in portal CSV)
    "進出口別": "direction_raw",
    # Date — portal uses ROC year like "109年1月"
    "日期": "date_raw",
    # HS code
    "貨品號列": "hs6",
    "稅則號別": "hs6",
    "商品代號": "hs6",
    "HS CODE": "hs6",
    # Description
    "中文貨名": "description",
    "貨品名稱": "description",
    "品名": "description",
    "英文貨名": "description_en",
    # Country
    "國家": "country",
    "國別": "country",
    "貿易夥伴": "country",
    "出口至": "country",
    "進口自": "country",
    # Value — portal uses "美元(千元)"
    "美元(千元)": "value_kusd",
    "美元（千元）": "value_kusd",
    # Legacy column names (other query modes)
    "年份": "year",
    "月份": "month",
    "年月": "ym",
    "進口值（千美元）": "value_kusd",
    "進口值(千美元)": "value_kusd",
    "出口值（千美元）": "value_kusd",
    "出口值(千美元)": "value_kusd",
    "進出口值（千美元）": "value_kusd",
    # Weight — optional
    "淨重（公噸）": "net_weight_mt",
    "淨重(公噸)": "net_weight_mt",
    "淨重": "net_weight_mt",
}


def _detect_direction(filename: str) -> str:
    """Infer I/E from filename, default to unknown."""
    fn = filename.upper()
    if "_I_" in fn or fn.startswith("I_") or "IMPORT" in fn or "進口" in fn:
        return "I"
    if "_E_" in fn or fn.startswith("E_") or "EXPORT" in fn or "出口" in fn:
        return "E"
    return "?"


def _read_csv_flexible(path: Path) -> pd.DataFrame:
    """
    Read Taiwan Customs portal CSV (cp950/Big5, 2 metadata rows, then header).
    Returns a DataFrame with renamed columns or raises ValueError.
    """
    content = None
    for enc in ("cp950", "big5hkscs", "utf-8-sig", "utf-8"):
        try:
            content = path.read_text(encoding=enc, errors="strict")
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if content is None:
        content = path.read_text(encoding="cp950", errors="replace")

    lines = content.splitlines()

    # Find the header row: first line that (a) contains a column keyword AND
    # (b) has at least 3 comma-separated fields (rules out single-column notes)
    header_idx = None
    HEADER_KEYWORDS = ("貨品號列", "稅則號別", "進出口別", "年份", "年月")
    for i, line in enumerate(lines):
        if line.count(",") >= 3 and any(k in line for k in HEADER_KEYWORDS):
            header_idx = i
            break

    if header_idx is None:
        header_idx = 0

    import io
    data_text = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(data_text), dtype=str)
    df.columns = df.columns.str.strip()

    # Rename columns
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    return df


def _normalise_hs6(series: pd.Series) -> pd.Series:
    """Strip dots, dashes, spaces; keep first 6 digits."""
    return (
        series.astype(str)
        .str.replace(r"[.\-\s]", "", regex=True)
        .str[:6]
    )


def _parse_roc_date(series: pd.Series) -> pd.DataFrame:
    """
    Parse ROC (民國) date strings like '109年1月' → year=2020, month=1.
    Also handles Gregorian '2020年1月' and plain YYYYMM strings.
    Returns a DataFrame with 'year' and 'month' int columns.
    """
    import re
    years, months = [], []
    for val in series.astype(str):
        m = re.search(r"(\d+)年(\d+)月", val)
        if m:
            y, mo = int(m.group(1)), int(m.group(2))
            # If ROC year (< 1900 range), convert: ROC year + 1911 = Gregorian
            if y < 1000:
                y += 1911
            years.append(y)
            months.append(mo)
        else:
            # Try plain YYYYMM
            digits = re.sub(r"\D", "", val)
            if len(digits) >= 6:
                years.append(int(digits[:4]))
                months.append(int(digits[4:6]))
            else:
                years.append(None)
                months.append(None)
    return pd.DataFrame({"year": years, "month": months})


def _split_ym(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure year and month columns exist."""
    if "date_raw" in df.columns:
        parsed = _parse_roc_date(df["date_raw"])
        df["year"] = parsed["year"]
        df["month"] = parsed["month"]
    elif "ym" in df.columns:
        df["year"] = df["ym"].str[:4].astype(int)
        df["month"] = df["ym"].str[4:6].astype(int)
    elif "year" in df.columns and "month" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
    else:
        raise ValueError("Cannot find year/month columns in data")
    return df


def _direction_from_raw(series: pd.Series) -> pd.Series:
    """
    Map portal's 進出口別 values to 'I' / 'E'.
    e.g. '進口總值(含復進口)' → 'I', '出口總值(含復出口)' → 'E'
    """
    return series.astype(str).map(
        lambda v: "I" if "進口" in v else ("E" if "出口" in v else "?")
    )


def process_single_file(path: Path) -> pd.DataFrame:
    print(f"  Processing {path.name}")

    df = _read_csv_flexible(path)
    df = _split_ym(df)

    # Direction: prefer direction_raw column, fall back to filename
    if "direction_raw" in df.columns:
        df["direction"] = _direction_from_raw(df["direction_raw"])
    else:
        df["direction"] = _detect_direction(path.name)

    # Normalise HS code
    if "hs6" not in df.columns:
        raise ValueError(f"No HS code column found in {path.name}. Available: {list(df.columns)}")
    df["hs6"] = _normalise_hs6(df["hs6"])

    # Keep only our target HS codes
    df = df[df["hs6"].isin(HS_FLAT.keys())].copy()
    if df.empty:
        print(f"    [WARN] No matching HS codes found in {path.name}")
        return pd.DataFrame()

    # Merge category info
    df["category"] = df["hs6"].map(lambda c: HS_FLAT.get(c, {}).get("category", "Unknown"))
    df["tw_name"] = df["hs6"].map(lambda c: HS_FLAT.get(c, {}).get("tw_name", c))
    df["en_name"] = df["hs6"].map(lambda c: HS_FLAT.get(c, {}).get("en_name", c))

    # Value column (already mapped to value_kusd by COLUMN_MAP)
    if "value_kusd" in df.columns:
        df["value_kusd"] = (
            pd.to_numeric(df["value_kusd"].astype(str).str.replace(",", "", regex=False), errors="coerce")
            .fillna(0)
        )
    else:
        df["value_kusd"] = 0.0
        print(f"    [WARN] No value column found; setting value_kusd = 0")

    # Flag China
    if "country" in df.columns:
        df["is_china"] = df["country"].isin(CHINA_LABELS)
    else:
        df["country"] = "Unknown"
        df["is_china"] = False

    # Add date column (first day of month)
    df["date"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01",
        errors="coerce",
    )

    keep_cols = [
        "date", "year", "month", "direction",
        "hs6", "tw_name", "en_name", "category",
        "country", "is_china", "value_kusd",
    ]
    if "net_weight_mt" in df.columns:
        df["net_weight_mt"] = pd.to_numeric(
            df["net_weight_mt"].str.replace(",", "", regex=False), errors="coerce"
        ).fillna(0)
        keep_cols.append("net_weight_mt")

    return df[[c for c in keep_cols if c in df.columns]].dropna(subset=["date"])


def main():
    raw_files = sorted(RAW_DIR.glob("*.csv"))
    if not raw_files:
        print(f"[ERROR] No CSV files found in {RAW_DIR}")
        print("  → Run  python scripts/fetch_data.py  or see  data/MANUAL_DOWNLOAD.md")
        return

    print(f"Found {len(raw_files)} CSV file(s) in {RAW_DIR}")
    frames = []
    for f in raw_files:
        try:
            df = process_single_file(f)
            if not df.empty:
                frames.append(df)
        except Exception as e:
            print(f"  [ERROR] {f.name}: {e}")

    if not frames:
        print("[ERROR] No data could be processed. Check file formats.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["date", "direction", "hs6", "country"])
    combined = combined.drop_duplicates()

    # ── Output ────────────────────────────────────────────────────────────────
    parquet_path = OUT_DIR / "battery_trade.parquet"
    csv_path = OUT_DIR / "battery_trade.csv"

    combined.to_parquet(parquet_path, index=False)
    combined.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(f"\n✅ Processed {len(combined):,} rows")
    print(f"   Date range : {combined['date'].min().date()} – {combined['date'].max().date()}")
    print(f"   HS codes   : {combined['hs6'].nunique()} unique codes")
    print(f"   Countries  : {combined['country'].nunique()} unique partners")
    print(f"\n   Saved to → {parquet_path}")
    print(f"             → {csv_path}")
    print("\n→ Run  python scripts/generate_dashboard.py  to rebuild the HTML dashboard.")


if __name__ == "__main__":
    main()
