# Contributing to Python Skills

本專案接受 skill 修正、範例改善、版本更新與新主題。請以可驗證、可移植、對代理真正有操作價值為目標。

## 開始前

1. 閱讀 `AGENTS.md`。
2. 從最新 `master` 建立分支。
3. 確認修改屬於現有 skill，避免建立功能高度重疊的新目錄。
4. 對版本、API、安全與效能資訊，先查官方文件或上游發行說明。

建議分支名稱：

```text
agent/<簡短主題>
fix/<簡短主題>
docs/<簡短主題>
```

## 更新現有 Skill

至少檢查：

- frontmatter `name` 與目錄名稱一致。
- `description` 能明確觸發正確任務，也不會吸收無關任務。
- `metadata.last-reviewed` 更新為實際查證日期。
- `執行流程` 是命令式步驟，而不是純概念介紹。
- 程式碼片段與標示的最低 Python 版本相容。
- 易變 API 已依目前官方文件校正。
- 不使用未量測的效能倍數或過度絕對的推薦。
- 新增的相對連結均存在。
- 範例不包含 token、真實帳號、使用者絕對路徑或危險預設。

## 新增 Skill

建立：

```text
py-example/
├── SKILL.md
└── references/
    ├── examples.md
    ├── cheatsheet.md
    └── pitfalls.md
```

主文件應保持精簡，建議順序：

1. 目標與適用邊界
2. 執行流程
3. 決策指南
4. 實作規範
5. 最小範例
6. 驗證方式
7. 交付標準
8. 延伸閱讀
9. 版本相容性

並同步更新：

- `README.md`
- `index.md`
- `skills-manifest.json`
- `evals/trigger-cases.json`

每個 skill 至少提供兩個正向與兩個負向觸發案例。

## 文件與程式碼風格

- 說明使用繁體中文，專有名詞保留英文。
- 變數、函式與類別名稱使用英文。
- Python 範例加入必要 type hints 與錯誤處理。
- 避免依賴未定義的全域名稱。
- 片段若不是可直接執行，必須清楚標示省略的上下文。
- 使用相對路徑，不硬編碼 `/home/<user>`、`C:\Users\<user>` 或暫存輸出路徑。
- 外部連結優先指向官方文件、PEP 或上游專案。

## 本地驗證

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

## Pull Request 檢查表

- [ ] 變更範圍單一且描述清楚
- [ ] 已更新 last-reviewed
- [ ] 已補正向與負向觸發案例
- [ ] 所有相對連結有效
- [ ] 內建驗證器通過
- [ ] Agent Skills 參考驗證器通過
- [ ] 未加入秘密資訊或未授權的危險工作流
- [ ] PR 說明列出驗證命令與結果

## 版本與相容性

目前穩定基準為 Python 3.14。這不代表所有使用者專案都可立即升級；skill 必須先遵守目標專案宣告的最低版本。預覽版 Python 或套件功能應標為 preview，並提供穩定替代方案。
