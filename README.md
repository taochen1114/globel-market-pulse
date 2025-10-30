# Global Market Pulse

Global Market Pulse 是一個全自動、每日更新的全球市場觀察網站。專案結合 Python 資料管線、OpenAI AI 摘要與 Astro 靜態網站生成，透過 GitHub Actions 部署至 GitHub Pages，實現「免維護、每日自動更新」。

## 專案結構

```
market-pulse/
├── scripts/
│   ├── fetch_data.py
│   ├── ai_summary.py
│   └── utils.py
├── data/
│   ├── market_data.json
│   └── summary.json
├── web/
│   ├── src/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── styles/
│   │   └── data/
│   └── public/data/
├── .github/workflows/update.yml
├── package.json
├── requirements.txt
└── README.md
```

## 快速開始

### 前置需求

- Python 3.10+
- Node.js 20+
- OpenAI API Key（若需啟用每日 AI 摘要）

### 安裝與開發

```bash
# 安裝 Python 依賴
pip install -r requirements.txt

# 取得最新市場資料與 AI 摘要
python scripts/fetch_data.py
OPENAI_API_KEY=your_key python scripts/ai_summary.py

# 安裝前端依賴並啟動開發伺服器
npm install
npm --workspace web install
npm --workspace web run dev
```

開發伺服器預設會在 `http://localhost:4321` 提供 Astro 網站。

### 建置靜態網站

```bash
npm run build
```

輸出會產生在 `web/dist` 目錄，可部署到任何靜態主機。

## GitHub Actions 自動化

`.github/workflows/update.yml` 定義每日自動排程：

1. 安裝 Python 與 Node.js 依賴
2. 執行 `fetch_data.py` 取得市場資料
3. 執行 `ai_summary.py` 產生 AI 摘要（需設定 `OPENAI_API_KEY` 機密）
4. 建置 Astro 靜態網站
5. 透過 `peaceiris/actions-gh-pages` 部署到 GitHub Pages

## 環境變數

| 變數 | 說明 |
| ---- | ---- |
| `OPENAI_API_KEY` | 用於呼叫 OpenAI API 生成每日 AI 摘要。 |

## 資料檔案

- `data/market_data.json`：最新市場資料，供網站與 AI 摘要使用。
- `data/summary.json`：AI 產出的每日觀察摘要。

管線執行時會自動同步上述檔案至 `web/public/data/` 與 `web/src/data/` 供前端使用。

## 授權

專案採用 MIT License，歡迎自由使用與擴充。
