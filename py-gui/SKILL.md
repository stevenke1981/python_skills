---
name: py-gui
description: >
  Python desktop GUI development with tkinter, CustomTkinter, PySide6, and PyQt6.
  Trigger when user mentions GUI, desktop app, tkinter, CustomTkinter, PySide6, PyQt6,
  Qt for Python, window, widget, dialog, form, button, layout, event loop, mainloop,
  Tk, ttk, QWidget, QMainWindow, signal slot, dark mode UI, tray icon, system tray.
  Also trigger when user asks about cross-platform desktop application, rapid prototyping UI,
  or packaging GUI app with PyInstaller / Nuitka.
---

# Python GUI 桌面應用開發

## Quick Start（30 秒上手）

```python
"""使用 CustomTkinter 建立現代深色視窗"""
import customtkinter as ctk          # pip install customtkinter

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Hello GUI")
app.geometry("400x200")

label = ctk.CTkLabel(app, text="歡迎使用 Python GUI 🎉", font=("", 20))
label.pack(pady=30)

ctk.CTkButton(app, text="按我", command=lambda: label.configure(text="你好！")).pack()
app.mainloop()
```

## 核心概念

### 1. 三大主流框架比較

| 特性 | tkinter / ttk | CustomTkinter | PySide6 / PyQt6 |
|------|---------------|---------------|-----------------|
| 安裝 | 內建 stdlib | `pip install customtkinter` | `pip install pyside6` |
| 授權 | PSF (自由) | MIT | LGPLv3 / GPLv3 |
| 外觀 | 原生 + ttk 主題 | 現代扁平深色/淺色 | 原生 + 自訂 QSS |
| 學習曲線 | 低 | 低 (tkinter 延伸) | 中高 |
| 功能豐富度 | 基礎 | 中 | 很高 (2D/3D/Web/多媒體) |
| Widget 數量 | ~30 | ~20 (封裝 tkinter) | 數百個 |
| 適用場景 | 輕量工具 UI | 快速原型 / 美觀小工具 | 大型商業應用 |

### 2. Widget 層次與容器

```python
"""tkinter widget 階層範例"""
import tkinter as tk
from tkinter import ttk

root = tk.Tk()                       # 根視窗（唯一）
root.title("Widget 階層")

# Frame 作為容器
frame = ttk.Frame(root, padding=10)
frame.pack(fill="both", expand=True)

# 子 widget 放入 frame
ttk.Label(frame, text="姓名：").grid(row=0, column=0, sticky="e")
entry = ttk.Entry(frame, width=25)
entry.grid(row=0, column=1, padx=5, pady=5)

ttk.Button(frame, text="送出", command=lambda: print(entry.get())).grid(row=1, columnspan=2)
root.mainloop()
```

### 3. Geometry Manager（佈局管理器）

| 管理器 | 特點 | 適用場景 |
|--------|------|----------|
| `pack()` | 按序堆疊（上/下/左/右） | 簡單線性排列 |
| `grid()` | 行列網格 | 表單、對齊佈局 |
| `place()` | 絕對/相對座標 | 精確定位（少用） |

> ⚠️ **同一個 Frame 內不可混用 `pack` 和 `grid`**，否則會進入無限迴圈。

### 4. 事件綁定與 Variable

```python
import tkinter as tk

root = tk.Tk()
status = tk.StringVar(value="等待中...")  # 變數 coupling

# trace 監聽變數變更
status.trace_add("write", lambda *_: print(f"狀態: {status.get()}"))

# bind 綁定事件
entry = tk.Entry(root, textvariable=status)
entry.pack()
entry.bind("<Return>", lambda e: print("按了 Enter"))

# 鍵盤快捷鍵
root.bind("<Control-q>", lambda e: root.destroy())
root.mainloop()
```

### 5. 多執行緒模型

```python
"""GUI 主執行緒 + 背景工作執行緒"""
import threading
import time
import customtkinter as ctk

class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("多執行緒")
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(padx=20, pady=20)
        self.progress.set(0)
        ctk.CTkButton(self, text="開始背景工作", command=self._start).pack()

    def _start(self) -> None:
        # 在背景執行緒執行耗時任務
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        for i in range(101):
            time.sleep(0.03)
            # ✅ 使用 after() 回到主執行緒更新 UI
            self.after(0, self.progress.set, i / 100)

App().mainloop()
```

## 實戰 Patterns

### Pattern 1: MVC 架構分離

**場景**：中大型 GUI 應用需要維護性

```python
from dataclasses import dataclass, field

# --- Model ---
@dataclass
class TodoModel:
    items: list[str] = field(default_factory=list)

    def add(self, text: str) -> list[str]:
        return TodoModel(items=[*self.items, text]).items

# --- View (tkinter) ---
class TodoView(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)
        self.entry = ctk.CTkEntry(self, placeholder_text="新增待辦事項")
        self.entry.pack(side="left", padx=5)
        self.add_btn = ctk.CTkButton(self, text="新增")
        self.add_btn.pack(side="left")
        self.listbox = tk.Listbox(self, height=10)
        self.listbox.pack(fill="both", expand=True, pady=5)

# --- Controller ---
class TodoController:
    def __init__(self, view: TodoView, model: TodoModel) -> None:
        self.view = view
        self.model = model
        self.view.add_btn.configure(command=self._on_add)

    def _on_add(self) -> None:
        text = self.view.entry.get().strip()
        if text:
            self.model.items = self.model.add(text)
            self.view.listbox.insert("end", text)
            self.view.entry.delete(0, "end")
```

**注意**：保持 Model 不依賴任何 GUI import。

### Pattern 2: 對話框與訊息

**場景**：使用者互動回饋

```python
from tkinter import messagebox, filedialog, simpledialog

# 訊息框
messagebox.showinfo("完成", "檔案已儲存！")
messagebox.askyesno("確認", "確定要刪除？")

# 檔案選擇
path = filedialog.askopenfilename(
    filetypes=[("Python 檔案", "*.py"), ("所有檔案", "*.*")]
)

# 簡單輸入
name = simpledialog.askstring("輸入", "請輸入名稱：")
```

### Pattern 3: PySide6 Signal/Slot

**場景**：Qt 應用的事件驅動

```python
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Signal, QObject
import sys

class Counter(QObject):
    """自訂 Signal"""
    value_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._value = 0

    def increment(self) -> None:
        self._value += 1
        self.value_changed.emit(self._value)  # 發送信號

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.counter = Counter()
        btn = QPushButton("點擊計數")
        btn.clicked.connect(self.counter.increment)  # Slot 連接
        self.counter.value_changed.connect(
            lambda v: btn.setText(f"已點擊 {v} 次")
        )
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(btn)
        self.setCentralWidget(container)

app = QApplication(sys.argv)
win = MainWindow()
win.show()
sys.exit(app.exec())
```

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| tkinter / ttk | 內建 GUI | 標準庫 | 輕量首選 |
| CustomTkinter | 現代外觀 | `pip install customtkinter` | 基於 tkinter |
| PySide6 | Qt 官方綁定 | `pip install pyside6` | LGPLv3 可商用 |
| PyQt6 | Qt 社群綁定 | `pip install pyqt6` | GPL/商業雙授權 |
| ttkbootstrap | Bootstrap 風格 ttk | `pip install ttkbootstrap` | 56+ 主題 |
| Pillow | 圖片處理 | `pip install pillow` | ImageTk 顯示圖片 |
| PyInstaller | 打包 exe | `pip install pyinstaller` | `--onefile --windowed` |
| Nuitka | 編譯打包 | `pip install nuitka` | 效能更好 |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | CustomTkinter / PySide6 持續更新 |
| 3.12 | ✅ | 所有框架穩定支援 |
| 3.11 | ✅ | tkinter、PySide6 6.5+ |
| 3.10 | ⚠️ 部分 | CustomTkinter 可能停止支援 |
