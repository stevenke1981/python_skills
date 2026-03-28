# py-modern: 常見陷阱與解法

## 陷阱 1：PEP 695 與舊式 TypeVar 混用

**問題**：新語法與舊式 `TypeVar` 分屬不同作用域，混用會導致型別不一致。

```python
# ❌ 錯誤：T 來自 PEP 695，但方法用了舊式 TypeVar
from typing import TypeVar
_T = TypeVar("_T")

class Box[T]:
    def convert(self, func: ...) -> _T:  # _T ≠ T
        ...
```

**解法**：統一使用新語法，或統一使用舊語法。

```python
# ✅ 全部用新語法
class Box[T]:
    def convert[U](self, func: ...) -> U:
        ...
```

## 陷阱 2：match-case 中的名稱綁定 vs 常數比對

**問題**：裸名稱（bare name）永遠是「捕捉」模式，不是常數比對。

```python
# ❌ 這不是比對 HTTP_OK 常數，而是將 value 綁定到 HTTP_OK
HTTP_OK = 200

match status:
    case HTTP_OK:  # 永遠匹配！HTTP_OK 被重新賦值
        print("OK")
```

**解法**：使用 dotted name（帶點存取）或 literal（字面值）。

```python
import http

# ✅ 方法 1：使用字面值
match status:
    case 200:
        print("OK")

# ✅ 方法 2：使用 dotted name
match status:
    case http.HTTPStatus.OK:
        print("OK")

# ✅ 方法 3：使用 guard
match status:
    case code if code == HTTP_OK:
        print("OK")
```

## 陷阱 3：f-string 中的反斜線（3.12 以前的限制）

**問題**：Python 3.11 及以前，f-string 不允許反斜線和引號重用。

```python
# ❌ 在 Python 3.11 會 SyntaxError
name = f"{'hello'}"           # 引號衝突
path = f"C:\n{'new'}"         # 反斜線問題
```

**解法**：升級到 3.12+，或在舊版本中提取到變數。

```python
# 3.11 相容寫法
greeting = 'hello'
name = f"{greeting}"

# 3.12+ 直接可用
name = f"{'hello'}"
```

## 陷阱 4：type alias 與 TypeAlias 混淆

**問題**：3.12 的 `type` 語句 vs 3.10 的 `TypeAlias` 行為不同。

```python
from typing import TypeAlias

# 3.10 方式——立即求值
Vector: TypeAlias = list[float]

# 3.12 方式——延遲求值（lazy evaluation）
type Vector = list[float]

# ❌ 注意：type 語句中的前向引用自動解析
# 但 TypeAlias 需要字串標註
type Tree[T] = T | list[Tree[T]]  # ✅ 直接遞迴
```

**要點**：`type` 語句的右側是延遲求值的，支援直接遞迴定義。

## 陷阱 5：Free-threaded Python 的套件相容性

**問題**：多數 C 擴充套件尚未為 free-threaded Python 做好準備。

```python
# ❌ 以下套件可能在 GIL-free 模式下出問題
import numpy as np      # 部分操作可能不安全
import pandas as pd     # 內部有非執行緒安全操作
```

**解法**：

1. 生產環境暫時保持 GIL 啟用
2. 使用 `PYTHON_GIL=1` 環境變數作為安全開關
3. 持續追蹤套件的 free-threaded 支援狀態

```bash
# 檢查套件是否聲明支援 free-threaded
pip install --only-binary :all: numpy  # 確保安裝預編譯版本
```

## 陷阱 6：except* 不能與 except 混用

**問題**：在同一個 try 區塊中，`except*` 和 `except` 不能混用。

```python
# ❌ SyntaxError
try:
    ...
except ValueError:
    ...
except* TypeError:  # 不能混用
    ...
```

**解法**：統一使用其中一種。

```python
# ✅ 全部用 except*
try:
    ...
except* ValueError as eg:
    ...
except* TypeError as eg:
    ...
```

## 陷阱 7：已移除標準庫模組

**問題**：3.12/3.13 移除了大量「老舊電池」模組，直接 import 會失敗。

```python
# ❌ Python 3.12 已移除
import distutils        # 改用 setuptools 或 sysconfig
import imp              # 改用 importlib

# ❌ Python 3.13 已移除
import cgi              # 改用 urllib.parse 或框架內建
import telnetlib        # 改用 telnetlib3（第三方）
import nntplib          # 無直接替代
```

**解法**：查閱遷移指南，使用推薦的替代方案。

```python
# distutils → setuptools / sysconfig
from sysconfig import get_paths
print(get_paths()["purelib"])

# cgi.parse_qs → urllib.parse.parse_qs
from urllib.parse import parse_qs
params = parse_qs("a=1&b=2")

# imp → importlib
import importlib
mod = importlib.import_module("os.path")
```

## 陷阱 8：3.12 comprehension 變數作用域改變

**問題**：Python 3.12 對 comprehension 的實作做了重大變更（PEP 709），
comprehension 不再建立獨立的函式框架，而是在外圍作用域中內聯執行。

```python
# 3.11: i 洩漏到外層（有時依賴此行為）
x = [i for i in range(3)]
# print(i)  # 3.11: 2, 3.12: NameError

# 注意：雖然 PEP 709 改了實作，但語義保持一致
# comprehension 的迭代變數仍然不會洩漏
```

**要點**：正式語義未改變（變數不該洩漏），但若舊程式碼依賴了 CPython 過去的洩漏行為，升級時要注意。
