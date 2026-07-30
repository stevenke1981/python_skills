# py-packaging — 速查表

## uv 指令速查

| 指令 | 說明 |
|------|------|
| `uv init [name]` | 建立新專案 |
| `uv add pkg` | 加入依賴 |
| `uv add --dev pkg` | 加入開發依賴 |
| `uv add --group lint ruff` | 加入自訂群組依賴 |
| `uv remove pkg` | 移除依賴 |
| `uv lock` | 產生/更新 lockfile |
| `uv lock --upgrade` | 升級所有至最新 |
| `uv lock --upgrade-package pkg` | 只升級指定套件 |
| `uv sync` | 同步虛擬環境 |
| `uv run cmd` | 在虛擬環境中執行 |
| `uv run --with pkg cmd` | 臨時加入依賴執行 |
| `uv build` | 建置 wheel + sdist |
| `uv publish` | 發布到 PyPI |
| `uv tree` | 依賴樹 |
| `uv export --format requirements-txt` | 匯出 requirements |
| `uv python install 3.13` | 安裝 Python |
| `uv python list` | 列出可用版本 |
| `uv python pin 3.12` | 固定版本 |
| `uv tool install ruff` | 全域安裝 CLI 工具 |
| `uv tool run black .` | 一次性執行工具 |
| `uv cache clean` | 清除快取 |

## pyproject.toml 必備欄位

```toml
[build-system]
requires = ["hatchling >= 1.26"]
build-backend = "hatchling.build"

[project]
name = "my-pkg"            # 必填
version = "1.0.0"          # 必填（或 dynamic）
requires-python = ">=3.12" # 強烈建議
description = "..."        # PyPI 顯示
readme = "README.md"       # PyPI 長描述
license = "MIT"            # SPDX 表示法（PEP 639）
```

## 依賴版本語法

| 語法 | 意義 |
|------|------|
| `requests` | 任何版本 |
| `requests>=2.28` | 最低版本 |
| `requests>=2.28,<3` | 版本範圍 |
| `requests~=2.28` | 相容版本（>=2.28, <2.29） |
| `requests==2.31.0` | 精確版本（鎖死） |
| `requests[security]` | 包含 extra |
| `requests; python_version>="3.12"` | 環境標記 |

## 專案結構速查

```
# src-layout（推薦：避免安裝前 import 混淆）
my-pkg/
├── pyproject.toml
├── src/
│   └── my_pkg/
│       ├── __init__.py
│       └── core.py
└── tests/
    └── test_core.py

# flat-layout（簡單腳本或小專案）
my-pkg/
├── pyproject.toml
├── my_pkg/
│   ├── __init__.py
│   └── core.py
└── tests/
    └── test_core.py
```

## 建置後端設定

```toml
# Hatchling（推薦）
[build-system]
requires = ["hatchling >= 1.26"]
build-backend = "hatchling.build"

# uv-build
[build-system]
requires = ["uv-build >= 0.7"]
build-backend = "uv_build"

# Setuptools
[build-system]
requires = ["setuptools >= 75"]
build-backend = "setuptools.build_meta"

# Flit
[build-system]
requires = ["flit_core >= 3.9"]
build-backend = "flit_core.buildapi"

# Maturin (Rust)
[build-system]
requires = ["maturin >= 1.7"]
build-backend = "maturin"
```

## ruff 指令速查

```bash
ruff check .                    # lint 檢查
ruff check . --fix              # 自動修復
ruff check . --select I --fix   # 只跑 isort
ruff format .                   # 格式化
ruff format . --check           # 格式檢查（CI 用）
ruff rule E501                  # 查詢規則說明
ruff linter                     # 列出所有 linter
```

## 常用 ruff 規則集

| 代碼 | 來源 | 說明 |
|------|------|------|
| `E`, `W` | pycodestyle | 風格錯誤/警告 |
| `F` | pyflakes | 邏輯錯誤 |
| `I` | isort | import 排序 |
| `UP` | pyupgrade | 升級舊語法 |
| `B` | bugbear | 常見 bug |
| `SIM` | simplify | 簡化建議 |
| `PT` | pytest-style | pytest 慣例 |
| `RUF` | ruff | ruff 專屬 |
| `S` | bandit | 安全性 |
| `TCH` | type-checking | TYPE_CHECKING 區塊 |
| `PERF` | perflint | 效能 |
| `FURB` | refurb | 現代化 |

## hatch 指令速查

```bash
hatch new my-project         # 建立專案
hatch env create             # 建立環境
hatch run test               # 跑指定腳本
hatch build                  # 建置
hatch publish                # 發布
hatch version minor          # 版本遞增（0.1.0 → 0.2.0）
hatch version patch          # 版本遞增（0.1.0 → 0.1.1）
hatch fmt                    # 格式化
hatch fmt --check            # 格式檢查
```

## 發布到 PyPI 速查

```bash
# 方式 1: uv（推薦）
uv build
uv publish

# 方式 2: twine
pip install build twine
python -m build
twine check dist/*
twine upload dist/*

# 測試 PyPI
uv publish --publish-url https://test.pypi.org/legacy/
# 或
twine upload --repository testpypi dist/*
```

## .gitignore 範本

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/

# 環境
.venv/
.python-version

# 工具
.mypy_cache/
.ruff_cache/
.pytest_cache/
htmlcov/
.coverage

# IDE
.vscode/
.idea/
```

## pyproject.toml 工具設定彙整

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --strict-markers"

[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
fail_under = 80
show_missing = true
```
