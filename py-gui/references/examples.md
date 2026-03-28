# py-gui 完整範例集

## 範例 1：tkinter 表單提交

```python
"""tkinter + ttk 表單範例，含驗證與回饋"""
import tkinter as tk
from tkinter import ttk, messagebox


def create_form() -> None:
    root = tk.Tk()
    root.title("使用者註冊")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=20)
    frame.pack()

    # 姓名
    ttk.Label(frame, text="姓名：").grid(row=0, column=0, sticky="e", pady=5)
    name_var = tk.StringVar()
    ttk.Entry(frame, textvariable=name_var, width=30).grid(row=0, column=1, pady=5)

    # Email
    ttk.Label(frame, text="Email：").grid(row=1, column=0, sticky="e", pady=5)
    email_var = tk.StringVar()
    ttk.Entry(frame, textvariable=email_var, width=30).grid(row=1, column=1, pady=5)

    # 性別
    ttk.Label(frame, text="性別：").grid(row=2, column=0, sticky="e", pady=5)
    gender_var = tk.StringVar(value="male")
    gender_frame = ttk.Frame(frame)
    gender_frame.grid(row=2, column=1, sticky="w")
    ttk.Radiobutton(gender_frame, text="男", variable=gender_var, value="male").pack(side="left")
    ttk.Radiobutton(gender_frame, text="女", variable=gender_var, value="female").pack(side="left")

    # 送出
    def submit() -> None:
        name = name_var.get().strip()
        email = email_var.get().strip()
        if not name or not email:
            messagebox.showwarning("驗證失敗", "姓名和 Email 不可為空")
            return
        if "@" not in email:
            messagebox.showerror("Email 格式錯誤", "請輸入有效的 Email")
            return
        messagebox.showinfo("成功", f"姓名：{name}\nEmail：{email}\n性別：{gender_var.get()}")

    ttk.Button(frame, text="送出", command=submit).grid(row=3, columnspan=2, pady=10)
    root.mainloop()


if __name__ == "__main__":
    create_form()
```

## 範例 2：CustomTkinter 深色主題設定面板

```python
"""CustomTkinter 設定面板，含 switch、滑桿、下拉選單"""
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SettingsApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("設定面板")
        self.geometry("450x350")

        # 音量滑桿
        ctk.CTkLabel(self, text="音量", font=("", 14)).pack(anchor="w", padx=20, pady=(20, 0))
        self.volume = ctk.CTkSlider(self, from_=0, to=100, number_of_steps=100)
        self.volume.set(50)
        self.volume.pack(padx=20, fill="x")

        # 深色模式切換
        self.dark_switch = ctk.CTkSwitch(
            self, text="深色模式", command=self._toggle_mode
        )
        self.dark_switch.select()  # 預設開啟
        self.dark_switch.pack(anchor="w", padx=20, pady=15)

        # 語言選擇
        ctk.CTkLabel(self, text="語言").pack(anchor="w", padx=20)
        self.lang = ctk.CTkOptionMenu(self, values=["繁體中文", "English", "日本語"])
        self.lang.set("繁體中文")
        self.lang.pack(padx=20, fill="x")

        # 儲存按鈕
        ctk.CTkButton(self, text="儲存設定", command=self._save).pack(pady=20)

    def _toggle_mode(self) -> None:
        mode = "dark" if self.dark_switch.get() else "light"
        ctk.set_appearance_mode(mode)

    def _save(self) -> None:
        print(f"音量={self.volume.get():.0f}, 語言={self.lang.get()}")


if __name__ == "__main__":
    SettingsApp().mainloop()
```

## 範例 3：背景任務 + 進度回報

```python
"""使用 threading + after() 安全更新 GUI"""
import threading
import time
import tkinter as tk
from tkinter import ttk


class DownloadSimulator(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("模擬下載")
        self.geometry("350x150")

        self.progress = ttk.Progressbar(self, length=300, mode="determinate")
        self.progress.pack(pady=20)

        self.label = ttk.Label(self, text="點擊開始")
        self.label.pack()

        self.btn = ttk.Button(self, text="開始下載", command=self._start)
        self.btn.pack(pady=10)

    def _start(self) -> None:
        self.btn.configure(state="disabled")
        self.label.configure(text="下載中...")
        threading.Thread(target=self._download, daemon=True).start()

    def _download(self) -> None:
        for i in range(101):
            time.sleep(0.05)  # 模擬網路延遲
            # ✅ 透過 after() 回到主執行緒
            self.after(0, self._update_progress, i)
        self.after(0, self._done)

    def _update_progress(self, value: int) -> None:
        self.progress["value"] = value
        self.label.configure(text=f"{value}%")

    def _done(self) -> None:
        self.label.configure(text="下載完成！")
        self.btn.configure(state="normal")


if __name__ == "__main__":
    DownloadSimulator().mainloop()
```

## 範例 4：PySide6 列表 + 搜尋過濾

```python
"""PySide6 QListWidget 搜尋過濾"""
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLineEdit,
    QListWidget, QWidget,
)


class FilterableList(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("搜尋過濾")
        self.setMinimumSize(300, 400)

        container = QWidget()
        layout = QVBoxLayout(container)

        # 搜尋框
        self.search = QLineEdit()
        self.search.setPlaceholderText("輸入關鍵字過濾...")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        # 列表
        self.list_widget = QListWidget()
        self._all_items = [
            "Python", "JavaScript", "TypeScript", "Rust", "Go",
            "C++", "Java", "Kotlin", "Swift", "Dart",
        ]
        self.list_widget.addItems(self._all_items)
        layout.addWidget(self.list_widget)

        self.setCentralWidget(container)

    def _filter(self, text: str) -> None:
        self.list_widget.clear()
        filtered = [
            item for item in self._all_items
            if text.lower() in item.lower()
        ]
        self.list_widget.addItems(filtered)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FilterableList()
    win.show()
    sys.exit(app.exec())
```

## 範例 5：Treeview 表格顯示

```python
"""ttk.Treeview 表格顯示與排序"""
import tkinter as tk
from tkinter import ttk

DATA: list[tuple[str, int, str]] = [
    ("Alice", 28, "工程師"),
    ("Bob", 35, "設計師"),
    ("Carol", 42, "經理"),
    ("Dave", 23, "實習生"),
]


def create_table() -> None:
    root = tk.Tk()
    root.title("員工列表")

    cols = ("name", "age", "title")
    tree = ttk.Treeview(root, columns=cols, show="headings", height=10)

    tree.heading("name", text="姓名")
    tree.heading("age", text="年齡")
    tree.heading("title", text="職稱")

    tree.column("name", width=100)
    tree.column("age", width=60, anchor="center")
    tree.column("title", width=100)

    for row in DATA:
        tree.insert("", "end", values=row)

    # 點擊表頭排序
    def sort_by(col: str, reverse: bool) -> None:
        items = [(tree.set(k, col), k) for k in tree.get_children("")]
        items.sort(reverse=reverse)
        for idx, (_, k) in enumerate(items):
            tree.move(k, "", idx)
        tree.heading(col, command=lambda: sort_by(col, not reverse))

    for col in cols:
        tree.heading(col, command=lambda c=col: sort_by(c, False))

    tree.pack(fill="both", expand=True, padx=10, pady=10)
    root.mainloop()


if __name__ == "__main__":
    create_table()
```
