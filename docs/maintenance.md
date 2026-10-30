# 維護手冊（給非程式人員）

所有操作都在 GitHub 網頁完成：https://github.com/ottoted34/taiwan-agri-land-law

## 1. 如何確認資料有持續更新

- 打開網站首頁，看「最後成功同步」時間；正常情況應在 1 天內。
- 更新紀錄**不公開在網站**（2026-10-30 擁有者決定），只在 GitHub 查看：Actions 頁面列出每次執行結果；Repository 的 `data/updates/runs/` 有每次作業完整紀錄（各來源新增、異動、失敗數與錯誤訊息），`data/metadata/source-status.json` 有各來源最近成功時間。
- 若超過 50 小時沒有成功同步，watchdog 會在 GitHub 開一個標題為「資料同步逾時警示」的 Issue，GitHub 會寄 Email 通知 Repository 擁有者。

## 2. 如何查看更新失敗原因

1. GitHub → `data/updates/runs/` → 開啟該次日期的檔案，`errors` 為錯誤訊息。
2. 或 GitHub → Actions → 點選失敗（紅色 ✗）的執行 → 點 `sync` → 展開紅色步驟。
3. 常見原因：官方網站維護中、改版（解析不到資料）、連線逾時。前兩者會自動保留舊資料，等官方恢復即可；若連續多日失敗，可能是官方改版，需要修改 `scripts/agrilaw/collectors/` 對應程式。

## 3. 如何手動重跑

GitHub → Actions → 左側選 **update-laws** → 右側 **Run workflow** → mode 選 `daily`（快速）、`weekly`（完整列表比對）或 `full`（全部重抓，約 1 小時）→ Run。
技術資料選 **update-technical**；來源盤點選 **source-audit**；只想重新部署網站選 **deploy**；評估新來源（robots、頁面格式）選 **diagnose** 並在 `probe` 欄填網址。

## 4. 如何新增一個農業改良場來源

若該場在農業資料開放平臺有出版品資料集：
1. 在 https://data.moa.gov.tw 找到資料集，記下網址中的代碼（如 `open_detail.aspx?id=740` 的 `740`）。
2. 編輯 `config/sources/technical_datasets.yaml`，在 `datasets:` 下新增一行：
   `- {unit_id: "代碼", title: 資料集名稱, agency_id: 機關代碼, series: 刊物名稱}`（機關代碼見 `config/agencies/agencies.yaml`）。
3. 存檔（Commit changes）。下次 update-technical 執行即會收錄。

系統每月也會自動搜尋平臺目錄，結果記在 `data/metadata/datamoa-catalog.json`；若誤收不相關資料集，把代碼加入同檔案的 `exclude:`。

其他型式（網站 HTML、RSS）需新增一個 collector 程式（參考 `collectors/datamoa.py`）並在 `sync.py` 的 `PLANS` 與 `run_source` 登錄，同時更新 `config/sources/registry.yaml`。

## 5. 地方規定（縣市）

地方規定依縣市分開收錄，設定檔為 `config/local/counties.yaml`。網站「法規」頁與「案件審查輔助」之縣市選單依此檔產生：`checked: false` 的縣市一律顯示「尚未查核」。

### 5-1. 地方規定審核流程（收錄前必經）

其他縣市同仁可在網站「資料來源」頁按「提供地方規定」，以 Google 表單提供（https://forms.gle/UiC2xsxrAwgb5pns5；設定建議見 `docs/google-form.md`，網址設於 `web/src/pages/Sources.tsx` 的 `GOOGLE_FORM_URL`）。回應只有表單擁有者看得到。**任何地方規定都必須經管理者審核才收錄**：

1. **確認無個資**：若回應含姓名、電話、身分證字號、地號或個案資料，處理完即刪除該筆回應（表單「回覆」頁與試算表都要刪）。
2. **核對官方網址**：網址須為政府機關網域（`gov.tw`），且頁面可看到法規全文或發布令。非官方來源（新聞、部落格、私人整理）一律不收。
3. **核對內容**：名稱、發布／修正日期、發文字號、施行日期與官方頁面一致；確認是否仍有效（未廢止、未停止適用）、是否有更新版本。
4. **判斷相關性**：限與農地農用、農業設施容許使用、農地變更使用、農舍、填土等本站主題直接相關者。
5. **決定收錄方式**：
   - 該縣市法規系統屬「主管法規共用系統」（網址含 `LawContent.aspx?id=GL…`），且 robots.txt 未限制：在 `counties.yaml` 該縣市下設 `law_system`、`source_id: local-縣市英文`、`auto_sync: true`、`checked: true`，並在 `laws:` 新增一筆（見下方範例）。不確定 robots 或頁面格式時，先執行 Actions → **diagnose**，在 `probe` 欄填入法規網址，結果在 `diagnostics` 分支的 `probe-report.json`。
   - 無法自動擷取者（robots 不允許、格式不同、只有 PDF）：設 `checked: true`、`auto_sync: false`，人工建立 `data/laws/<縣市代碼>-<編號>.json`（格式同 `data/laws/TXG-GL000357.json`，須含 `county`、`official_url`、`sources`），並在 `review` 欄註明人工輸入日期與核對人。
6. **留下審核紀錄**：在該筆設定填 `reviewed_by`（單位或職稱即可）、`reviewed_at`、`basis`（核對之官方頁面）、`issue`（選填：審核紀錄連結，或「Google 表單第 N 筆回應」）。網站法規頁會顯示審核紀錄。
7. **回寫試算表**：在回應試算表填審核狀態（收錄／不收錄）與理由；不收錄者可將法規代碼加入該縣市 `rejected:`，候選清單即不再列出。表單未收集聯絡方式，如需回覆提供者，請以機關內部管道聯繫。

```yaml
      - law_system_id: GL000357          # 官方網址 id= 後面的代碼
        name: 臺中市申請農業用地作農業設施容許使用審查要點
        topics: [material_room, greenhouse]   # config/topics/topics.yaml 之 legal_topics
        scenarios: [material, greenhouse, local] # 案件審查輔助情境 id（web/src/lib/scenarios.ts）
        reviewed_by: ○○縣政府農業處
        reviewed_at: 2026-11-01
        basis: 臺中市法規查詢系統法規內容頁（府授農地字第1130041756號令修正）
        issue: Google 表單第 12 筆回應
```

存檔後下次 update-laws（每日）即會擷取；要立即生效可手動執行 update-laws（mode `daily`）。

### 5-2. 系統自動列出之候選

自動同步之縣市，每次同步會讀取 `candidate_categories` 分類頁，把名稱含 `candidate_keywords` 且尚未收錄、未拒絕之法規寫入 `data/metadata/local-candidates.json`，網站「資料來源」頁亦會列出。**候選不會自動上線**，須依 5-1 審核後加入 `laws:`。

### 5-3. 移除或更正

- 不再收錄：自 `laws:` 移除該筆、加入 `rejected:`，並刪除 `data/laws/<代碼>-<編號>.json` 及 `data/laws/versions/<代碼>-<編號>/`。
- 官方已廢止：系統會依官方頁面標示更新狀態；仍保留紀錄供查核舊案。
- 地方規定只適用於該縣市，網站與案件輔助均會標示縣市，不得視為全國適用。

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

- 首頁「最後成功同步」時間；GitHub `data/updates/runs/` 最新一筆。
- 網站資料檔 `data/manifest.json` 的 `built_at` 為建置時間。
- 每筆法規頁顯示「本站最後查核」；每筆函釋頁顯示「最後確認」。

## 10. 仍需人工判斷的事項

- 函釋是否仍可援用（效力）、是否適用於個案。
- 系統比對之法規關聯是否正確。
- 地方規定之審核收錄（見第 5 節）與候選清單之審核。
- 無法自動擷取之機關資料（農糧署、試驗研究機構官網）。
- 修法後過渡條款、施行日期之判斷。
- 案件審查輔助產出之草稿內容。

## 排程被 GitHub 停用怎麼辦

公開 Repository 60 天無活動時，GitHub 可能停用排程。本專案每次同步都會提交更新紀錄，正常運作下不會停用；watchdog 亦會嘗試重新啟用。若仍被停用：Actions → 選該工作流程 → 按上方 **Enable workflow**。GitHub 不保證排程永久執行，請定期查看首頁同步時間。

## 自架 runner（選用）

試驗研究機構官網自海外主機無法連線。若日後要直接擷取，可在國內電腦安裝 GitHub self-hosted runner，並在工作流程 `runs-on` 改用該 runner。此項需要使用者提供主機，未預設啟用。
