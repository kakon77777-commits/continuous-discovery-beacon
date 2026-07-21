# EveMissLab 網站群清單(草稿)

狀態:**未完成,持續收集中**——Neo 陸續補充,尚未轉成正式 Site Registry 設定檔。

來源:`D:\Ai\網站群\beacon\網站列表.txt`(2026-07-21)

---

## 單獨網域

- agiright.org
- asiright.org — 301 → agiright.org
- commoninstant.org
- efficientnewlanguage.org
- emlphosphor.com
- eveglypheditor.com
- evemiss.com
- evemisslab.com
- evemisstechnology.com
- httpefficientnewlanguage.org — 301 → efficientnewlanguage.org
- 一言諾科技有限公司.tw

## 子網域

- https://logic.evemisslab.com/
- https://aiboard.evemisslab.com/
- https://felra.evemisslab.com/
- https://storyforge.evemisslab.com/
- https://wse.evemisstechnology.com/
- https://beacon.evemiss.com/（Beacon 自己）

---

## 下一步

等清單補齊後,依白皮書(`docs/持續可發現性廣播器_概念與技術設計_v0.1.md` §39、CDCP 補充文件 §7.1)定義的 Site Registry 格式,把每個站點整理成：

```yaml
sites:
  - id: <site_id>
    origin: <網站網址>
    repository: <對應的 GitHub repo,若有>
    sitemap: <sitemap 位置>
    adapter: <URL 對應規則類型>
```

再依序建立每個站點在 Beacon 裡的紀錄(`POST /api/v1/sites`),取得各自獨立的 `submit_token`。301 轉址的網域（`asiright.org`、`httpefficientnewlanguage.org`）不需要單獨建站，只是需要留意它們指向的目標站點。
