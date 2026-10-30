# 臺灣農地農用及農業設施容許使用法規、函釋暨農業技術知識平台

**Taiwan Agricultural Land Law & Knowledge Hub**

🌐 網站：https://ottoted34.github.io/taiwan-agri-land-law/

> **非官方網站聲明**：本網站為非官方農業法規及技術資訊整理平台，並非農業部或其他政府機關官方網站。資料僅供檢索與研究參考，實際法律適用及行政處分仍應以主管機關現行正式資料與個案審認為準。

## 功能

- 法規、函釋、農業技術資料交叉搜尋（關鍵字、發文字號、法規＋條號、民國／西元日期、同義詞）
- 法規全文、條文直接連結、附表官方連結、修正沿革、版本比較
- 函釋全文、官方原文連結、相關法條（官方列示／系統比對／人工確認分開標示）、效力查核資訊
- 改制前（112年8月1日前）機關對照
- 農地案件審查輔助（14 種情境，檢索＋規則式，產出草稿；可選縣市納入地方規定）
- 「複製給 AI」：將檢索到之條文、函釋（字號、日期、官方連結、效力查核）、技術資料整理成提示詞，自行貼到 ChatGPT／Claude 等；不登入、不需 API Key、不經本站伺服器
- 地方規定模組：依縣市分開收錄（目前臺中市），其他縣市顯示「尚未查核」；同仁可經 [Issue 表單](https://github.com/ottoted34/taiwan-agri-land-law/issues/new?template=local-regulation.yml) 提供，管理者審核後收錄
- 每日自動同步、每週完整比對、每月來源盤點、失敗隔離、更新紀錄公開

## 資料來源

| 來源 | 內容 | 同步 |
|---|---|---|
| 法務部全國法規資料庫開放資料 | 法律、命令全文 | 每日 |
| 農業部農村發展及水土保持署 農地及農舍法規檢索系統 | 通案函釋、行政規則、歷史沿革、法規對應函釋 | 每日／每週 |
| 農業部 農業資料開放平臺 | 試驗研究機構出版品書目 | 每週 |
| 臺中市政府主管法規共用系統 | 經審核列入之臺中市農地相關地方規定 | 每日 |
| 農業部林業及自然保育署 公文函釋 | 山坡地、林業用地、回饋金等農地相關函釋 | 每日／每週 |
| 農業綠能發展資訊網 函釋查詢 | 農業綠能函釋（與 RMIS 重複者合併） | 每日／每週 |

完整盤點結果與限制：[docs/source-audit.md](docs/source-audit.md)、[docs/known-limitations.md](docs/known-limitations.md)

## 文件

- [架構](docs/architecture.md)｜[資料結構](docs/data-schema.md)｜[授權](docs/data-licenses.md)｜[更新政策](docs/update-policy.md)｜[部署](docs/deployment.md)｜[維護手冊](docs/maintenance.md)｜[Google 表單評估](docs/google-form.md)

## 開發

```bash
pip install -r requirements.txt
python -m pytest tests                       # 後端測試
cd scripts && python -m agrilaw.cli sync --mode daily   # 需可連線官方網站
python -m agrilaw.cli build                  # 產生 web/public/data
cd ../web && npm ci && npm test && npm run dev
```

## 授權

程式碼 MIT。資料授權處理見 [docs/data-licenses.md](docs/data-licenses.md)。
