# 資料結構

所有日期為西元 ISO 格式（`YYYY-MM-DD`），網站顯示時轉為民國。時間戳記含 +08:00 時區。

## 法規 `data/laws/<id>.json`

`id`：全國法規資料庫 PCode（如 `M0020022`），僅存在於 RMIS 之行政規則為 `RMIS-<編號>`。

| 欄位 | 說明 |
|---|---|
| name, level, category | 名稱、法律／命令／行政規則、主管分類 |
| official_url, primary_source, sources[] | 官方網址與資料來源（含擷取時間、資料集更新日） |
| modified_date, effective_date, effective_note, abandon_note | 修正、施行、施行說明、廢止 |
| status | `current`／`abolished`／`partially_pending`／`needs_review` |
| articles[] | `{key, label, chapter, text}`；key 如 `8-1`，行政規則之點為 `P7-1` |
| attachments[] | 附表名稱與官方連結 |
| histories[] | 沿革 `{seq, date, text}` |
| rmis | RMIS 對應頁、法規對應函釋網址、RMIS 沿革 |
| cross_check | 兩官方來源條文比對結果 |
| content_hash, first_seen, last_checked, last_changed, change_log[] | 版本管理 |

地方規定：`id` 為「縣市代碼-該縣市法規系統代碼」（如 `TXG-GL000357`），另有 `county`（縣市）、`published_date`（公發布日）、`docno_text`（最新發文字號）、`system_path`（法規體系）、`scenarios[]`（對應案件審查輔助情境）、`review`（管理者審核紀錄 `{reviewed_by, reviewed_at, basis, issue}`）。設定見 `config/local/counties.yaml`；待審核候選見 `data/metadata/local-candidates.json`。

版本：`data/laws/versions/<id>/<version>.json`。`kind=captured` 為本站擷取之現行條文快照（每次內容雜湊改變即新增）；`kind=official_history` 為 RMIS 歷史沿革頁（`is_full_text` 標示是否含全文）。

## 函釋 `data/interpretations/<id>.json`

課程摘錄：`sources[0].source_id = course-summaries`、`category = 課程摘錄`、`flags` 含 `course_summary`，內容取自 `config/relations/course_summaries.yaml`（教育訓練資料之文字，非函釋原文，無官方網址）。

`id = itp-` + sha256(發文字號|發文日期) 前 10 碼。同一函釋由多個來源取得時合併為一筆，`sources[]` 保留全部來源。字號相同但日期不同者不合併，標示 `docno_shared`。

| 欄位 | 說明 |
|---|---|
| docno, date, date_text | 正規化字號、ISO 日期、原始日期文字 |
| agency_text, agency_id, agency_name, historical_name, is_historical | 原始發文機關、現行業務承接機關、改制前機關 |
| category, subject, content, memo | 類別、主旨（案由摘要）、內容、備註（原文照錄） |
| sources[] | `{source_id, url, source_key, serial, fetched_at}` |
| relations[] | `{law_id, article, kind: official｜extracted｜manual, evidence, snippet}` |
| validity | `{status, confirmed, basis[], notes}`，見 update-policy.md |
| topics[], flags[] | 系統主題標記；旗標（historical_agency、source_missing、docno_shared） |
| version, content_hash, history[] | 內容版本與歷次異動前內容 |
| first_seen, last_synced, source_missing_since | 時間戳記 |

## 技術資料 `data/technical/<id>.json`

`title, series, issue, agency_id, authors, date (YYYY-MM), url, isbn, gpn, pages, license, dataset{unit_id,title,url}, topics[], raw{}`。只存書目。

## 關聯 `data/relations/`

- `official.json`：RMIS 法規對應解釋函（法規層級）；`unmatched` 為官方列示但本站尚未收錄之函釋。
- `extracted.json`：由函釋文字比對「法規名稱＋條號」所得之演算法建議。
- 人工確認：`config/relations/manual.yaml`。

## 中繼資料 `data/metadata/`

`source-index.json`（來源鍵→函釋 id）、`source-status.json`（各來源最近檢查／成功／完整比對／異動時間）、`source-audit-latest.json`、`datamoa-catalog.json`。

## 更新紀錄 `data/updates/`

`runs/<日期>_<run id>.json`：每次執行完整紀錄；`log.jsonl`：摘要（一行一次）。
