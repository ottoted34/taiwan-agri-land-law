# 系統架構

```
官方來源 ──► collectors（每個來源一個模組） ──► sync（驗證、去重、雜湊比對、異常隔離、紀錄）
                                                  │
                                                  ▼
                                    data/（git 版本化 JSON，一筆一檔）
                                                  │ postprocess：關聯、效力訊號、修法影響、主題標記
                                                  ▼
                                    indexing.build ──► web/public/data（靜態 JSON）
                                                  │
                                    Vite + React 前端 ──► GitHub Pages
```

## 技術選擇

| 層 | 技術 | 理由 |
|---|---|---|
| 資料擷取與處理 | Python 3.12、requests、BeautifulSoup/lxml、PyYAML | 免費、易維護 |
| 資料保存 | 一筆一檔 JSON，存於 git | 每次異動有 git 歷史可回復；不需資料庫 |
| 搜尋 | 前端正規化子字串比對＋同義詞，於瀏覽器執行 | 中文不需斷詞即可正確找到專有名詞（如「資材室」），無伺服器成本 |
| 網站 | React 18 + Vite + TypeScript，HashRouter | 純靜態，可部署於 GitHub Pages |
| 自動化 | GitHub Actions | 免費（公開 Repository） |

## 程式目錄

- `scripts/agrilaw/collectors/`：各來源 Adapter（`moj_law.py`、`rmis.py`、`datamoa.py`、`audit.py`、`local_glrs.py`＝縣市「主管法規共用系統」地方規定、`agency_letters.py`＝林保署公文函釋與農業綠能函釋）。
- `config/local/counties.yaml`：縣市地方規定設定（查核狀態、自動同步、審核列入之法規、候選分類頁）。
- `scripts/agrilaw/sync.py`：中央同步流程，所有寫入都在這裡，確保失敗不會破壞資料。
- `scripts/agrilaw/postprocess.py`、`relations.py`、`validity.py`：衍生資料（關聯、效力訊號、修法影響）。
- `scripts/agrilaw/indexing.py`：產生網站資料；`health()` 供監控使用。
- `web/src/lib/search.ts`：搜尋引擎；`web/src/lib/scenarios.ts`：案件審查輔助情境（依事實文字自動判斷，不需使用者選擇）。

## 為何不使用 AI 問答

目前沒有可安全放在公開靜態網站、且免費又能防止濫用的 AI API（金鑰不得放前端）。依規格，先完成以檢索及規則為基礎的案件輔助；未來如導入，須採 RAG，回答只能引用本站已驗證資料並顯示出處（見 known-limitations.md）。
