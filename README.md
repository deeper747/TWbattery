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

## 烏克蘭 HS 8507 進口分析

### 研究問題

台灣是否曾向烏克蘭出口電動載具電池（HS 8507）？在俄烏戰爭前後規模如何變化？台灣在烏克蘭進口來源國中排第幾？

### 資料來源

烏克蘭海關統計局（Державна митна служба України）發布的年度進出口明細，檔案為 Excel 格式，依來源國 × HS 六位碼分列進口金額（千美元）與淨重（公噸）。

資料儲存路徑：`data/raw/country_goods/`，檔名格式：`12 month_YYYY_country_goods.xlsx`

> **注意**：烏克蘭海關將台灣登記為「Тайвань, провінція Китаю」（Taiwan, Province of China）。

### 分析腳本

| 腳本 | 功能 |
|------|------|
| `scripts/fetch_ukraine_taiwan_8507.py` | 篩選烏克蘭從台灣進口 HS 8507 的歷年資料，輸出明細與年度摘要 CSV |
| `scripts/fetch_ukraine_hs8507_all_countries.py` | 擴大範圍至所有來源國，計算台灣排名，產出堆疊長條圖與折線圖 |

### 執行方式

```bash
# Step 1：僅看台灣 → 烏克蘭的數字
python scripts/fetch_ukraine_taiwan_8507.py
# → data/ukraine_taiwan_8507.csv
# → data/ukraine_taiwan_8507_summary.csv

# Step 2：全來源國比較 + 台灣排名 + 圖表
python scripts/fetch_ukraine_hs8507_all_countries.py
# → data/processed/ukraine_hs8507_all_countries.csv
# → data/processed/ukraine_hs8507_by_country_year.csv
# → data/processed/ukraine_hs8507_ranking_value.csv
# → data/processed/ukraine_hs8507_ranking_weight.csv
# → data/processed/ukraine_hs8507_stacked_value.png
# → data/processed/ukraine_hs8507_stacked_weight.png
# → data/processed/ukraine_hs8507_line_value.png
# → data/processed/ukraine_hs8507_line_weight.png
```

### 主要產出

- **排名表**：每年前三大供應國 + 台灣排名與金額，分進口值與淨重兩版
- **堆疊長條圖**：各年度前 10 大來源國佔比（部分年份標 `*` 表示非完整年）
- **折線圖**：前 10 大來源國歷年趨勢（對數刻度）

---

## 資料來源

- **台灣進出口資料**：財政部關務署 統計資料查詢平台 (portal.sw.nat.gov.tw/APGA/GA30)
  - 每月 2 日後公布上月資料；月底前數字可能有微幅修正
- **烏克蘭進口資料**：烏克蘭海關統計局年度 Excel 報告
- **HS Code 分類**：參考 U.S. Energy Trade Dashboard 及 Council on Strategic Risks 研究方法
