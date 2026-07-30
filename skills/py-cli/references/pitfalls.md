# py-cli — 常見陷阱與解法

## 陷阱 1：Typer 忘記加 `typer.Argument()`，變成 Option

**症狀**：參數本應是位置引數，卻變成 `--name` 選項。

```python
# ❌ 有預設值的參數自動變成 Option
@app.command()
def greet(name: str = "World") -> None:  # name 變成 --name
    ...

# ✅ 明確標記為 Argument
@app.command()
def greet(name: str = typer.Argument("World", help="名字")) -> None:
    ...
```

**原因**：Typer 遵循 Click 規則 — 有預設值的參數預設是 Option，無預設值的才是 Argument。

---

## 陷阱 2：Click/Typer 的 `--flag` 布林行為

**症狀**：`--verbose` 無法用 `--no-verbose` 關閉。

```python
# ❌ Click 風格 — 只有 --verbose，沒有 --no-verbose
@click.option("--verbose", is_flag=True)

# ✅ Click 顯式雙旗標
@click.option("--verbose/--no-verbose", default=False)

# ✅ Typer 自動處理（bool 型別自動產生 --no-xxx）
@app.command()
def cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    ...
# 自動生成 --verbose / --no-verbose
```

---

## 陷阱 3：Rich Console 寫到 stderr

**症狀**：彩色輸出和資料混在 stdout，pipe 時破壞下游工具。

```python
# ❌ 所有輸出都到 stdout
console = Console()
console.print("[red]Error![/red]")  # 顏色 escape 碼汙染 stdout
print(json.dumps(data))              # 資料也在 stdout

# ✅ 分離：資料 → stdout，訊息 → stderr
import sys

err_console = Console(stderr=True)   # 訊息/進度條到 stderr
err_console.print("[red]Error![/red]")

sys.stdout.write(json.dumps(data))   # 純資料到 stdout
```

**原則**：CLI 工具的「結果」用 stdout，「狀態/錯誤」用 stderr。這樣 `mycli | jq` 才能正常運作。

---

## 陷阱 4：忘記處理 `KeyboardInterrupt`

**症狀**：使用者按 Ctrl+C，CLI 印出一大堆 traceback。

```python
# ❌ 未處理 — 顯示完整 traceback
if __name__ == "__main__":
    app()

# ✅ 捕獲 KeyboardInterrupt
if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        print("\n中斷", file=sys.stderr)
        sys.exit(130)  # 130 = 128 + SIGINT(2)
```

**補充**：也可以用 `typer.Exit(code=130)` 或 Click 的 `@cli.command()`（Click 預設會處理）。

---

## 陷阱 5：Path 參數沒有驗證

**症狀**：使用者輸入不存在的路徑，到了業務邏輯才報 `FileNotFoundError`。

```python
# ❌ 延遲報錯 — 使用者不知道哪裡出錯
@app.command()
def process(input_file: str) -> None:
    with open(input_file) as f:  # FileNotFoundError
        ...

# ✅ 在參數層級就驗證
from pathlib import Path

@app.command()
def process(
    input_file: Path = typer.Argument(
        ..., exists=True, readable=True, help="輸入檔案",
    ),
    output_dir: Path = typer.Option(
        ".", file_okay=False, dir_okay=True, help="輸出目錄",
    ),
) -> None:
    ...  # 到這裡時，路徑一定存在且可讀
```

---

## 陷阱 6：子命令名稱衝突

**症狀**：子命令名稱和 Python 關鍵字或內建函式同名（`list`, `import`）。

```python
# ❌ 函式名 list 覆蓋了 Python 內建
@app.command()
def list() -> None:  # 覆蓋了 builtins.list!
    ...

# ✅ 用 name 參數指定 CLI 名稱
@app.command(name="list")
def list_items() -> None:
    ...

@app.command(name="import")
def import_data() -> None:
    ...
```

---

## 陷阱 7：Textual CSS 不生效

**症狀**：在 Textual App 中設定 CSS 但元件外觀不變。

```python
# ❌ CSS 選擇器錯誤 — class name 不等於 widget id
class MyApp(App):
    CSS = """
    .my-widget { color: red; }  /* 沒效果 */
    """
    def compose(self):
        yield Static("hello", id="my-widget")

# ✅ 用 # 選擇 id，用 . 選擇 class
class MyApp(App):
    CSS = """
    #my-widget { color: red; }      /* id 選擇器用 # */
    .highlight { background: blue; }  /* class 選擇器用 . */
    Static { padding: 1; }            /* 型別選擇器 */
    """
    def compose(self):
        yield Static("hello", id="my-widget", classes="highlight")
```

**注意**：Textual 的 CSS 是 TCSS（Textual CSS），不是瀏覽器 CSS。只支援部分屬性，參考 [Textual CSS Reference](https://textual.textualize.io/css_types/)。

---

## 陷阱 8：CLI 測試遺漏退出碼

**症狀**：只驗證輸出文字，忽略退出碼。上線後錯誤情境回傳 exit 0。

```python
# ❌ 只檢查輸出
def test_bad():
    result = runner.invoke(app, ["bad-input"])
    assert "error" in result.output.lower()
    # 忘記檢查 exit_code → CLI 回傳 0 但有錯誤訊息

# ✅ 一定要檢查退出碼
def test_error_case():
    result = runner.invoke(app, ["bad-input"])
    assert result.exit_code != 0                # 必須非零
    assert "error" in result.output.lower()

def test_success_case():
    result = runner.invoke(app, ["good-input"])
    assert result.exit_code == 0                # 必須為零
    assert "success" in result.output.lower()
```

**建議退出碼慣例**：

| 退出碼 | 意義 |
|--------|------|
| 0 | 成功 |
| 1 | 一般錯誤 |
| 2 | 參數錯誤 |
| 130 | 使用者中斷（Ctrl+C） |
