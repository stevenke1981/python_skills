# py-modern: 完整可運行範例

## 範例 1：PEP 695 完整泛型系統

```python
"""PEP 695 型別參數語法示範（Python 3.12+）"""
from collections.abc import Callable, Iterator

# 型別別名
type NumberList = list[int | float]
type Transformer[T] = Callable[[T], T]
type Pair[A, B] = tuple[A, B]

# 泛型函式
def apply[T](func: Transformer[T], value: T) -> T:
    """套用轉換函式"""
    return func(value)

# 有約束的泛型
def total[T: (int, float)](items: list[T]) -> T:
    """加總數字列表"""
    return sum(items)  # type: ignore[return-value]

# 泛型類別
class Pair[A, B]:
    """不可變配對"""
    __slots__ = ("first", "second")

    def __init__(self, first: A, second: B) -> None:
        self.first = first
        self.second = second

    def map_first[C](self, func: Callable[[A], C]) -> "Pair[C, B]":
        return Pair(func(self.first), self.second)

    def __repr__(self) -> str:
        return f"Pair({self.first!r}, {self.second!r})"

# TypeVarTuple（可變長泛型）
def first_and_last[*Ts](items: tuple[*Ts]) -> tuple[*Ts]:
    """回傳原本的 tuple — 展示 TypeVarTuple 語法"""
    return items

if __name__ == "__main__":
    # 泛型函式
    doubled = apply(lambda x: x * 2, 21)
    print(f"apply: {doubled}")  # 42

    # 約束泛型
    print(f"total: {total([1, 2, 3])}")  # 6

    # 泛型類別
    p = Pair("hello", 42)
    p2 = p.map_first(str.upper)
    print(f"Pair: {p2}")  # Pair('HELLO', 42)

    # 型別別名
    nums: NumberList = [1, 2.5, 3]
    print(f"NumberList: {nums}")
```

## 範例 2：f-string 新能力（PEP 701）

```python
"""PEP 701 f-string 解放示範（Python 3.12+）"""

# 1. 巢狀引號
data = {"users": ["Alice", "Bob", "Charlie"]}
print(f"Users: {", ".join(data["users"])}")

# 2. 多行運算 + 內嵌註解
matrix = [[1, 2], [3, 4]]
result = f"""矩陣總和: {
    sum(
        val
        for row in matrix  # 走訪每一列
        for val in row     # 走訪每個元素
    )
}"""
print(result)  # 矩陣總和: 10

# 3. 格式化輸出
import datetime

now = datetime.datetime.now()
items = [
    ("Python", 3.12, "released"),
    ("Rust", 1.75, "released"),
    ("Go", 1.22, "released"),
]

# f-string 中使用格式規範
for name, ver, status in items:
    print(f"{name:<10} v{ver:<6.2f} [{status:^10}]")

# 4. 除錯用 = 語法（3.8+ 但與新 f-string 搭配更強）
x, y = 3, 4
print(f"{x = }, {y = }, {x**2 + y**2 = }")
```

## 範例 3：Structural Pattern Matching 進階

```python
"""match-case 進階模式比對示範（Python 3.10+）"""
from dataclasses import dataclass
from typing import Any

@dataclass
class Command:
    action: str
    args: list[str]

def handle_command(cmd: Command) -> str:
    """複合模式比對範例"""
    match cmd:
        # 值模式 + guard
        case Command(action="quit", args=[]):
            return "再見！"

        case Command(action="quit", args=[*extra]):
            return f"quit 不接受參數，收到: {extra}"

        # 巢狀結構比對
        case Command(action="move", args=[("north" | "south" | "east" | "west") as direction]):
            return f"往 {direction} 移動"

        # 星號模式
        case Command(action="say", args=[first, *rest]):
            return f"說: {first} (還有 {len(rest)} 句)"

        case _:
            return f"未知指令: {cmd.action}"

# 字典模式比對
def parse_event(event: dict[str, Any]) -> str:
    match event:
        case {"type": "click", "position": (int(x), int(y))}:
            return f"點擊 ({x}, {y})"
        case {"type": "keypress", "key": str(k)} if len(k) == 1:
            return f"按鍵 '{k}'"
        case {"type": str(t)}:
            return f"事件: {t}"
        case _:
            return "無法解析"

if __name__ == "__main__":
    print(handle_command(Command("quit", [])))
    print(handle_command(Command("move", ["north"])))
    print(handle_command(Command("say", ["Hello", "World"])))

    print(parse_event({"type": "click", "position": (10, 20)}))
    print(parse_event({"type": "keypress", "key": "a"}))
```

## 範例 4：Free-threaded Python 效能比較

```python
"""Free-threaded CPython 效能比較（Python 3.13t）"""
import time
import threading
from concurrent.futures import ThreadPoolExecutor

def fibonacci(n: int) -> int:
    """遞迴 Fibonacci（CPU 密集）"""
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def benchmark_sequential(tasks: list[int]) -> float:
    """序列執行"""
    start = time.perf_counter()
    results = [fibonacci(n) for n in tasks]
    elapsed = time.perf_counter() - start
    return elapsed

def benchmark_threaded(tasks: list[int]) -> float:
    """多執行緒執行"""
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        results = list(pool.map(fibonacci, tasks))
    elapsed = time.perf_counter() - start
    return elapsed

if __name__ == "__main__":
    import sys
    gil_status = "disabled" if hasattr(sys, "_is_gil_enabled") and not sys._is_gil_enabled() else "enabled"
    print(f"Python {sys.version}")
    print(f"GIL: {gil_status}\n")

    tasks = [32, 32, 32, 32]

    t_seq = benchmark_sequential(tasks)
    print(f"序列執行: {t_seq:.3f}s")

    t_par = benchmark_threaded(tasks)
    print(f"多執行緒: {t_par:.3f}s")

    speedup = t_seq / t_par if t_par > 0 else 0
    print(f"加速比:   {speedup:.2f}x")
    # GIL-enabled ≈ 1.0x, GIL-free ≈ 3-4x (視核心數)
```

## 範例 5：typing 新特性整合

```python
"""Python 3.12-3.13 typing 新特性整合範例"""
from dataclasses import dataclass
from typing import TypedDict, override

# @override（3.12+）
class Animal:
    def speak(self) -> str:
        return "..."

class Dog(Animal):
    @override
    def speak(self) -> str:
        return "Woof!"

# TypedDict + Unpack 用於 **kwargs（PEP 692, 3.12+）
class RequestOptions(TypedDict, total=False):
    timeout: float
    retries: int
    headers: dict[str, str]

def fetch(url: str, **kwargs: object) -> str:
    """發送請求——kwargs 類型安全"""
    # 實際應用中使用 Unpack[RequestOptions]
    return f"GET {url}"

# 型別別名 + 泛型的組合
type Result[T] = tuple[T, None] | tuple[None, str]

def safe_divide(a: float, b: float) -> Result[float]:
    if b == 0:
        return (None, "除以零錯誤")
    return (a / b, None)

if __name__ == "__main__":
    dog = Dog()
    print(dog.speak())  # Woof!

    val, err = safe_divide(10, 3)
    if err is None:
        print(f"結果: {val:.4f}")
    else:
        print(f"錯誤: {err}")

    val2, err2 = safe_divide(10, 0)
    print(f"錯誤: {err2}")  # 除以零錯誤
```
