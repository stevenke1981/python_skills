# py-gui 速查表

## tkinter Widget 速查

| Widget | 用途 | 範例 |
|--------|------|------|
| `tk.Label` | 文字標籤 | `tk.Label(root, text="Hello")` |
| `tk.Button` | 按鈕 | `tk.Button(root, text="OK", command=fn)` |
| `tk.Entry` | 單行輸入 | `tk.Entry(root, textvariable=var)` |
| `tk.Text` | 多行文字 | `tk.Text(root, height=10, width=40)` |
| `tk.Listbox` | 列表選擇 | `tk.Listbox(root, selectmode="single")` |
| `tk.Canvas` | 繪圖區 | `tk.Canvas(root, width=400, height=300)` |
| `tk.Frame` | 容器 | `tk.Frame(root, padding=10)` |
| `tk.Checkbutton` | 勾選框 | `tk.Checkbutton(root, variable=bool_var)` |
| `tk.Radiobutton` | 單選 | `tk.Radiobutton(root, value="A", variable=v)` |
| `tk.Scale` | 滑桿 | `tk.Scale(root, from_=0, to=100)` |
| `tk.Spinbox` | 數字微調 | `tk.Spinbox(root, from_=0, to=10)` |
| `tk.Menu` | 選單 | `menubar = tk.Menu(root)` |

## ttk 增強 Widget

| Widget | 說明 |
|--------|------|
| `ttk.Treeview` | 樹狀/表格 |
| `ttk.Notebook` | 頁籤容器 |
| `ttk.Progressbar` | 進度條 |
| `ttk.Combobox` | 下拉選單 |
| `ttk.Separator` | 分隔線 |
| `ttk.Sizegrip` | 視窗調整握把 |

## Geometry Manager 比較

### pack()
```python
widget.pack(side="top", fill="x", expand=True, padx=5, pady=5)
# side: top, bottom, left, right
# fill: none, x, y, both
```

### grid()
```python
widget.grid(row=0, column=1, sticky="nsew", padx=5, pady=5, columnspan=2)
# sticky: n, s, e, w 或組合 (nsew = 填滿)
# 記得設定 columnconfigure / rowconfigure weight
root.columnconfigure(0, weight=1)
```

### place()
```python
widget.place(relx=0.5, rely=0.5, anchor="center")
# relx/rely: 0.0~1.0 相對位置
# x/y: 絕對像素
```

## 事件綁定語法

| 事件 | 說明 |
|------|------|
| `<Button-1>` | 滑鼠左鍵點擊 |
| `<Button-3>` | 滑鼠右鍵 |
| `<Double-Button-1>` | 雙擊 |
| `<Return>` | Enter 鍵 |
| `<Key>` | 任意鍵 |
| `<Control-s>` | Ctrl+S |
| `<Alt-F4>` | Alt+F4 |
| `<FocusIn>` | 取得焦點 |
| `<FocusOut>` | 失去焦點 |
| `<Configure>` | 視窗大小改變 |
| `<MouseWheel>` | 滑鼠滾輪 |

```python
# 綁定到 widget
widget.bind("<Button-1>", lambda event: print(event.x, event.y))

# 綁定到根視窗（全域）
root.bind_all("<Control-q>", lambda e: root.destroy())
```

## Variable 類型

| 類型 | 用途 | 預設值 |
|------|------|--------|
| `tk.StringVar()` | 字串 | `""` |
| `tk.IntVar()` | 整數 | `0` |
| `tk.DoubleVar()` | 浮點數 | `0.0` |
| `tk.BooleanVar()` | 布林值 | `False` |

```python
var = tk.StringVar(value="預設值")
var.trace_add("write", callback)  # 監聽變更
var.get()                         # 取值
var.set("新值")                   # 設值
```

## CustomTkinter 對照表

| tkinter | CustomTkinter | 備註 |
|---------|---------------|------|
| `tk.Button` | `ctk.CTkButton` | 支援 corner_radius |
| `tk.Entry` | `ctk.CTkEntry` | 支援 placeholder |
| `tk.Label` | `ctk.CTkLabel` | 支援 font tuple |
| `tk.Frame` | `ctk.CTkFrame` | 自動圓角 |
| `tk.Checkbutton` | `ctk.CTkCheckBox` | 現代外觀 |
| `tk.Radiobutton` | `ctk.CTkRadioButton` | - |
| `ttk.OptionMenu` | `ctk.CTkOptionMenu` | 下拉選單 |
| `tk.Toplevel` | `ctk.CTkToplevel` | 子視窗 |
| `ttk.Progressbar` | `ctk.CTkProgressBar` | 圓角進度條 |
| `tk.Scrollbar` | `ctk.CTkScrollbar` | - |
| - | `ctk.CTkSwitch` | 新增 Widget |
| - | `ctk.CTkSlider` | 新增 Widget |
| - | `ctk.CTkSegmentedButton` | 新增 Widget |
| - | `ctk.CTkTextbox` | 新增 Widget |
| - | `ctk.CTkTabview` | 頁籤容器 |
| - | `ctk.CTkScrollableFrame` | 可捲動 Frame |

## PySide6 常用類別

| 模組 | 類別 | 用途 |
|------|------|------|
| `QtWidgets` | `QApplication` | 應用程式實例 |
| `QtWidgets` | `QMainWindow` | 主視窗 |
| `QtWidgets` | `QWidget` | 基礎 Widget |
| `QtWidgets` | `QPushButton` | 按鈕 |
| `QtWidgets` | `QLabel` | 標籤 |
| `QtWidgets` | `QLineEdit` | 單行輸入 |
| `QtWidgets` | `QTextEdit` | 多行文字 |
| `QtWidgets` | `QComboBox` | 下拉選單 |
| `QtWidgets` | `QVBoxLayout` | 垂直佈局 |
| `QtWidgets` | `QHBoxLayout` | 水平佈局 |
| `QtWidgets` | `QGridLayout` | 網格佈局 |
| `QtWidgets` | `QFileDialog` | 檔案對話框 |
| `QtWidgets` | `QMessageBox` | 訊息框 |
| `QtCore` | `Signal` | 自訂信號 |
| `QtCore` | `QTimer` | 定時器 |
| `QtCore` | `QThread` | 多執行緒 |
| `QtGui` | `QFont` | 字型 |
| `QtGui` | `QPixmap` | 圖片 |

## 打包指令

```bash
# PyInstaller — 單檔 exe（不帶命令列視窗）
pyinstaller --onefile --windowed --icon=app.ico main.py

# Nuitka — 編譯為原生 exe
nuitka --standalone --windows-console-mode=disable --output-dir=dist main.py

# 加入額外資料檔案
pyinstaller --add-data "assets;assets" --onefile main.py
```
