# py-gui 完整範例集

> 本文件補充 [`../SKILL.md`](../SKILL.md)。所有 UI 讀寫留在主執行緒；背景工作只透過 queue 或 signal 回傳不可變事件。

## 範例 1：tkinter 表單與可測驗證

```python
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk


@dataclass(frozen=True, slots=True)
class Registration:
    name: str
    email: str


def validate_registration(name: str, email: str) -> Registration:
    cleaned_name = name.strip()
    cleaned_email = email.strip().lower()
    if not cleaned_name:
        raise ValueError("姓名不可為空")
    if "@" not in cleaned_email or cleaned_email.startswith("@"):
        raise ValueError("Email 格式不正確")
    return Registration(name=cleaned_name, email=cleaned_email)


def create_form() -> None:
    root = tk.Tk()
    root.title("使用者註冊")

    frame = ttk.Frame(root, padding=20)
    frame.grid(sticky="nsew")
    frame.columnconfigure(1, weight=1)

    name_var = tk.StringVar()
    email_var = tk.StringVar()

    ttk.Label(frame, text="姓名：").grid(row=0, column=0, sticky="e", pady=5)
    name_entry = ttk.Entry(frame, textvariable=name_var, width=32)
    name_entry.grid(row=0, column=1, sticky="ew", pady=5)

    ttk.Label(frame, text="Email：").grid(row=1, column=0, sticky="e", pady=5)
    ttk.Entry(frame, textvariable=email_var, width=32).grid(
        row=1,
        column=1,
        sticky="ew",
        pady=5,
    )

    def submit() -> None:
        try:
            registration = validate_registration(name_var.get(), email_var.get())
        except ValueError as exc:
            messagebox.showerror("驗證失敗", str(exc), parent=root)
            return
        messagebox.showinfo(
            "完成",
            f"姓名：{registration.name}\nEmail：{registration.email}",
            parent=root,
        )

    ttk.Button(frame, text="送出", command=submit).grid(
        row=2,
        column=0,
        columnspan=2,
        pady=10,
    )

    name_entry.focus_set()
    root.bind("<Return>", lambda _event: submit())
    root.mainloop()


if __name__ == "__main__":
    create_form()
```

`validate_registration()` 可在沒有 GUI 的環境單元測試；正式 email 驗證仍應依產品規則處理。

---

## 範例 2：CustomTkinter 背景工作、取消與 Queue

安裝：

```bash
python -m pip install customtkinter
```

```python
from __future__ import annotations

import time
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Thread

import customtkinter as ctk


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    percent: int
    message: str
    finished: bool = False


@dataclass(frozen=True, slots=True)
class FailureEvent:
    message: str


type WorkerEvent = ProgressEvent | FailureEvent


def run_job(events: Queue[WorkerEvent], cancelled: Event) -> None:
    try:
        for percent in range(101):
            if cancelled.is_set():
                events.put(ProgressEvent(percent, "已取消", finished=True))
                return
            time.sleep(0.03)
            events.put(ProgressEvent(percent, f"處理中：{percent}%"))
        events.put(ProgressEvent(100, "完成", finished=True))
    except Exception as exc:
        events.put(FailureEvent(f"背景工作失敗：{exc}"))


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("背景工作")
        self.geometry("420x220")
        self.protocol("WM_DELETE_WINDOW", self.close_app)

        self.events: Queue[WorkerEvent] = Queue()
        self.cancelled = Event()
        self.worker: Thread | None = None

        self.progress = ctk.CTkProgressBar(self)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=24, pady=(30, 12))

        self.status = ctk.CTkLabel(self, text="等待中")
        self.status.pack(pady=8)

        self.start_button = ctk.CTkButton(
            self,
            text="開始",
            command=self.start_job,
        )
        self.start_button.pack(pady=4)

        self.cancel_button = ctk.CTkButton(
            self,
            text="取消",
            command=self.cancelled.set,
            state="disabled",
        )
        self.cancel_button.pack(pady=4)

    def start_job(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return

        self.cancelled.clear()
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.status.configure(text="啟動中")

        self.worker = Thread(
            target=run_job,
            args=(self.events, self.cancelled),
            daemon=True,
        )
        self.worker.start()
        self.after(50, self.poll_events)

    def poll_events(self) -> None:
        finished = False
        try:
            while True:
                event = self.events.get_nowait()
                if isinstance(event, FailureEvent):
                    self.status.configure(text=event.message)
                    finished = True
                else:
                    self.progress.set(event.percent / 100)
                    self.status.configure(text=event.message)
                    finished = finished or event.finished
        except Empty:
            pass

        worker_alive = self.worker is not None and self.worker.is_alive()
        if worker_alive or not self.events.empty():
            self.after(50, self.poll_events)
            return

        if finished or not worker_alive:
            self.start_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")

    def close_app(self) -> None:
        self.cancelled.set()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
```

worker 不呼叫 `after()` 或 widget method；主執行緒定時輪詢 thread-safe queue。正式應用若不能使用 daemon thread，關閉時應以有限 deadline 等待 worker 結束。

---

## 範例 3：PySide6 QThread Worker

安裝：

```bash
python -m pip install pyside6
```

```python
from __future__ import annotations

import sys
import time

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QProgressBar, QPushButton, QVBoxLayout, QWidget


class Worker(QObject):
    progress = Signal(int)
    failed = Signal(str)
    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            for percent in range(101):
                if self._cancelled:
                    return
                time.sleep(0.03)
                self.progress.emit(percent)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True


class MainWindow(QMainWindow):
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("QThread Worker")

        self.progress = QProgressBar()
        self.status = QLabel("等待中")
        self.start_button = QPushButton("開始")
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addWidget(self.start_button)
        layout.addWidget(self.cancel_button)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self.start_button.clicked.connect(self.start_job)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)

    @Slot()
    def start_job(self) -> None:
        if self.thread is not None and self.thread.isRunning():
            return

        self.thread = QThread(self)
        self.worker = Worker()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.progress.connect(
            lambda value: self.status.setText(f"處理中：{value}%")
        )
        self.worker.failed.connect(
            lambda message: self.status.setText(f"失敗：{message}")
        )
        self.worker.finished.connect(self.finish_job)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.cancel_requested.connect(self.worker.cancel)

        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("啟動中")
        self.thread.start()

    @Slot()
    def finish_job(self) -> None:
        self.status.setText("工作已結束")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.worker = None
        self.thread = None


if __name__ == "__main__":
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    raise SystemExit(application.exec())
```

長工作若在單次 blocking call 內，單純設定 `_cancelled` 不會立刻停止；底層 API 也必須支援 timeout/cancellation。

---

## 範例 4：可正確排序型別的 ttk.Treeview

```python
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk


@dataclass(frozen=True, slots=True)
class Employee:
    name: str
    age: int
    title: str


EMPLOYEES = [
    Employee("Alice", 28, "工程師"),
    Employee("Bob", 35, "設計師"),
    Employee("Carol", 42, "經理"),
    Employee("Dave", 23, "實習生"),
]


def create_table() -> None:
    root = tk.Tk()
    root.title("員工列表")

    columns = ("name", "age", "title")
    tree = ttk.Treeview(root, columns=columns, show="headings", height=10)
    tree.pack(fill="both", expand=True, padx=12, pady=12)

    labels = {"name": "姓名", "age": "年齡", "title": "職稱"}
    rows: dict[str, Employee] = {}

    for column in columns:
        tree.heading(column, text=labels[column])

    for employee in EMPLOYEES:
        item_id = tree.insert(
            "",
            "end",
            values=(employee.name, employee.age, employee.title),
        )
        rows[item_id] = employee

    def sort_by(column: str, reverse: bool = False) -> None:
        key_functions = {
            "name": lambda employee: employee.name.casefold(),
            "age": lambda employee: employee.age,
            "title": lambda employee: employee.title.casefold(),
        }
        ordered_ids = sorted(
            rows,
            key=lambda item_id: key_functions[column](rows[item_id]),
            reverse=reverse,
        )
        for index, item_id in enumerate(ordered_ids):
            tree.move(item_id, "", index)
        tree.heading(
            column,
            command=lambda: sort_by(column, not reverse),
        )

    for column in columns:
        tree.heading(column, command=lambda value=column: sort_by(value))

    root.mainloop()


if __name__ == "__main__":
    create_table()
```

不要直接用 `Treeview.set()` 的字串值排序數字或日期；保存 typed model，再依欄位使用正確 key。
