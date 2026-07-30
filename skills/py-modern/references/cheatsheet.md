# py-modern: 速查表

## 型別參數語法（PEP 695, 3.12+）

```python
# 泛型函式
def func[T](x: T) -> T: ...

# 有約束的泛型
def func[T: int](x: T) -> T: ...           # 上界
def func[T: (int, str)](x: T) -> T: ...     # 聯集約束

# 泛型類別
class MyClass[T]: ...
class MyClass[T, U]: ...
class MyClass[T: Comparable]: ...

# 型別別名
type Vector = list[float]
type Matrix[T] = list[list[T]]
type Callback[**P, R] = Callable[P, R]

# TypeVarTuple
def func[*Ts](args: tuple[*Ts]) -> tuple[*Ts]: ...

# ParamSpec
def decorator[**P, R](func: Callable[P, R]) -> Callable[P, R]: ...

# TypeVar 預設值（3.13+）
class Container[T = int]: ...
```

## f-string（PEP 701, 3.12+）

```python
# 引號重用
f"{'hello'}"              # 合法（3.12+）
f"Say {"hello"}"          # 合法

# 多行
f"""Result: {
    complex_expression()
}"""

# 帶註解
f"{value  # 這是註解
}"

# 除錯
f"{variable = }"          # 輸出 variable = value
f"{expr = :.2f}"          # 輸出 expr = 3.14
```

## match-case（3.10+）

```python
match value:
    case int(n) if n > 0:      # 值 + guard
    case str(s):                # 型別比對
    case [x, y]:                # 序列解構
    case [first, *rest]:        # 星號模式
    case {"key": v}:            # 字典模式
    case Point(x=0, y=0):      # 類別模式
    case "a" | "b" | "c":      # OR 模式
    case _ as caught:           # 捕捉任意值
    case _:                     # 萬用模式
```

## Exception Groups（3.11+）

```python
# 引發
raise ExceptionGroup("errors", [ValueError("a"), TypeError("b")])

# 捕捉（except* 只捕捉匹配的子集）
try:
    ...
except* ValueError as eg:
    for e in eg.exceptions:
        print(e)
except* TypeError as eg:
    ...
```

## typing 速查

```python
# 3.12+
from typing import override, TypedDict, Unpack

@override                          # 覆寫檢查
class RequestOpts(TypedDict): ...  # **kwargs 型別
def f(**kw: Unpack[RequestOpts]): ...

# 3.13+
from typing import TypeIs, ReadOnly
from warnings import deprecated

def is_str(v: object) -> TypeIs[str]: ...  # 型別窄化
class Cfg(TypedDict):
    x: ReadOnly[int]                        # 唯讀欄位

@deprecated("use new_func")                 # 棄用標記
def old(): ...
```

## copy.replace()（3.13+）

```python
from copy import replace
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    host: str = "localhost"
    port: int = 8080

new_cfg = replace(Config(), port=3000)
```

## Free-threaded Python（3.13+）

```bash
# 安裝 free-threaded 版本
# macOS (Homebrew)
brew install python-freethreaded

# 執行
python3.13t script.py

# 環境變數控制
PYTHON_GIL=0 python3.13t script.py   # 強制停用 GIL
PYTHON_GIL=1 python3.13t script.py   # 強制啟用 GIL
```

```python
import sys
# 檢查 GIL 狀態
if hasattr(sys, "_is_gil_enabled"):
    print(sys._is_gil_enabled())  # True/False
```

## 已移除標準庫（3.12-3.13）

| 版本 | 已移除模組 |
|------|-----------|
| 3.12 | `distutils`, `asynchat`, `asyncore`, `imp`, `smtpd` |
| 3.13 | `aifc`, `cgi`, `cgitb`, `chunk`, `crypt`, `imghdr`, `mailcap`, `msilib`, `nntplib`, `nis`, `ossaudiodev`, `pipes`, `sndhdr`, `spwd`, `sunau`, `telnetlib`, `uu`, `xdrlib` |

## Union 語法演進

```python
# 3.9 以前
from typing import Union, Optional
x: Union[int, str]
y: Optional[int]  # = Union[int, None]

# 3.10+
x: int | str
y: int | None

# 內建泛型（3.9+，免 typing 匯入）
x: list[int]          # 取代 List[int]
y: dict[str, int]     # 取代 Dict[str, int]
z: tuple[int, ...]    # 取代 Tuple[int, ...]
```
