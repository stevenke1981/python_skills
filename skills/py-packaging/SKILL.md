---
name: py-packaging
description: >
  Package, build, lock, install, and publish Python applications or libraries with pyproject.toml, PEP 517/518/621 metadata, uv, pip, build backends, src layouts, wheel, sdist, dependency groups, entry points, CI matrices, TestPyPI, Trusted Publishing, and supply-chain checks. Use for setup.py migration, dependency reproducibility, PyPI releases, executable entry points, or packaging failures.
compatibility: Agent Skills-compatible. Packaging tools and metadata standards evolve; inspect the project backend, lockfile, target indexes, and official PyPA documentation before changing release workflows.
metadata:
  author: stevenke1981
  version: "2.0.1"
  last-reviewed: "2026-09-07"
---

# Python 打包、依賴與發布

## 目標與邊界

用此 skill 建立可重現、可在乾淨環境安裝、具有正確 metadata 與安全發布流程的 Python 專案。

`pyproject.toml` 是多種工具共用的設定入口，但不是所有專案唯一會存在的設定檔。不要宣稱 uv、Ruff 或單一 backend「完全取代」所有工具；依專案需求選擇。

## 執行流程

1. **分類專案**：應用程式、可發布 library、CLI、plugin、native extension 或 workspace。
2. **盤點現況**：`setup.py`、`setup.cfg`、`pyproject.toml`、requirements、lockfile、CI 與發布方式。
3. **決定相容契約**：distribution name、import package、最低 Python、平台、ABI、公開 entry points 與 semantic versioning。
4. **選擇 backend 與 layout**：保留既有可用 backend；新專案依需求選 setuptools、Hatchling、Flit、PDM backend、maturin 等。
5. **分離 runtime 與 development dependencies**：runtime 放 `[project]` 的 `dependencies` 陣列，開發工具使用 dependency groups 或專案既有機制。
6. **建立 lock/reproducibility 策略**：應用與部署環境鎖定完整解析；library metadata 保留合理相容範圍。
7. **建置與安裝驗證**：在乾淨環境測真正發布的 sdist、wheel 或 ZIP；移除對 checkout 的隱性依賴，測 metadata、entry point、資源、安裝、升級與移除。
8. **安全發布**：優先 OIDC Trusted Publishing、受保護 environment、不可變 tag 與 provenance。
9. **記錄遷移與回復**：列出舊安裝方式、破壞性 metadata 變更與 rollback。

## Application 與 Library 的差異

| 項目 | 應用程式 | Library |
|---|---|---|
| 依賴 | 通常提交 lockfile，部署使用精確解析 | metadata 使用相容範圍；可另鎖開發環境 |
| Python 版本 | 可依部署環境提高 | 依使用者與維護成本決定 |
| 發布 | 容器、installer、內部 artifact | wheel + sdist + package index |
| 相容性 | 控制整個 runtime | 不應任意限制下游解析 |
| CLI | 可直接交付 executable/installer | 使用 `[project.scripts]` entry point |

不要把 lockfile 內容複製成 library 的過度精確 runtime dependencies；也不要讓 production application 每次部署重新解析不受控版本。

## pyproject.toml 基本結構

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "example-tool"
version = "0.1.0"
description = "A small example command-line tool"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [
  { name = "Example Maintainer", email = "maintainer@example.invalid" },
]
dependencies = [
  "httpx>=0.27,<1",
]

[project.optional-dependencies]
docs = ["mkdocs-material>=9,<10"]

[dependency-groups]
dev = [
  "pytest>=9,<10",
  "ruff>=0.12",
]

[project.scripts]
example-tool = "example_tool.cli:main"
```

注意：

- distribution name 可含 `-`，import package 通常使用 `_`；兩者不必完全相同。
- `license` 使用有效 SPDX expression，並確保 license file 被包含。
- dependency upper bound 只在有已知不相容理由時加入；不要機械式限制每個 major。
- build backend 的特定設定放在對應 `[tool.<backend>]`。
- metadata 應盡量靜態；若 dynamic version 取自 Git tag，sdist/wheel 與 shallow clone 都要測。

## src Layout

```text
project/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── example_tool/
│       ├── __init__.py
│       └── cli.py
└── tests/
```

`src/` layout 可降低測試意外 import 工作目錄原始碼的風險。無論 layout 為何，都要以「已安裝 wheel」執行至少一組測試。

## uv 工作流

應用程式／workspace 可使用：

```bash
uv lock --check
uv sync --locked
uv run --locked pytest -q
```

規則：

- CI 使用 `--locked` 或 `--frozen`，避免靜默更新 lockfile。
- 依賴更新使用獨立 PR，保留測試與變更摘要。
- `uv sync` 預設精確同步可能移除 lockfile 之外套件；不要在未理解環境時對共享 Python 執行。
- export 到 requirements、`pylock.toml` 或 SBOM 時，將產物視為衍生檔並定義更新來源。
- uv 是選項，不是強制；既有 Poetry、PDM、pip-tools 或企業流程可保留。

## 從 setup.py 遷移

1. 先保留測試與目前 build artifact 作比較基準。
2. 將 metadata 移至 `[project]`。
3. 將 build backend 宣告放入 `[build-system]`。
4. 將 console script、package data、optional dependencies 與 native build 設定逐一遷移。
5. 不再使用 `python setup.py install/upload`。
6. 建 sdist 與 wheel，比較檔案清單、metadata 與 import 行為。
7. 在支援的每個 Python/platform 安裝 artifact 測試。
8. 確認 editable install 與一般 wheel install 差異。

## 建置與 Artifact 驗證

```bash
python -m build
python -m twine check dist/*
```

還要驗證：

- sdist 可在沒有 VCS metadata 的環境建出 wheel。
- wheel 中包含必要 package data、型別標記、license、templates 與 migrations。
- wheel 不包含測試秘密、cache、模型權重或意外大型檔案。
- 安裝後 entry point 可執行。
- `importlib.metadata` 顯示正確版本與 dependencies。
- 以 `--no-deps` 安裝 wheel 能揭露未宣告 runtime dependency。
- native wheel 在目標平台/ABI 測試，不能只發布開發機 wheel。

簡化的乾淨環境測試：

```bash
python -m venv .venv-wheel-test
. .venv-wheel-test/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-deps dist/*.whl
python -c "import example_tool"
example-tool --help
```

Windows activation 語法不同；CI 應直接使用 venv 內的 Python 路徑以避免 shell 差異。

## 發布流程

### 推薦順序

1. version 與 changelog 已確認。
2. 所有支援 Python/OS 測試通過。
3. 從乾淨 tag/commit 建置 artifacts。
4. 驗證 sdist、wheel、metadata、hash 與安裝。
5. 先發布 TestPyPI 或內部 staging index（適用時）。
6. 使用受保護 environment 與 Trusted Publishing 發布 PyPI。
7. 安裝正式 index 的 artifact 做 smoke test。
8. 建立 release notes 與 provenance/SBOM（依風險需求）。

Trusted Publishing 透過 CI OIDC 身分發布，不需要長期 PyPI API token。workflow 只在 publish job 給 `id-token: write`，其他 job 保持 `contents: read`。

不要讓 fork PR、任意 branch 或未受保護 workflow 取得發布權限。

## 供應鏈與依賴安全

- lockfile、artifact 與 action 應可追溯到 commit/tag。
- 對 dependency confusion 使用明確 index policy；不要混用公開與私有同名套件而無優先規則。
- 審查 direct URL、Git dependency、editable path 與未簽章 binary。
- 執行 vulnerability/audit 工具，但理解其資料庫與 false positive。
- 產生 hash、SBOM 或 provenance 時，在 CI 保留 artifact。
- 預覽 malware check 或新解析器只能 opt-in，不取代正式審查。
- 秘密不可寫入 `.pypirc`、workflow log、artifact 或 source distribution。

## 常見失敗

- `ModuleNotFoundError`：package discovery、src layout、缺少 `__init__.py` 或未宣告 package。
- wheel 缺檔：package data/backend include 設定不完整。
- sdist 可建、wheel 不可裝：runtime dependency 或 build hook 問題。
- 本機可建、CI 失敗：依賴 VCS、環境變數、系統 library 或未提交檔案。
- editable install 正常、wheel 失敗：測試只 import source tree。
- version 不一致：多個 version source 或 dynamic version 在 shallow clone 無資料。
- PyPI 拒絕：版本已存在、metadata 不合法、OIDC publisher 綁定錯誤。

## 交付標準

- project type、最低 Python、平台、ABI 與公開 entry points 已定義。
- `[build-system]`、`[project]` 與 backend 設定清楚且不互相矛盾。
- application/deployment 使用可重現 lock；library metadata 不過度鎖死下游。
- sdist 與 wheel 均可在乾淨環境建置、安裝與 smoke test。
- package data、license、typing 與 metadata 已檢查。
- CI 不會靜默改 lockfile，dependency update 有獨立驗證。
- 發布使用最小權限與 Trusted Publishing，無長期 token。
- release 可追溯到 tag/commit，並有 rollback/修補策略。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)
- [Python Packaging User Guide](https://packaging.python.org/en/latest/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [uv project documentation](https://docs.astral.sh/uv/concepts/projects/)

## 版本相容性

| 環境 | 建議 |
|---|---|
| Python 3.14 | 穩定維護基準；native wheels 需逐平台驗證 |
| Python 3.10–3.13 | 支援；metadata 與語法遵守最低版本 |
| pyproject/PEP 621 | 優先標準 metadata，backend-specific 設定另放 tool table |
| uv | 適合 lock/sync/workspace；依實際版本文件使用 |
| Preview Python/backend | 僅 compatibility job，不作正式發布唯一環境 |
