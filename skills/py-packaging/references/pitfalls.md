# py-packaging — 常見陷阱與解法

## 陷阱 1：遺留 setup.py / setup.cfg 衝突

**問題**：專案中同時有 `setup.py` / `setup.cfg` 和 `pyproject.toml`，造成建置後端混淆。

```
# ❌ 混用三種設定檔
my-project/
├── setup.py          # 舊式
├── setup.cfg         # 舊式
└── pyproject.toml    # 新式（但可能不完整）
```

**解法**：全部遷移到 pyproject.toml。

```toml
# ✅ 只用 pyproject.toml，刪除 setup.py + setup.cfg
[build-system]
requires = ["hatchling >= 1.26"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "1.0.0"
# ... 所有 metadata 都在這裡
```

---

## 陷阱 2：缺少 `[build-system]` 表

**問題**：pyproject.toml 只有工具設定但沒有 `[build-system]`，導致 `pip install -e .` 或 `uv build` 失敗。

```toml
# ❌ 缺少 build-system
[project]
name = "my-pkg"
version = "1.0.0"

[tool.ruff]
line-length = 88
```

**解法**：永遠加上 `[build-system]`。

```toml
# ✅ 加上 build-system
[build-system]
requires = ["hatchling >= 1.26"]
build-backend = "hatchling.build"

[project]
name = "my-pkg"
version = "1.0.0"
```

---

## 陷阱 3：src-layout 安裝前 import 失敗

**問題**：使用 src-layout 但未 `pip install -e .` 就嘗試 import，Python path 找不到套件。

```python
# ❌ src-layout 沒安裝就 import
# 目錄: my-pkg/src/my_pkg/__init__.py
import my_pkg  # ModuleNotFoundError!
```

**解法**：開發時必須用可編輯安裝。

```bash
# ✅ 可編輯安裝
uv sync        # uv 專案自動做
pip install -e .  # 傳統方式

# 或者調整 build backend 設定
[tool.hatch.build.targets.wheel]
packages = ["src/my_pkg"]
```

---

## 陷阱 4：版本不一致（pyproject.toml vs __init__.py）

**問題**：pyproject.toml 中寫一個版本，`__init__.py` 中又硬編碼另一個版本。

```toml
# pyproject.toml
[project]
version = "2.0.0"  # ← 這裡是 2.0.0
```

```python
# my_pkg/__init__.py
__version__ = "1.5.0"  # ← 這裡是 1.5.0，不一致！
```

**解法**：使用動態版本，只維護一個來源。

```toml
# ✅ Hatchling 動態版本
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/my_pkg/__init__.py"
```

```python
# src/my_pkg/__init__.py
__version__ = "2.0.0"  # 唯一版本來源
```

```toml
# ✅ 或反過來：pyproject.toml 為唯一來源
[project]
version = "2.0.0"  # 唯一版本來源
```

```python
# src/my_pkg/__init__.py
from importlib.metadata import version
__version__ = version("my-pkg")  # 動態讀取
```

---

## 陷阱 5：PyPI 名稱衝突

**問題**：本地套件名稱在 PyPI 已被佔用，`uv publish` 失敗（HTTP 400）。PyPI 名稱是永久的，且會正規化（`my_pkg` == `my-pkg`）。

```bash
# ❌ 名稱在 PyPI 已被佔用
$ uv publish
Error: 400 Bad Request - file already exists or name is reserved
```

**解法**：發布前先檢查。

```bash
# ✅ 先查 PyPI 是否有同名套件
pip index versions my-desired-name
# 或直接訪問 https://pypi.org/project/my-desired-name/

# 名稱正規化規則：底線 = 連字號 = 句點
# my_pkg == my-pkg == my.pkg
# 選一個一致的，推薦用連字號（my-pkg）
```

---

## 陷阱 6：sdist 遺漏檔案

**問題**：`uv build` 產生的 sdist 沒有包含非 Python 檔案（如 README、data files），PyPI 頁面空白或安裝後缺少資源。

```toml
# ❌ 沒有明確指定要包含的檔案
[project]
readme = "README.md"  # 標記了 readme 但 sdist 可能沒包含
```

**解法**：根據 build backend 設定包含規則。

```toml
# ✅ Hatchling — 預設就包含大部分檔案，但可以明確設定
[tool.hatch.build.targets.sdist]
include = ["src/", "tests/", "README.md", "LICENSE"]

# ✅ Setuptools — 需要 MANIFEST.in 或 pyproject.toml 設定
[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
my_pkg = ["data/*.json", "templates/*.html"]
```

---

## 陷阱 7：optional-dependencies 鍵名寫錯

**問題**：optional-dependencies 中的群組名稱只支援底線、連字號、句點和字母數字，拼寫錯誤不會有任何警告。

```toml
# ❌ 群組名稱拼錯，安裝時沒有效果但也不報錯
[project.optional-dependencies]
devtools = ["pytest"]    # 寫成 devtools

# pip install "my-pkg[dev]" → 安裝 0 個額外套件（因為群組叫 devtools 不是 dev）
```

**解法**：確認群組名一致，用 uv 驗證。

```toml
# ✅ 群組名對應使用場景
[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.8"]
docs = ["sphinx>=7", "furo"]
```

```bash
# ✅ 驗證 optional-deps 有效
uv sync --group dev     # uv 會報錯如果群組不存在
pip install ".[dev]"    # 應該有安裝 pytest + ruff
pip show pytest         # 確認安裝成功
```

---

## 陷阱 8：license 欄位用了舊格式

**問題**：自 PEP 639 起，`license` 欄位推薦使用 SPDX 字串，舊的 table 格式已被標記為 deprecated。

```toml
# ❌ 舊格式（PEP 639 deprecated）
[project]
license = { file = "LICENSE" }

# 或
[project]
license = { text = "MIT License" }
```

**解法**：使用 SPDX 表示法。

```toml
# ✅ PEP 639 推薦格式
[project]
license = "MIT"

# 複合授權用 SPDX 表達式
[project]
license = "MIT OR Apache-2.0"

# 額外授權檔案
[project]
license-files = ["LICENSE", "NOTICE"]
```

> **注意**：部分舊版 build backend 尚未完全支援 PEP 639。Hatchling ≥ 1.24、uv-build 已支援。
