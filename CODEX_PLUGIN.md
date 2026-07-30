# Codex / ChatGPT 外掛安裝指南

本儲存庫同時提供：

- 可由 Marketplace 安裝的 skills-only plugin
- 可直接複製到 Codex VM 的獨立 skills
- Windows、macOS、Linux 與 CI 可使用的一鍵安裝器
- 驗證、同步與可重現 ZIP 打包工具

外掛名稱固定為 `python-engineering-skills`。版本只記錄在 `.codex-plugin/plugin.json` 與發布產物中，不會加入專案目錄名稱。

## 1. Marketplace 安裝

將 GitHub 儲存庫加入 Codex Marketplace：

```bash
codex plugin marketplace add stevenke1981/python_skills
codex plugin marketplace list
```

接著在 ChatGPT 或 Codex 的 Plugins 頁面選擇 **Python Engineering Skills** 並安裝。

更新 Marketplace：

```bash
codex plugin marketplace upgrade
```

移除 Marketplace：

```bash
codex plugin marketplace remove stevenke-python-plugins
```

## 2. 本機 Marketplace 安裝

從已下載或 clone 的儲存庫執行：

```bash
python scripts/install_codex.py --mode plugin --scope user
```

Windows PowerShell：

```powershell
.\scripts\install_codex.ps1 --mode plugin --scope user
```

安裝器會：

1. 以目前套件完整取代舊的 `python-engineering-skills` 安裝目錄。
2. 保留 `marketplace.json` 內其他外掛。
3. 不修改 `~/.codex/config.toml`。
4. 不安裝 Python 套件，也不要求 API key。

重新執行同一命令即可更新。

專案限定安裝：

```bash
python scripts/install_codex.py \
  --mode plugin \
  --scope repo \
  --repo-root /path/to/project
```

## 3. Codex VM／無介面環境安裝 skills

使用者全域：

```bash
python scripts/install_codex.py --mode skills --scope user
```

指定專案：

```bash
python scripts/install_codex.py \
  --mode skills \
  --scope repo \
  --repo-root /path/to/project
```

Linux 系統管理範圍：

```bash
sudo python scripts/install_codex.py --mode skills --scope admin
```

每個同名 skill 會先移除再完整複製，其他 skills 不受影響。

## 4. Codex Cloud setup script

可在環境設定的 setup script 內加入：

```bash
python scripts/install_codex.py --mode skills --scope user
python scripts/validate_plugin.py
```

若工作目錄就是目標 repository，也可以使用：

```bash
python scripts/install_codex.py \
  --mode skills \
  --scope repo \
  --repo-root "$PWD"
```

## 5. 解除安裝

使用者 Marketplace 外掛：

```bash
python scripts/uninstall_codex.py --mode plugin --scope user
```

使用者全域 skills：

```bash
python scripts/uninstall_codex.py --mode skills --scope user
```

專案或系統管理範圍同樣支援 `--scope repo` 與 `--scope admin`。

## 6. 開發與同步

根目錄的 `py-*` 是唯一維護來源，`skills/` 是外掛發布鏡像。修改 skill 後執行：

```bash
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
```

驗證整個外掛：

```bash
python scripts/validate_skills.py --strict
python scripts/validate_plugin.py
python -m unittest discover -s tests -v
```

建立 ZIP：

```bash
python scripts/package_plugin.py
```

產物位置：

```text
dist/python-engineering-skills-<version>.zip
```

ZIP 只包含執行外掛所需內容，不包含開發測試資料或 Git metadata。

## 7. 安全與權限

這是純 skills 外掛：

- 不包含 MCP server
- 不啟動網路服務
- 不儲存或要求 API key
- 不修改 Codex 的模型、sandbox 或核准政策
- 不自動執行 skill 文件內的範例命令

技能內涉及網路、檔案、部署或外部工具的操作，仍須遵守目標環境的權限與人工核准規則。
