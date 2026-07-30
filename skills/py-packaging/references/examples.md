# py-packaging — 完整可運行範例

## 範例 1: 最小可發布套件（hatchling + src-layout）

```
my-greeter/
├── pyproject.toml
├── README.md
├── src/
│   └── greeter/
│       ├── __init__.py
│       └── core.py
└── tests/
    └── test_core.py
```

```toml
# pyproject.toml
[build-system]
requires = ["hatchling >= 1.26"]
build-backend = "hatchling.build"

[project]
name = "my-greeter"
version = "0.1.0"
description = "簡單的打招呼工具"
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
greet = "greeter.core:main"

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.8"]
```

```python
# src/greeter/__init__.py
"""Greeter 套件"""
__version__ = "0.1.0"
```

```python
# src/greeter/core.py
"""核心模組"""

def greet(name: str, greeting: str = "Hello") -> str:
    """產生問候語"""
    return f"{greeting}, {name}!"

def main() -> None:
    """CLI 進入點"""
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(greet(name))
```

```python
# tests/test_core.py
from greeter.core import greet

def test_greet_default():
    assert greet("Alice") == "Hello, Alice!"

def test_greet_custom():
    assert greet("Bob", greeting="Hi") == "Hi, Bob!"
```

```bash
# 建置並測試
uv build
uv run pytest
uv run greet Alice  # 輸出: Hello, Alice!
```

---

## 範例 2: uv 完整工作流程

```bash
# 從零開始建立專案
uv init data-pipeline
cd data-pipeline

# 加入依賴
uv add polars httpx
uv add --dev pytest ruff mypy

# 查看依賴樹
uv tree

# 鎖定版本（自動產生 uv.lock）
uv lock

# 升級特定套件
uv lock --upgrade-package polars

# 匯出為 requirements.txt（相容舊工具）
uv export --format requirements-txt > requirements.txt

# 多 Python 版本測試
uv run --python 3.12 pytest
uv run --python 3.13 pytest

# 臨時使用未安裝的套件
uv run --with rich -- python -c "from rich import print; print('[bold]Hello![/bold]')"
```

---

## 範例 3: ruff 完整設定與整合

```toml
# pyproject.toml — 進階 ruff 設定
[tool.ruff]
target-version = "py312"
line-length = 88
src = ["src"]

[tool.ruff.lint]
select = [
    "E",     # pycodestyle errors
    "W",     # pycodestyle warnings
    "F",     # pyflakes
    "I",     # isort
    "UP",    # pyupgrade（自動升級舊語法）
    "B",     # bugbear（常見 bug 偵測）
    "SIM",   # simplify（簡化建議）
    "RUF",   # ruff 專屬規則
    "PT",    # pytest style
    "TCH",   # type checking imports
    "PERF",  # performance
    "FURB",  # refurb（現代化建議）
]
ignore = [
    "E501",  # 行長由 formatter 處理
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # 測試中允許 assert

[tool.ruff.lint.isort]
known-first-party = ["my_lib"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true
```

```bash
# 日常使用
ruff check .                 # 檢查所有問題
ruff check . --fix           # 自動修復
ruff check . --fix --unsafe-fixes  # 包含 unsafe 修復
ruff format .                # 格式化
ruff format . --check        # 檢查格式（CI 用）

# 單一檔案
ruff check src/my_lib/core.py --diff
```

---

## 範例 4: pre-commit 設定

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.0]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
```

```bash
# 安裝
pre-commit install

# 手動執行
pre-commit run --all-files
```

---

## 範例 5: Trusted Publisher — 無 Token 發布

```yaml
# .github/workflows/release.yml
name: Release to PyPI
on:
  push:
    tags: ["v*.*.*"]

permissions:
  id-token: write
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Build
        run: uv build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi  # 需要在 GitHub Settings 設定
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        # Trusted Publisher — 不需要 PYPI_API_TOKEN
        # 需在 PyPI 設定 Trusted Publisher：
        # pypi.org → Your project → Settings → Publishing
```
