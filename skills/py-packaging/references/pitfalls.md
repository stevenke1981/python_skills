# py-packaging — 常見陷阱與解法

## 陷阱 1：遺留 setup.py / setup.cfg 衝突

**問題**：多份設定重複宣告 metadata 或設定不一致，可能造成建置結果與預期不同。檔案共存本身不是錯誤；不要未檢查 native extension 或相容性需求就刪檔。

```
# 需要檢查設定來源及優先順序
my-project/
├── setup.py          # 舊式
├── setup.cfg         # 舊式
└── pyproject.toml    # 新式（但可能不完整）
```

**解法**：新專案優先採用 pyproject.toml；既有專案逐項遷移與比較產物，仍有必要的 setup.py 程式化設定可以保留。

```toml
# ✅ 新專案的宣告式設定範例；不要直接刪除既有建置設定
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

**問題**：需要建置套件時，未明確宣告 backend 與 build dependencies，可能依賴工具的 fallback 行為；只有 linter 設定的專案不一定需要建置套件。

```toml
# ❌ 缺少 build-system
[project]
name = "my-pkg"
version = "1.0.0"

[tool.ruff]
line-length = 88
```

**解法**：要建置／發布的專案應明確加入 `[build-system]`。不要把只有工具設定的 pyproject.toml 當作完整的可安裝套件。

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

**解法**：開發時通常使用可編輯安裝；發布驗收仍須測一般 wheel 安裝。單獨設定 package discovery 不會自動完成安裝。

```bash
# ✅ 可編輯安裝
uv sync        # uv 專案自動做
python -m pip install -e .  # 傳統方式
```

需要時，在 pyproject.toml 設定 package discovery：

```toml
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

**問題**：名稱衝突、保留名稱、無發布權限或重複版本都可能使發布失敗；實際原因以 index 回應為準。套件名稱會正規化（`my_pkg` == `my-pkg`），不能靠更換分隔符避開衝突。

```bash
# ❌ 名稱在 PyPI 已被佔用
$ uv publish
Error: 400 Bad Request - file already exists or name is reserved
```

**解法**：發布前先檢查名稱與擁有權；查不到版本不代表名稱一定可用。特殊名稱轉移依 PyPI 的 PEP 541 流程處理。

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

**問題**：安裝命令要求的 extra 名稱與宣告不一致。工具可能警告或報錯；不能只根據命令結束就認定額外依賴已安裝。

```toml
# ❌ 要求的 extra 名稱與宣告不一致
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
uv sync --extra dev     # [project.optional-dependencies].dev 是 extra
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

> **注意**：先確認鎖定的 build backend 版本支援 PEP 639，並驗證 wheel/sdist 中的 License-Expression 與授權檔案；不要僅由 backend 名稱推定相容。


## 陷阱 9：把 extras 與 dependency groups 混為一談

`[project.optional-dependencies]` 宣告可發布的 extras：使用 `uv sync --extra dev` 或 `python -m pip install ".[dev]"`。`[dependency-groups]` 宣告開發群組：使用 `uv sync --group dev`，不會因此產生可供 `pip install ".[dev]"` 安裝的 extra。兩者可以同名，但不是同一張表。

```toml
[dependency-groups]
dev = ["pytest", "ruff"]
```

官方參考：[uv syncing optional dependencies](https://docs.astral.sh/uv/concepts/projects/sync/#syncing-optional-dependencies)、[dependency groups](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups)、[PyPA licensing](https://packaging.python.org/en/latest/guides/licensing-examples-and-user-scenarios/)。

## 陷阱 10：只測 checkout，未測真正發布的套件

安裝器在 checkout 中能讀到的 manifest、共用模組或文件，可能未被封裝。驗收時先建置實際 ZIP/wheel，解壓到另一個含空白及非 ASCII 字元的暫存目錄，移除原始 checkout 或切換到無法依賴它的環境，再測安裝、更新與移除。不要只驗證 ZIP 可以開啟。

所有來源、設定與 manifest 必須先通過驗證才可更動目標。使用唯一同檔案系統暫存目錄，先完整 staging 再替換；測試 copy、rename 與設定寫入失敗時，舊版及其他套件仍完整。拒絕來源／目標重疊、危險名稱、symlink、junction 與空來源。

新增版本不應默默刪除同名個人檔案；提供 dry-run、所有權／雜湊檢查、明確的覆蓋選項與復原限制。可重現封裝固定檔案排序、時間與權限 metadata，排除快取與秘密；SHA-256 sidecar 是完整性檢查而不是發布者身分證明。

其他官方參考：[pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)、[src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)、[PEP 541](https://peps.python.org/pep-0541/)。
