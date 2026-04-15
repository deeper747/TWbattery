# 台灣電池供應鏈進出口 Dashboard
## Taiwan Battery Supply Chain Trade Dashboard

追蹤台灣進出口電池成品、原物料的月度資料，供 DSET 同事使用。
靜態 HTML dashboard，部署於 GitHub Pages，無需伺服器。

---

## 快速開始（三步驟）

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 下載資料（見下方說明），處理成標準格式
python scripts/process_data.py

# 3. 生成靜態 HTML
python scripts/generate_dashboard.py
# → 開啟 docs/index.html，或 push 至 GitHub Pages
```

---

## 架構

```
TWbattery/
├── config.py                       # HS Code 定義與分類
├── requirements.txt
├── scripts/
│   ├── fetch_data.py               # 自動從關務署下載 CSV（Playwright）
│   ├── process_data.py             # 處理原始 CSV → 標準化格式
│   ├── generate_dashboard.py       # 生成靜態 HTML dashboard
│   └── setup_reminder.sh           # 設定 macOS 每月提醒
├── .github/workflows/
│   └── monthly_update.yml          # GitHub Actions：每月 10 日自動重建
├── data/
│   ├── MANUAL_DOWNLOAD.md          # 手動下載步驟說明
│   ├── raw/                        # 從關務署下載的原始 CSV
│   └── processed/                  # 處理後資料（parquet + csv）
└── docs/
    └── index.html                  # 靜態 dashboard（GitHub Pages 服務此檔）
```

---

## 追蹤的 HS Code

| 類別 | HS Code | 品名 |
|------|---------|------|
| 電池成品 | 850760 | 鋰離子蓄電池 |
| 電池成品 | 850790 | 蓄電池零件 |
| 正極材料 | 283329 | 其他硫酸鹽（鈷／鎳／錳） |
| 正極材料 | 282200 | 氧化鈷及氫氧化鈷 |
| 正極材料 | 282520 | 氧化鋰及氫氧化鋰 |
| 正極材料 | 282540 | 氧化鎳及氫氧化鎳 |
| 正極材料 | 283691 | 碳酸鋰 |
| 負極材料 | 250410 | 天然石墨（粉末） |
| 負極材料 | 380110 | 人造石墨 |
| 負極材料 | 280300 | 炭黑 |
| 電解液 | 382499 | 其他未列名化學品 |
| 金屬原料 | 750210 | 未合金鎳 |
| 金屬原料 | 281820 | 氧化鋁 |
| 金屬原料 | 810520 | 鈷粉 |
| 封裝材料 | 390120 | 高密度聚乙烯 (HDPE) |
| 封裝材料 | 390210 | 聚丙烯 (PP) |

---

## 資料下載

### 方法 A：自動（推薦，需要 Playwright）

```bash
playwright install chromium   # 只需執行一次
python scripts/fetch_data.py --start 202001 --end 202503
```

若出現驗證碼，瀏覽器視窗保持開啟，手動填完後按 Enter 繼續。

### 方法 B：手動

參閱 [`data/MANUAL_DOWNLOAD.md`](data/MANUAL_DOWNLOAD.md) — 步驟詳細說明。

---

## 每月更新流程

### 自動（GitHub Actions）

`.github/workflows/monthly_update.yml` 設定每月 10 日自動執行：
1. 重新處理 `data/raw/` 下的 CSV
2. 重新生成 `docs/index.html`
3. Commit & push 回 repo

**前提**：需先手動將最新月份的 CSV 放入 `data/raw/` 並 push，Action 才會抓到新資料。

### 手動更新

```bash
python scripts/fetch_data.py          # 下載新月份資料
python scripts/process_data.py        # 重新處理
python scripts/generate_dashboard.py  # 重新生成 HTML
git add data/ docs/ && git commit -m "data: update to YYYY-MM" && git push
```

### macOS 月曆提醒（每月 10 日）

```bash
bash scripts/setup_reminder.sh
```

---

## 設定 GitHub Pages

1. Push repo 至 GitHub
2. Settings → Pages → Source: **Deploy from a branch**
3. Branch: `main` / Folder: `/docs`
4. Save → dashboard URL: `https://deeper747.github.io/TWbattery/`

---

## 資料來源

- **進出口資料**：財政部關務署 統計資料查詢平台 (portal.sw.nat.gov.tw/APGA/GA30)
  - 每月 2 日後公布上月資料；月底前數字可能有微幅修正
- **HS Code 分類**：參考 U.S. Energy Trade Dashboard 及 Council on Strategic Risks 研究方法
