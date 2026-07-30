# py-gui 常見陷阱與解法

## 陷阱 1：在非主執行緒更新 GUI

**問題**：從 Thread 直接修改 widget 導致 crash 或畫面凍結。

```python
# ❌ 錯誤：在背景執行緒直接更新
def worker():
    result = heavy_computation()
    label.config(text=result)  # ⚠️ 可能死鎖或崩潰

threading.Thread(target=worker).start()
```

**解法**：使用 `widget.after()` 或 Queue 將更新排入主執行緒。

```python
# ✅ 正確：透過 after() 回到主執行緒
def worker():
    result = heavy_computation()
    root.after(0, label.config, {"text": result})

threading.Thread(target=worker, daemon=True).start()
```

---

## 陷阱 2：PhotoImage 被垃圾回收

**問題**：圖片顯示後突然消失（全白或空白）。

```python
# ❌ 區域變數，函式結束後被 GC
def show_image():
    img = tk.PhotoImage(file="photo.png")
    label = tk.Label(root, image=img)
    label.pack()  # 離開函式後 img 被 GC，圖片消失
```

**解法**：保持圖片的參考（reference）。

```python
# ✅ 保存在 widget 屬性上
def show_image():
    img = tk.PhotoImage(file="photo.png")
    label = tk.Label(root, image=img)
    label.image = img  # ← 關鍵：防止 GC
    label.pack()
```

---

## 陷阱 3：混用 pack() 和 grid()

**問題**：同一個 Frame 內同時使用 `pack()` 和 `grid()` 導致無限迴圈或 `TclError`。

```python
# ❌ 不可在同一容器中混用
frame = ttk.Frame(root)
ttk.Label(frame, text="A").pack()
ttk.Label(frame, text="B").grid(row=0, column=1)  # TclError!
```

**解法**：每個容器只能使用一種 geometry manager。用巢狀 Frame 分區。

```python
# ✅ 不同容器各自使用
top_frame = ttk.Frame(root)
top_frame.pack()
ttk.Label(top_frame, text="A").pack()

bottom_frame = ttk.Frame(root)
bottom_frame.pack()
ttk.Label(bottom_frame, text="B").grid(row=0, column=0)
```

---

## 陷阱 4：mainloop() 阻塞

**問題**：在 `mainloop()` 之後寫的程式碼不會執行。

```python
# ❌ 這行永遠不會執行（除非關閉視窗）
root.mainloop()
print("這行不會執行")
```

**解法**：所有邏輯放在 mainloop 之前的 callback 或事件綁定中。

```python
# ✅ 使用 after() 排程
def periodic_task():
    print("每 1 秒執行一次")
    root.after(1000, periodic_task)

root.after(1000, periodic_task)
root.mainloop()
```

---

## 陷阱 5：lambda 迴圈陷阱（late binding）

**問題**：在迴圈中用 lambda 綁定事件，所有 lambda 共享最後一個值。

```python
# ❌ 所有按鈕都印出 "Button 4"
for i in range(5):
    tk.Button(root, text=f"Button {i}", command=lambda: print(i)).pack()
```

**解法**：用預設參數捕獲當前值。

```python
# ✅ 用 default argument 捕獲
for i in range(5):
    tk.Button(root, text=f"Button {i}", command=lambda x=i: print(x)).pack()
```

---

## 陷阱 6：PySide6 忘記保持 QApplication 引用

**問題**：PySide6 應用啟動後立刻閃退。

```python
# ❌ app 被 GC
def main():
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.show()
    # app.exec() 之前 app 可能被 GC

# ✅ 確保 app 存活到 exec() 完成
def main():
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.show()
    sys.exit(app.exec())  # 阻塞直到視窗關閉
```

---

## 陷阱 7：QThread vs threading.Thread

**問題**：在 PySide6 中使用 `threading.Thread` 無法安全使用 Signal/Slot。

```python
# ❌ 原生 Thread 不支援 Qt 信號
import threading
def worker():
    obj.my_signal.emit(42)  # 跨執行緒 emit 不保證安全

# ✅ 使用 QThread + Signal
from PySide6.QtCore import QThread, Signal

class Worker(QThread):
    progress = Signal(int)

    def run(self):
        for i in range(100):
            self.progress.emit(i)  # 安全的跨執行緒通訊
```

---

## 陷阱 8：高 DPI 模糊

**問題**：Windows 高 DPI 顯示器上 tkinter 視窗模糊。

```python
# ✅ 在建立 Tk() 之前設定 DPI 感知
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor V2
except Exception:
    pass

root = tk.Tk()
```

對 PySide6：
```python
# ✅ 在建立 QApplication 之前
from PySide6.QtCore import Qt
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
```

---

## 陷阱 9：檔案對話框路徑格式

**問題**：`filedialog` 回傳空字串時未檢查，直接使用導致錯誤。

```python
# ❌ 使用者按取消時 path 是空字串
path = filedialog.askopenfilename()
with open(path) as f:  # FileNotFoundError: ''
    data = f.read()

# ✅ 先檢查
path = filedialog.askopenfilename()
if path:
    with open(path) as f:
        data = f.read()
```

---

## 陷阱 10：CustomTkinter 非同步更新 appearance

**問題**：在深色/淺色切換時，自訂的 tk 原生 widget 不會跟著變色。

**解法**：
1. 盡量使用 `ctk.CTk*` widget 系列
2. 若必須用原生 widget，手動監聽外觀變更：

```python
def _on_appearance_change(mode: str) -> None:
    bg = "#2b2b2b" if mode == "Dark" else "#ffffff"
    native_listbox.configure(bg=bg)

ctk.AppearanceModeTracker.callback_list.append(_on_appearance_change)
```
