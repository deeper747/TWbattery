#!/usr/bin/env python3
"""
fetch_data.py — 從財政部關務署統計資料查詢平台下載台灣進出口資料
Taiwan Customs Import/Export Data Fetcher
Source: https://portal.sw.nat.gov.tw/APGA/GA30

使用方式 / Usage:
    python scripts/fetch_data.py --start 202301 --end 202412
    python scripts/fetch_data.py --start 202301 --end 202412 --direction both

自動下載需要 Playwright（pip install playwright && playwright install chromium）
如遇 CAPTCHA 阻擋，請改用手動下載（見 data/MANUAL_DOWNLOAD.md）
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ── paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))
from config import ALL_HS6

# ── portal constants ────────────────────────────────────────────────────────────
PORTAL_URL = "https://portal.sw.nat.gov.tw/APGA/GA30"
HS_CODES_STR = ",".join(ALL_HS6)   # all codes in one query


# ══════════════════════════════════════════════════════════════════════════════
# Playwright-based automated download
# ══════════════════════════════════════════════════════════════════════════════

async def fetch_with_playwright(
    start_ym: str,
    end_ym: str,
    direction: str,  # "I" = import, "E" = export
    headless: bool = False,   # set False so you can solve CAPTCHA manually if needed
) -> Optional[Path]:
    """
    Opens a Chromium browser, fills the customs portal form, and downloads a CSV.

    Args:
        start_ym: "YYYYMM"  e.g. "202301"
        end_ym:   "YYYYMM"  e.g. "202412"
        direction: "I" (進口) or "E" (出口)
        headless: False = show browser window (recommended first time)

    Returns:
        Path to downloaded CSV, or None on failure.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] playwright not installed. Run: pip install playwright && playwright install chromium")
        return None

    dir_label = "進口" if direction == "I" else "出口"
    out_filename = RAW_DIR / f"customs_{direction}_{start_ym}_{end_ym}.csv"

    if out_filename.exists():
        print(f"[SKIP] {out_filename.name} already exists.")
        return out_filename

    print(f"\n[INFO] 開啟瀏覽器，下載 {dir_label} 資料 {start_ym}–{end_ym} ...")
    print(f"[INFO] HS codes: {HS_CODES_STR}")
    if not headless:
        print("[INFO] 瀏覽器視窗將會開啟；若出現驗證碼請手動填入，再等待程式繼續執行。")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        await page.goto(PORTAL_URL, wait_until="networkidle", timeout=30_000)
        await page.wait_for_timeout(1500)

        # ── 1. Select 進口 / 出口 ──────────────────────────────────────────────
        # The radio buttons are typically named "ietype" or similar.
        # Try common selectors; adjust if the portal layout changes.
        try:
            if direction == "I":
                await page.click("input[value='1']")   # 進口
            else:
                await page.click("input[value='2']")   # 出口
            await page.wait_for_timeout(500)
        except Exception as e:
            print(f"[WARN] Could not select direction radio button: {e}")

        # ── 2. Select monthly (按月) ─────────────────────────────────────────
        try:
            await page.click("text=按月")
            await page.wait_for_timeout(500)
        except Exception as e:
            print(f"[WARN] Could not select monthly: {e}")

        # ── 3. Set date range ────────────────────────────────────────────────
        # Try to fill start/end year-month fields.
        # Common field names: startym, endym, ym_s, ym_e
        for selector in ["#startym", "input[name='startym']", "input[placeholder*='開始']"]:
            try:
                await page.fill(selector, start_ym)
                break
            except Exception:
                pass

        for selector in ["#endym", "input[name='endym']", "input[placeholder*='結束']"]:
            try:
                await page.fill(selector, end_ym)
                break
            except Exception:
                pass

        # ── 4. Select 指定貨品號列 ──────────────────────────────────────────
        try:
            await page.click("text=指定貨品號列")
            await page.wait_for_timeout(500)
        except Exception as e:
            print(f"[WARN] Could not click 指定貨品號列: {e}")

        # Fill HS codes
        for selector in [
            "textarea[name='taxcode']",
            "#taxcode",
            "input[name='taxcode']",
            "textarea",
        ]:
            try:
                await page.fill(selector, HS_CODES_STR)
                break
            except Exception:
                pass

        # ── 5. Select by country (全部國家, aggregate by partner) ────────────
        # We want country-level breakdown for China-dependency analysis
        try:
            await page.click("text=全部國家")
            await page.wait_for_timeout(500)
        except Exception as e:
            print(f"[WARN] Could not select country option: {e}")

        # ── 6. Wait for any CAPTCHA (if headless=False user can solve it) ──
        if not headless:
            print("\n[ACTION NEEDED] 請在瀏覽器中確認表單填寫正確，解決驗證碼（如有），然後回到終端機按 Enter 繼續...")
            input()

        # ── 7. Click CSV download ────────────────────────────────────────────
        async with page.expect_download(timeout=60_000) as dl_info:
            # Try common download button labels
            for btn in ["下載CSV", "CSV", "download_csv"]:
                try:
                    await page.click(f"text={btn}")
                    break
                except Exception:
                    pass

        download = await dl_info.value
        await download.save_as(out_filename)
        print(f"[OK] Downloaded → {out_filename}")

        await browser.close()
        return out_filename


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(description="Fetch Taiwan Customs data")
    p.add_argument(
        "--start", default=None,
        help="Start year-month YYYYMM (default: 24 months ago)"
    )
    p.add_argument(
        "--end", default=None,
        help="End year-month YYYYMM (default: last month)"
    )
    p.add_argument(
        "--direction", choices=["I", "E", "both"], default="both",
        help="I=import, E=export, both=download both (default: both)"
    )
    p.add_argument(
        "--headless", action="store_true",
        help="Run browser in headless mode (no window, no CAPTCHA solving possible)"
    )
    return p.parse_args()


def last_month_ym() -> str:
    today = datetime.today()
    first = today.replace(day=1)
    last = first - timedelta(days=1)
    return last.strftime("%Y%m")


def months_ago_ym(n: int) -> str:
    today = datetime.today()
    y = today.year
    m = today.month - n
    while m <= 0:
        m += 12
        y -= 1
    return f"{y}{m:02d}"


async def main():
    args = parse_args()
    start = args.start or months_ago_ym(24)
    end = args.end or last_month_ym()

    directions = []
    if args.direction in ("I", "both"):
        directions.append("I")
    if args.direction in ("E", "both"):
        directions.append("E")

    print(f"=== Taiwan Customs Data Fetch ===")
    print(f"Period : {start} – {end}")
    print(f"Direction(s): {directions}")
    print(f"HS codes: {len(ALL_HS6)} codes")

    results = []
    for d in directions:
        path = await fetch_with_playwright(start, end, d, headless=args.headless)
        if path:
            results.append(path)

    if results:
        print(f"\n✅ Downloaded {len(results)} file(s):")
        for r in results:
            print(f"   {r}")
        print("\n→ Run  python scripts/process_data.py  to process into dashboard format.")
    else:
        print("\n❌ Download failed. Please use manual download:")
        print(f"   See  data/MANUAL_DOWNLOAD.md  for instructions.")


if __name__ == "__main__":
    asyncio.run(main())
