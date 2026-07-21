# EveMissLab CDB 部署方案決策 — 本地端 Agent 審查回覆

回覆對象：`EveMissLab_CDB_部署方案決策與操作審查_v0.1.md`（2026-07-21）
本文件依該文件第 22 節「審查回覆格式」填寫。

---

## 審查者

名稱／模型：Claude Sonnet 5（Claude Code，本機 Agent，D:\Ai）
審查日期：2026-07-21
是否實際開啟官方介面：是（Hetzner cost-optimized 定價頁、Coolify 官方安裝文件；未登入任何帳號，僅公開頁面）

## 建議方案

- [x] 方案 A：Coolify
- [ ] 方案 B：Docker Compose（保留為明確退路，觸發條件見下）
- [ ] 其他方案

理由：現有 repo（Dockerfile + docker-compose.yml）對兩個方案都零改動即可用，差別純粹在維運體驗。Neo 已明確表示偏好 GitHub push 即自動部署的體驗（見前次對話），且站群會持續增加，Coolify 的集中管理面板長期效益更高。採用文件本身的退路設計：Coolify 若在 CX23 上實測資源吃緊，直接退到方案 B，不需更換 Hetzner 或網域。

## 發現的錯誤

1. `notify-beacon.yml`（repo 現有範例）在 `git push` 後立即通知 Beacon，尚未等待實際部署成功——這與本文件 §7.3「部署成功閘門」的原則矛盾，目前只是「示範」而非可上線流程，需在該事件源頭（各網站自己的部署 workflow）補上部署完成後才呼叫 Beacon 的機制，不是 Beacon 服務本身要改。
2. `Dockerfile` 原本沒有 `HEALTHCHECK`，Coolify／Compose 的滾動部署與代理切換依賴容器健康狀態，缺少會讓「部署成功」判斷退化成「process 有啟動」。**已修正並推送**（commit `626d9fe`）。
3. README／`.env.example` 的 `CDB_API_TOKEN=change-me` 是公開 repo 明文可見的字面字串；程式邏輯本身正確（非空字串就強制 Bearer Token），但若正式部署忘記在 Coolify 環境變數覆寫，等於任何人都能照著 README 的 curl 範例對正式站寫入假事件。**這不是程式碼缺陷，是上線前必查清單項目**（見下）。

## 價格核對（Hetzner cost-optimized 頁面，今日即時核對）

- CX23 規格：**2 vCPU（Intel/AMD）／4 GB RAM／40 GB SSD** —— 與文件描述**一致**，已於官方頁面確認存在。
- 精確月費數字：頁面價格為 JS 動態渲染（依地區/幣別選擇後才顯示），純文字擷取拿不到數字，**無法在此次核對中重新確認 €5.49/月是否仍準確**。鑑於 Hetzner 在 2026 年已有至少兩次調價（4/1、6/15），**強烈建議在 Phase 1 實際建立前，直接在 Hetzner 主控台看一次即時顯示價格**，不要沿用文件裡的舊數字下單。
- VAT／IPv4／Backups：同樣需要在你自己登入的帳號介面上核對（依帳單地址、方案而異），我這邊沒有帳號無法看到。

## 操作風險

1. GHCR image 預設是 **private package**，若 Coolify 要直接 pull 需要額外設定 registry 認證，或把 package 設為 public（建議後者，反正原始碼已公開）。文件沒提到這點，Phase 2 建立 CI 時要處理。
2. Coolify 官方文件明確寫：**「安裝後第一件事必須立刻建立管理帳號，晚一步可能被別人搶先建立、拿走伺服器控制權」**——這是官方原文警告，不是我推測的風險，Phase 2 執行時要把這步驟排第一優先、不能拖延。
3. Cloudflare Tunnel 架構下（子方案 A1），Hetzner 防火牆**不需要**對外開放 80/443，只需開 22（SSH，限金鑰登入）；這比子方案 A2 直接暴露 IPv4 的攻擊面小很多，支持文件「優先嘗試 Tunnel」的判斷。

## 必須由使用者本人完成

1. Hetzner 開帳號、建立 Project、建立 CX23、綁 SSH 公鑰、設定 Firewall（涉及付款，Agent 不可代辦）。
2. Coolify 安裝後**立即**建立管理帳號（見上方風險 2，時效性高）。
3. Cloudflare Zero Trust → Tunnels 建立、DNS 記錄新增、Google Search Console Domain Property 驗證——這些需要你已登入的帳號 session；若你願意在瀏覽器裡登入，我可以在旁邊用 Browser 工具幫你核對介面文字、抓錯字漏字，但點擊「建立/確認/購買」等按鈕仍由你本人操作。

## 可以由 Agent 協助完成

1. 撰寫 GitHub Actions：pytest + build + push GHCR image（可以現在就先寫好，不需要等 Hetzner 開好）。
2. Coolify 建好後，協助設定 persistent volume、環境變數清單、Scheduled Task（retry worker）、部署 webhook。
3. SQLite 安全備份腳本（`sqlite3 .backup` 而非直接複製檔案）。
4. Cloudflare Tunnel／DNS 設定步驟的逐步核對（你操作、我旁邊核對畫面文字）。

## 最終建議

**可以進入 Phase 1**，但有兩個前置條件：

1. 你在 Hetzner 主控台親眼確認今日實際月費（不要沿用文件或本回覆裡的舊數字）。
2. 記得 Coolify 裝好後第一步就是搶建管理帳號。

方案 A（Coolify）維持首選，方案 B（純 Docker Compose）作為文件已定義好的自動退路，不需要現在重新討論。

---

## 附：第 18 節逐題回答

1. **能否直接用 GHCR image 部署？** 能，但目前 repo 沒有建置＋推送 GHCR 的 workflow，需新增；且 GHCR package 預設 private，建議設為 public 或在 Coolify 設 registry 認證。
2. **Dockerfile／Compose 的 SQLite volume 掛載是否正確？** 正確：`docker-compose.yml` 有 `./data:/app/data`，Dockerfile 建立 `/app/data`，`config.py` 預設路徑與此一致。改用 Coolify 時要把 host bind mount 換成 Coolify 自己管理的 persistent volume，掛到同一個路徑。
3. **Coolify 該用 Dockerfile、Compose 還是預建 image？** 用預建 image（文件 §8.3 的選擇）。CX23 只有 2 vCPU，若同時跑 Coolify 管理層又在本機 build image，資源尖峰會互相排擠；GitHub Actions 建置、Coolify 只 pull+deploy 更穩。
4. **CX23 上 Coolify + Beacon + cloudflared 預估 RAM？** 依 Coolify 官方最低需求（2 core/2GB/30GB）與其官方範例（8GB 機器上均值用量 3.5GB，掛了十幾個服務）反推，4GB 機器上 Coolify 自身 stack + 單一輕量 FastAPI/SQLite 服務 + cloudflared，閒置估計約 1.5–2.2GB，可用但不寬裕，需 Phase 2 實測記錄真實數字，不是精確值。
5. **是否該加 swap？多大？** 應該加。Coolify 官方文件原文建議「若在同機跑 build 又跑 Coolify，考慮開 swap」。建議 2–4GB swap file，並調低 `vm.swappiness`（如 10），讓 swap 只當緊急緩衝，不當常態依賴。
6. **Cloudflare Tunnel 該指向 Coolify proxy 還是 Beacon container？** 指向 Coolify 的 reverse proxy。Container 每次部署都可能重建，直接綁定 container port 在下次部署後會失效；Coolify proxy 提供穩定進入點與零停機切換。
7. **GitHub webhook 需不需要公開 Coolify endpoint？** 文件選的是 GitHub Actions 主動呼叫 `COOLIFY_WEBHOOK_URL`（非 Coolify 反向 poll GitHub），所以這一條 deploy-webhook path 必須可從公網（GitHub runner）連到，用 `COOLIFY_TOKEN` 保護即可，不需曝露整個 dashboard，且這條 path 不能被 Cloudflare Access 的登入政策擋住（GitHub Actions 沒辦法走 MFA）。
8. **如何讓部署成功後才建立 content event？** 這是每個網站「自己的」部署 workflow 要做的事，不是 Beacon 要做的事：在該 workflow 的 Cloudflare 部署步驟之後，加一步等待部署完成（用 Cloudflare 部署狀態 API，或直接 curl 正式網址驗證 200+內容），通過才呼叫 Beacon `/api/v1/events`。屬於文件附錄 A 第 4 項，v0.2 才做，現在不阻擋 Phase 1-3。
9. **retry worker 該不該改常駐？** 不需要。目前是 one-shot script，設計是對的——比常駐 process 更省資源、更容易觀察是否卡住。用 Coolify 的 Scheduled Task 功能每分鐘跑一次即可，不必包成 systemd/supervisor 常駐服務。
10. **SQLite 備份如何避免複製到不一致檔案？** 不要直接 `cp` .sqlite3 檔案。用 SQLite 官方線上備份指令：`sqlite3 /app/data/cdb.sqlite3 ".backup '/backup/cdb-$(date +%Y%m%d%H%M).sqlite3'"`，即使有寫入中的交易也能拿到一致快照；建議同時開啟 WAL mode（目前 `database.py` 未設定）讓讀寫並行更安全。
11. **哪些 port 該開、該關？** 用 Cloudflare Tunnel 架構的話，`cloudflared` 是 outbound-only 連線，Hetzner 防火牆完全不用對外開 80/443，只需開 22（SSH，限金鑰登入）；Coolify dashboard 跟 webhook 一樣走 Tunnel，不需要額外開 port。
12. **能否先 staging 再逐站接入？** 可以，文件 Phase 3/4 的分階段規劃沒有問題，照做即可。
13. **方案 A / B 哪個更符合現有程式碼？** 兩者程式碼相容性相同（Dockerfile + docker-compose.yml 現在就都能直接用）。差別純粹在維運：方案 B 更貼近現狀（Makefile 已有 `docker-up` 對應），方案 A 需要多學一套面板，但符合 Neo 明確表示過的「喜歡 GitHub 連動自動部署」偏好，且站群持續增加時 Coolify 的集中管理優勢會更明顯。
14. **是否有資料遺失、Token 洩漏或無法回滾的缺陷？** 主要一項：`CDB_API_TOKEN` 的公開範例值 `change-me` 已在 GitHub 明文可見，正式部署時**必須**在 Coolify 環境變數換成真正隨機字串，否則等同無認證。次要兩項（不阻擋上線，列 v0.2 待辦）：SQLite 未開 WAL（目前流量規模不會碰到 lock 問題）；`dispatch_event` 若在單一 channel 交付中途被中斷，該筆 delivery 會卡在 `processing`，下次會重新嘗試而非遺失，但可能對 IndexNow 重複提交同一 URL（IndexNow 本身冪等，無實質影響）。
