# Codex / ChatGPT 外掛安裝指南

Plugin 名稱：`python-engineering-skills`。安裝器支援 Python 3.10+；不需要第三方套件、API key 或網路連線。Git 原始碼包含維護與測試工具，發布 ZIP 包含安裝、解除安裝與 12 組完整 skills。

## 1. 選擇安裝模式

| 模式／範圍 | 目標位置 | 使用情境 |
|---|---|---|
| `skills` / `user` | `~/.agents/skills/py-*` | Codex CLI、VM、無介面環境 |
| `skills` / `repo` | `<repo>/.agents/skills/py-*` | 只在指定專案使用 |
| `skills` / `admin` | `/etc/codex/skills/py-*` | Unix 管理者；Windows 明確拒絕 |
| `plugin` / `user` | `~/.codex/plugins/python-engineering-skills` | 支援本機 Marketplace 的環境 |
| `plugin` / `repo` | `<repo>/plugins/python-engineering-skills` | 專案 Marketplace |

Plugin 模式同步維護同一範圍下的 `.agents/plugins/marketplace.json`，保留其他 entries。`--home` 可覆寫使用者根目錄，適合隔離測試；它不影響 `admin` 範圍。

這些是目前執行腳本的檔案位置，不是把本機檔案上傳到 ChatGPT 網頁。Marketplace 可見性取決於實際執行環境與客戶端支援；本機檔案就緒不等同已在 UI 啟用 plugin。

## 2. 安裝與預覽

從解壓後的資料夾或 `main` checkout 執行：

```bash
python scripts/install_codex.py --mode skills --scope user --dry-run
python scripts/install_codex.py --mode skills --scope user
python scripts/install_codex.py --mode plugin --scope user
```

`--dry-run` 仍會檢查 JSON、路徑、來源與同名衝突，但不建立目錄或改寫檔案。Plugin 模式之後需從本機 Marketplace 安裝外掛並開啟新 session。

專案限定安裝，請把相對路徑換成實際的「另一個目標專案」：

```bash
python scripts/install_codex.py --mode skills --scope repo --repo-root ../my-project
```

來源套件與目標安裝目錄不得互相包含。因此不要把這個來源 checkout 自己當成 `--repo-root`。在 Cloud setup script 也應先指定正確套件位置，再執行上述命令；發布 ZIP 沒有開發驗證器，不能直接執行 `validate_plugin.py`。

Windows：

```powershell
.\scripts\install_codex.ps1 --mode skills --scope user
```

macOS/Linux：

```bash
sh scripts/install_codex.sh --mode skills --scope user
```

## 3. 更新與舊版遷移

新安裝含 `.python-skills-install.json`，記錄套件擁有者與每個檔案的 SHA-256。未修改的新版安裝可直接重新執行命令更新；空白/損壞紀錄、無紀錄舊版或手動修改的檔案，都會預設停止。

先備份同名安裝目錄與 marketplace 設定，確認要取代後再使用：

```bash
python scripts/install_codex.py --mode skills --scope user --force
```

`--force` 只解除所有權／內容變更保護，不解除路徑、symlink、Windows reparse point 或 manifest 名稱檢查。它不是自動備份選項。其他技能及其他外掛不在取代範圍。

## 4. 解除安裝

模式、範圍、`--home` 與 `--repo-root` 必須與原安裝相同：

```bash
python scripts/uninstall_codex.py --mode skills --scope user --dry-run
python scripts/uninstall_codex.py --mode skills --scope user
python scripts/uninstall_codex.py --mode plugin --scope user
```

同名安裝內容被修改時先備份；確定刪除才加入 `--force`。沒有安裝的目標可重複移除。損壞的 marketplace 會在任何刪除之前被拒絕，請先修正或從自行備份恢復 JSON。

## 5. 故障回復與限制

安裝器會先驗證全部輸入，再將全部新內容寫入唯一暫存目錄。每個目標的舊內容暫存於同一檔案系統，替換或設定更新失敗時會嘗試回復。若回復本身失敗，錯誤訊息列出保留的 `.python-skills-txn-*` 資料夾；請先保留它們，再依其中 `old` 內容人工復原。

這不是完整的 crash-recovery journal，也不防範具有相同系統權限的程序在檢查後惡意更換路徑。請避免並行執行安裝器，並在更新前保留重要個人修改。成功完成後，暫存舊版會移除。

安裝與解除安裝不修改 `config.toml`、模型、sandbox、核准規則或金鑰。技能文字中的命令不會被安裝器自動執行。

## 6. 開發、封裝與驗收（僅 Git 原始碼版）

```bash
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python scripts/validate_skills.py --strict
python scripts/validate_plugin.py
python -m unittest discover -s tests -v
python scripts/package_plugin.py
```

產物為 `dist/python-engineering-skills-<version>.zip` 與同名 `.zip.sha256`。封裝採固定排序、時間戳與 Unix metadata，忽略快取；相同輸入在同一壓縮工具鏈可重建相同位元組，不宣稱不同 zlib 版本必然相同。

驗收包含「封裝 → 解壓 → 移除來源 checkout → 安裝 → 更新／移除」、Unicode/空白路徑、故障注入與平台條件測試。不同平台不支援的特性必須記錄 skip，不得視為已實測通過。

## 官方格式參考

- [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [OpenAI skill authoring](https://learn.chatgpt.com/docs/build-skills)
- [Agent Skills specification](https://agentskills.io/specification)

CLI/UI 功能依客戶端版本而異；本文不假定僅加入 GitHub Marketplace 就會自動選取 `main` 或完成遠端安裝。
