---
name: py-packaging
description: >
  Modern Python packaging and distribution with pyproject.toml.
  Trigger when user mentions pyproject.toml, uv, hatch, ruff,
  packaging, pip install, build backend, wheel, sdist, PEP 621,
  PEP 660, setuptools, flit, poetry migration, publish to PyPI.
  Also trigger when user asks about project setup, dependency
  management, virtual environments, or modern Python toolchain.
---

# Python 打包與發布

## Quick Start（30 秒上手）

```bash
# 用 uv 建立新專案（最快方式）
uv init my-project
cd my-project

# 安裝依賴
uv add httpx rich

# 執行
uv run main.py

# 建置發行包
uv build
```

產出的 `pyproject.toml`：

```toml
[project]
name = "my-project"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "httpx",
    "rich",
]
```

## 核心概念

### 1. pyproject.toml — 唯一設定檔

PEP 621 定義了標準 `[project]` 表格，取代 setup.py / setup.cfg。所有現代工具（uv、hatch、flit、setuptools ≥61）都支援。

```toml
[build-system]
requires = ["hatchling >= 1.26"]
build-backend = "hatchling.build"

[project]
name = "my-lib"
version = "1.0.0"
description = "實用工具庫"
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
authors = [
    {name = "Alice", email = "alice@example.com"},
]
keywords = ["utils", "tools"]
classifiers = [
    "Programming Language :: Python :: 3",
    "Development Status :: 4 - Beta",
]
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.8", "mypy>=1.14"]
docs = ["mkdocs-material"]

[project.scripts]
my-tool = "my_lib.cli:main"

[project.urls]
Homepage = "https://github.com/alice/my-lib"
Documentation = "https://my-lib.readthedocs.io"
Issues = "https://github.com/alice/my-lib/issues"
```

### 2. 建置後端（Build Backend）選擇

| 後端 | 特色 | 適用場景 |
|------|------|----------|
| **hatchling** | 快速、設定少、plugin 架構 | 純 Python 庫（推薦） |
| **uv-build** | uv 原生後端 | uv 生態深度整合 |
| **setuptools** | 最廣泛支援、C 擴展 | 需要 C/Cython 的專案 |
| **flit-core** | 極簡 | 簡單純 Python 庫 |
| **maturin** | Rust + Python | PyO3 / Rust 擴展 |

### 3. uv — Rust 寫的超快套件管理

uv 取代 pip + pip-tools + venv + pyenv，速度快 10-100 倍。

```bash
# 安裝 uv
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 專案管理
uv init my-app              # 建立專案
uv add fastapi uvicorn      # 加依賴
uv add --dev pytest ruff    # 加開發依賴
uv remove requests          # 移除依賴
uv lock                     # 鎖定版本
uv sync                     # 同步環境

# Python 版本管理
uv python install 3.13      # 安裝 Python
uv python list               # 列出可用版本
uv python pin 3.12           # 固定專案版本

# 執行
uv run pytest                # 在虛擬環境中執行
uv run --with rich -- python script.py  # 臨時加入依賴

# 建置與發布
uv build                     # 產出 wheel + sdist
uv publish                   # 發布到 PyPI
```

### 4. ruff — 程式碼品質一站式工具

ruff 取代 flake8 + isort + black + pyupgrade，速度快 100 倍。

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "UP",   # pyupgrade
    "B",    # bugbear
    "SIM",  # simplify
    "RUF",  # ruff 專屬
]

[tool.ruff.format]
quote-style = "double"
docstring-code-format = true
```

```bash
ruff check .           # 檢查
ruff check . --fix     # 自動修復
ruff format .          # 格式化
```

### 5. 版本管理策略

```toml
# 方案 A: 靜態版本（手動更新）
[project]
version = "1.2.3"

# 方案 B: 動態版本（從 __init__.py 讀取）
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/my_lib/__init__.py"

# 方案 C: 從 Git tag 讀取
[tool.hatch.version]
source = "vcs"
```

## 實戰 Patterns

### Pattern 1: src-layout 專案結構

**場景**：標準的可發布 Python 庫。

```
my-lib/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── my_lib/
│       ├── __init__.py
│       ├── core.py
│       └── utils.py
└── tests/
    ├── conftest.py
    └── test_core.py
```

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-lib"
version = "0.1.0"
requires-python = ">=3.12"

# hatchling 自動偵測 src/ layout
```

### Pattern 2: Monorepo / Workspace

**場景**：多個相關套件共用一個 repo。

```toml
# pyproject.toml（根目錄）
[tool.uv.workspace]
members = ["packages/*"]

# packages/core/pyproject.toml
[project]
name = "myorg-core"
version = "0.1.0"

# packages/api/pyproject.toml
[project]
name = "myorg-api"
dependencies = ["myorg-core"]
```

```bash
uv sync                    # 同步所有 workspace 套件
uv run --package myorg-api pytest
```

### Pattern 3: GitHub Actions CI/CD 發布

**場景**：推 tag 時自動發布到 PyPI。

```yaml
# .github/workflows/publish.yml
name: Publish
on:
  push:
    tags: ["v*"]

permissions:
  id-token: write  # Trusted Publisher

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
        # Trusted Publisher — 不需要 API token
```

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| uv | 套件/專案/Python 管理 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | 取代 pip+venv+pyenv |
| ruff | lint + format | `pip install ruff` 或 `uv tool install ruff` | 取代 flake8+black+isort |
| hatch | 建置+版本+環境 | `pip install hatch` | 官方推薦建置工具 |
| mypy | 靜態型別檢查 | `pip install mypy` | `--strict` 模式推薦 |
| pyright | 型別檢查（更快） | `pip install pyright` | VS Code 整合佳 |
| pre-commit | Git hooks | `pip install pre-commit` | 提交前自動品質檢查 |
| tox / nox | 多版本測試 | `pip install tox` | CI 矩陣測試 |
| twine | 安全上傳 PyPI | `pip install twine` | uv publish 可取代 |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | uv、ruff 完整支援 |
| 3.12 | ✅ 完整支援 | PEP 621 標準 |
| 3.11 | ✅ | |
| 3.10 | ✅ | setuptools ≥61 開始支援 [project] |
| 3.9 | ⚠️ | 部分工具即將停止支援 |
