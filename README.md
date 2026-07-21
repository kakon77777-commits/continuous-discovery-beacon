# Continuous Discovery Beacon — MVP v0.1

事件驅動式網站內容發現與索引訊號中樞。這一版先完成單站／少量站點可用的核心閉環：

```text
內容變更事件
  → URL 正規化與主機白名單
  → 內容事件去重
  → SQLite 持久化
  → IndexNow / Sitemap / RSS / JSONL Changes
  → 交付狀態與重試資料
  → Web 儀表板與 OpenAPI
```

## 已完成

- FastAPI API 與 Swagger／OpenAPI。
- SQLite + SQLAlchemy 資料模型。
- 站點建立與站點主機限制。
- URL 強制 HTTPS、追蹤參數移除、尾斜線統一。
- `site + canonical URL + event type + content hash` 去重。
- `created / updated / deleted / redirected / restored / metadata_changed / structured_data_changed`。
- IndexNow 單 URL POST；未配置金鑰時明確標記 `skipped`。
- 資料庫即時生成 `/sitemap.xml`、`/feed.xml`、`/changes.jsonl`。
- `/.well-known/discovery.json` 機器發現端點。
- Bearer Token 寫入保護：管理端（建站、手動 dispatch）用單一 `CDB_API_TOKEN`；事件投稿（`POST /api/v1/events`）改用**每站獨立 Token**，建站時產生、只回傳一次，外洩範圍只限單一站點。
- 指數退避所需的 `next_retry_at` 與一次性 retry worker。
- Docker、Compose、GitHub Actions 範例與 pytest 測試。

## MVP 刻意未做

- 完整 Git diff 到公共 URL 的通用映射器；不同網站路由規則差異太大，範例 Action 留有映射點。
- WebSub Hub、第三方 Webhook 訂閱、Crawler IP／反向 DNS 驗證。
- PostgreSQL、多租戶權限、完整管理 UI、分散式佇列。
- 主動抓取頁面並自行計算內容指紋；v0.1 由部署流程或 CMS 提供 `content_hash`。

## 本機啟動

需要 Python 3.12+。

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

開啟：

- Dashboard: `http://localhost:8000/`
- OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/healthz`

## Docker 啟動

```bash
cp .env.example .env
# 修改 .env 的 CDB_API_TOKEN
docker compose up --build
```

## 建立站點

站點建立用**管理員 Token**（`CDB_API_TOKEN`）。回應會附一組 `submit_token`——**只會顯示這一次**，是這個站點之後投稿事件要用的憑證，請立刻存到該站點的 CI/CD Secret（例如 `BEACON_SUBMIT_TOKEN_LOGIC`），不要存進任何 Git 儲存庫。

```bash
curl -X POST http://localhost:8000/api/v1/sites \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "logic_evemisslab",
    "name": "EVEMISSLAB Logic",
    "base_url": "https://logic.evemisslab.com"
  }'
```

要啟用 IndexNow，再加入：

```json
{
  "indexnow_key": "YOUR_KEY",
  "indexnow_key_location": "https://logic.evemisslab.com/YOUR_KEY.txt"
}
```

金鑰檔案必須實際部署在該公開位置。

## 建立與自動交付事件

投稿事件用**該站點自己的 `submit_token`**（不是管理員 Token）。用錯站點的 Token、或用管理員 Token 投稿，都會被拒絕（403）——這樣單一站點的 Token 外洩，不會波及其他站點。

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer SITE_SUBMIT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "logic_evemisslab",
    "url": "https://logic.evemisslab.com/timeline/",
    "event_type": "updated",
    "content_hash": "sha256:replace-with-real-hash",
    "title": "Timeline",
    "summary": "Timeline updated.",
    "priority": 0.8,
    "auto_dispatch": true
  }'
```

## 手動交付

建立事件時設 `auto_dispatch: false`，再執行：

```bash
curl -X POST http://localhost:8000/api/v1/events/EVENT_ID/dispatch \
  -H "Authorization: Bearer change-me"
```

## 重試 Worker

```bash
python scripts/retry_worker.py --limit 100
```

正式部署可由 cron 每分鐘執行一次；它只處理 `next_retry_at` 已到期的交付。

## Demo 資料

```bash
python scripts/bootstrap_demo.py
```

## 測試

```bash
pytest
```

測試涵蓋：認證、站點建立、URL 正規化、跨主機拒絕、事件去重、交付、Sitemap、RSS、Changes、discovery endpoint,以及每站 Token 隔離（缺 Token 拒絕、A 站 Token 不能投稿 B 站、管理員 Token 不能單獨拿來投稿事件）。

## 部署前最低安全清單

1. 設定高強度 `CDB_API_TOKEN`。
2. 只讓 Dashboard/API 經 HTTPS 存取。
3. 不要把 IndexNow Key 放進公開 Git 儲存庫。
4. 確認提交 URL 的 host 與站點 base URL 相同。
5. 為 `/api/v1/*` 加上反向代理速率限制。
6. 正式規模改用 PostgreSQL，並把背景交付移到可靠佇列。

## 下一個合理版本 v0.2

優先順序應是：

1. 針對 EVEMISSLAB 網站實作真正的 `changed file → absolute URL` 映射器。
2. GitHub Webhook／Cloudflare Deploy Hook 驗證。
3. PostgreSQL + durable worker。
4. Webhook 訂閱與 HMAC。
5. Crawler access-log ingestion 與廣播到回訪延遲。
