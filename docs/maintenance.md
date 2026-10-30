# 維護手冊（給非程式人員）

所有操作都在 GitHub 網頁完成：https://github.com/ottoted34/taiwan-agri-land-law

## 1. 如何確認資料有持續更新

- 打開網站首頁，看「最後成功同步」時間；正常情況應在 1 天內。
- 網站「更新紀錄」頁列出每次作業結果；「資料來源」頁列出各來源最近成功時間。
- 若超過 50 小時沒有成功同步，watchdog 會在 GitHub 開一個標題為「資料同步逾時警示」的 Issue，GitHub 會寄 Email 通知 Repository 擁有者。

## 2. 如何查看更新失敗原因

1. 網站「更新紀錄」→ 展開該次紀錄，紅字為錯誤訊息。
2. 或 GitHub → Actions → 點選失敗（紅色 ✗）的執行 → 點 `sync` → 展開紅色步驟。
3. 常見原因：官方網站維護中、改版（解析不到資料）、連線逾時。前兩者會自動保留舊資料，等官方恢復即可；若連續多日失敗，可能是官方改版，需要修改 `scripts/agrilaw/collectors/` 對應程式。

## 3. 如何手動重跑

GitHub → Actions → 左側選 **update-laws** → 右側 **Run workflow** → mode 選 `daily`（快速）、`weekly`（完整列表比對）或 `full`（全部重抓，約 1 小時）→ Run。
技術資料選 **update-technical**；來源盤點選 **source-audit**；只想重新部署網站選 **deploy**。

## 4. 如何新增一個農業改良場來源

若該場在農業資料開放平臺有出版品資料集：
1. 在 https://data.moa.gov.tw 找到資料集，記下網址中的代碼（如 `open_detail.aspx?id=740` 的 `740`）。
2. 編輯 `config/sources/technical_datasets.yaml`，在 `datasets:` 下新增一行：
   `- {unit_id: "代碼", title: 資料集名稱, agency_id: 機關代碼, series: 刊物名稱}`（機關代碼見 `config/agencies/agencies.yaml`）。
3. 存檔（Commit changes）。下次 update-technical 執行即會收錄。

系統每月也會自動搜尋平臺目錄，結果記在 `data/metadata/datamoa-catalog.json`；若誤收不相關資料集，把代碼加入同檔案的 `exclude:`。

其他型式（網站 HTML、RSS）需新增一個 collector 程式（參考 `collectors/datamoa.py`）並在 `sync.py` 的 `PLANS` 與 `run_source` 登錄，同時更新 `config/sources/registry.yaml`。

## 5. 如何新增地方政府法規

1. 在 `config/sources/registry.yaml` 新增來源（`id: local-縣市代碼`），填寫網址與 `audit_status`。
2. 若該縣市有開放資料或可合法擷取之法規系統，新增 collector；否則先人工建立 `data/laws/LOCAL-縣市-名稱.json`（格式同其他法規，`level: 地方自治法規`），並於 `sources` 填官方網址。
3. 地方規定只適用該縣市，網站與案件輔助會標示縣市，不得視為全國適用。

## 6. 如何修正錯誤函釋資料

函釋內容來自官方系統，每次同步會以官方內容覆蓋。若官方內容本身有誤，請勿直接改資料檔，改用：
- 錯誤關聯：在 `config/relations/manual.yaml` 的 `relations:` 新增人工確認關聯並附依據。
- 解析錯誤（本站程式問題）：開 Issue 說明官方網址與錯誤之處。

## 7. 如何處理停止適用函釋

在 `config/relations/manual.yaml` 的 `validity:` 新增：
```yaml
  - {docno: 農企字第1000143240號, date: 2011-07-19, status: ceased, basis: 農業部XXX年X月X日農XX字第XXXX號函停止適用, evidence: https://官方網址, confirmed_by: 承辦人, confirmed_at: 2026-11-01}
```
`status` 可為 `ceased`（停止適用）、`revoked`（廢止／撤回）、`amended_by_later`、`possibly_affected`、`needs_review`、`no_known_cessation`。必須附官方依據網址。存檔後下次同步或手動執行 deploy 即生效。

## 8. 如何回復上一個正確版本

所有資料都在 git 版本控制中：
1. GitHub → 檔案頁面 → History → 找到正確版本的 commit。
2. 對該資料更新 commit 使用 **Revert**（或請熟悉 git 的人執行 `git revert <commit>`），推送後執行 deploy。
3. 被隔離的批次資料在 `data/quarantine/`，確認無誤才需處理，平時可忽略。

## 9. 如何確認公開網站沒有使用過時資料

- 首頁「最後成功同步」與「更新紀錄」最新一筆時間。
- 網站資料檔 `data/manifest.json` 的 `built_at` 為建置時間。
- 每筆法規頁顯示「本站最後查核」；每筆函釋頁顯示「最後確認」。

## 10. 仍需人工判斷的事項

- 函釋是否仍可援用（效力）、是否適用於個案。
- 系統比對之法規關聯是否正確。
- 地方自治法規之查核與收錄。
- 無法自動擷取之機關資料（農糧署、試驗研究機構官網）。
- 修法後過渡條款、施行日期之判斷。
- 案件審查輔助產出之草稿內容。

## 排程被 GitHub 停用怎麼辦

公開 Repository 60 天無活動時，GitHub 可能停用排程。本專案每次同步都會提交更新紀錄，正常運作下不會停用；watchdog 亦會嘗試重新啟用。若仍被停用：Actions → 選該工作流程 → 按上方 **Enable workflow**。GitHub 不保證排程永久執行，請定期查看首頁同步時間。

## 自架 runner（選用）

試驗研究機構官網自海外主機無法連線。若日後要直接擷取，可在國內電腦安裝 GitHub self-hosted runner，並在工作流程 `runs-on` 改用該 runner。此項需要使用者提供主機，未預設啟用。
