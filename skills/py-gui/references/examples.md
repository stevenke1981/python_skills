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


WorkerEvent = ProgressEvent | FailureEvent


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
        try:
            while True:
                event = self.events.get_nowait()
                if isinstance(event, FailureEvent):
                    self.status.configure(text=event.message)
                else:
                    self.progress.set(event.percent / 100)
                    self.status.configure(text=event.message)
        except Empty:
            pass

        worker_alive = self.worker is not None and self.worker.is_alive()
        if worker_alive or not self.events.empty():
            self.after(50, self.poll_events)
            return

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

## 範例 3：PySide6 QThread Worker 與可生效取消

安裝：

```bash
python -m pip install pyside6
```

```python
from __future__ import annotations

import sys
import time

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Worker(QObject):
    progress = Signal(int)
    failed = Signal(str)
    finished = Signal()

    @Slot()
    def run(self) -> None:
        thread = QThread.currentThread()
        try:
            for percent in range(101):
                if thread.isInterruptionRequested():
                    return
                time.sleep(0.03)
                self.progress.emit(percent)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
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
        self.cancel_button.clicked.connect(self.cancel_job)

    @Slot()
    def start_job(self) -> None:
        if self.thread is not None and self.thread.isRunning():
            return

        thread = QThread(self)
        worker = Worker()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self.progress.setValue)
        worker.progress.connect(
            lambda value: self.status.setText(f"處理中：{value}%")
        )
        worker.failed.connect(
            lambda message: self.status.setText(f"失敗：{message}")
        )
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self.on_thread_finished)
        thread.finished.connect(thread.deleteLater)

        self.thread = thread
        self.worker = worker
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("啟動中")
        thread.start()

    @Slot()
    def cancel_job(self) -> None:
        if self.thread is not None and self.thread.isRunning():
            self.status.setText("取消中")
            self.thread.requestInterruption()

    @Slot()
    def on_thread_finished(self) -> None:
        if self.status.text() == "取消中":
            self.status.setText("已取消")
        elif not self.status.text().startswith("失敗"):
            self.status.setText("完成")
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

將 cancel slot 排入同一個被 `run()` 佔用的 worker thread，通常不會即時執行；此範例改由主執行緒呼叫 `QThread.requestInterruption()`，worker 在迴圈中查詢。若底層是單次 blocking call，該 API 本身仍必須支援 timeout/cancellation。
