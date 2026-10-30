# 部署

## 一次性設定（Repository 擁有者在 GitHub 網頁操作）

1. Settings → General → Danger Zone → Change visibility → **Public**（公開 Repository 才能免費使用 Actions 與 Pages）。
2. Settings → Pages → Build and deployment → Source 選 **GitHub Actions**。
3. Settings → Actions → General → Workflow permissions 維持預設即可（各工作流程已自行宣告最小權限）。

## 部署流程

- 程式或設定變更推送到 `main` 時，`deploy` 工作流程自動建置部署。
- 資料更新流程（update-laws、update-technical、source-audit）在提交資料後，以 `workflow_call` **直接呼叫** `deploy`，不依賴 `GITHUB_TOKEN` 推送事件觸發（該類推送不會觸發其他工作流程）。
- 部署後自動讀取線上 `data/manifest.json` 驗證新版本已上線。
- 建置失敗時不部署，網站維持上一版。

網址：`https://ottoted34.github.io/taiwan-agri-land-law/`
