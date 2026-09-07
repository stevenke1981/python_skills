# Changelog

## Plugin 1.1.0 — 2026-09-07

### 修正與強化

- 整合既有 Codex plugin 分支；保留 12 組 skills 與原始維護來源。
- 補齊 ZIP 內解除安裝需要的 `skills-manifest.json` 與共用 runtime。
- 安裝／移除先驗證來源、名稱、共用 JSON 與路徑，再執行 staging、替換與失敗回復。
- 新增 SHA-256 安裝紀錄；未受管理或手動修改的同名目錄，需先備份並明確指定 `--force`。
- 拒絕 traversal、來源／目標重疊、symlink、junction、特殊檔案與空來源；Windows 不接受 Unix admin 安裝範圍。
- 同步器完整驗證來源後才清理鏡像，內容未變的 skill 不重新複製。
- 封裝固定時間、排序與 Unix metadata，原子替換 ZIP 並輸出 SHA-256 sidecar；缺檔時不覆蓋既有 ZIP。
- 新增實際解壓產物、升級、移除、故障注入與路徑回歸測試；保留既有 validator 測試。
- CI 新增 `main` 觸發與 Ubuntu／Windows／macOS × Python 3.10／3.14 矩陣，成功後才產生套件。
- `py-packaging` 與 `py-testing` 更新至 2.0.1：修正 uv extras / dependency groups 範例並補上封裝驗收與故障回復要求。

### 遷移與限制

舊版無安裝紀錄，第一次更新需備份後使用 `--force`。成功替換不保留歷史備份；rollback 處理可捕捉錯誤，不保證斷電或並行寫入安全。發布 ZIP 不包含開發驗證器；完整測試及重建請使用 Git 原始碼。
