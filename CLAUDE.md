# CLAUDE.md

本儲存庫的完整跨代理規範位於 [`AGENTS.md`](AGENTS.md)。Claude Code 在處理此專案前，先讀取該文件；本檔只補充 Claude Code 的入口與必要命令。

## 專案目的

這是一組可供 AI 編碼代理載入的 Python Agent Skills。主要交付物是各 `py-*/SKILL.md` 及其 `references/`，不是一般 Python 套件。

## 工作方式

1. 先讀取 `AGENTS.md` 與 `index.md`。
2. 只選一個主要 skill，再按需讀取一至兩個支援 skill。
3. 更新易變資訊前，查閱 Python、PEP、框架或套件的官方文件與 release notes。
4. 保持 `SKILL.md` 任務導向；大型範例、速查與陷阱放入 `references/`。
5. 不硬編碼 `/home/claude`、`/mnt/user-data`、使用者家目錄、API key、模型名稱或雲端環境。
6. 不要求使用者先選「全部或子集」才開始；從明確任務直接選擇最相關的 skill。
7. 修改以獨立分支處理，不直接寫入 `master`。

## 必要品質閘門

```bash
python scripts/validate_skills.py --strict
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
for skill in py-*; do agentskills validate "$skill"; done
```

Windows PowerShell：

```powershell
python scripts/validate_skills.py --strict
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
Get-ChildItem -Directory py-* | ForEach-Object { agentskills validate $_.FullName }
```

## 修改 Skill 時

- 目錄名稱與 frontmatter `name` 必須一致。
- 更新 `metadata.last-reviewed`。
- 保留 `執行流程`、`交付標準`、`延伸閱讀`、`版本相容性`。
- 同步更新 `skills-manifest.json` 與 `evals/trigger-cases.json`（若名稱、範圍或觸發描述改變）。
- 對新增或改動的程式片段檢查語法、型別、資源關閉、錯誤路徑與最低 Python 版本。
- 不使用未量測的效能倍數、過度絕對推薦或失效 API。

## 交付回報

列出：

- 修改的 skill 與原因
- 實際執行的驗證命令及結果
- 尚未驗證的平台或第三方服務
- 破壞性變更、遷移與回復方式
