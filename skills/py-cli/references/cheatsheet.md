# py-cli — 速查表

## Typer CLI 速查

### 基本結構

```python
import typer
app = typer.Typer(help="說明文字")

@app.command()
def cmd(
    arg: str = typer.Argument(help="位置參數"),
    opt: str = typer.Option("default", "--opt", "-o", help="選項"),
    flag: bool = typer.Option(False, "--flag", "-f", help="旗標"),
) -> None:
    """命令說明（顯示在 --help）"""
    typer.echo(f"{arg} {opt} {flag}")

if __name__ == "__main__":
    app()
```

### Argument / Option 常用參數

| 參數 | 用途 | 範例 |
|------|------|------|
| `help` | 說明文字 | `help="輸入檔案"` |
| `default` | 預設值 | 第一個位置參數 |
| `exists` | Path 必須存在 | `exists=True`（Path 參數） |
| `envvar` | 環境變數來源 | `envvar="API_KEY"` |
| `prompt` | 互動式輸入 | `prompt="你的名字"` |
| `hide_input` | 密碼模式 | `hide_input=True` |
| `callback` | 驗證回呼 | `callback=validate_port` |
| `is_eager` | 優先執行 | `is_eager=True`（版本號） |
| `min` / `max` | 數值範圍 | `min=1, max=65535` |

### 支援的型別

| Python Type | CLI 表現 | 範例 |
|-------------|----------|------|
| `str` | 字串 | `--name Alice` |
| `int` | 整數 | `--port 8080` |
| `float` | 浮點數 | `--rate 0.5` |
| `bool` | 旗標 | `--verbose / --no-verbose` |
| `Path` | 路徑（可驗證） | `--config ./config.toml` |
| `StrEnum` | 下拉選項 | `--format json` |
| `datetime` | 日期時間 | `--date 2024-01-01` |
| `UUID` | UUID | `--id abc-123` |
| `list[str]` | 多值 | `--tag foo --tag bar` |
| `Optional[str]` | 可選 | `--note "..."` |

### 子命令

```python
app = typer.Typer()
sub = typer.Typer(help="子命令群組")
app.add_typer(sub, name="db")

@sub.command()
def migrate(): ...

# CLI: myapp db migrate
```

### 全域選項（Callback）

```python
@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    state["verbose"] = verbose
```

### 退出碼

```python
raise typer.Exit(code=0)       # 正常退出
raise typer.Exit(code=1)       # 一般錯誤
raise typer.Abort()            # 使用者取消
```

---

## Click CLI 速查

### 基本結構

```python
import click

@click.group()
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx, debug):
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug

@cli.command()
@click.argument("name")
@click.option("--count", "-c", default=1, type=int)
def hello(name, count):
    for _ in range(count):
        click.echo(f"Hello {name}!")
```

### Click 常用裝飾器

| 裝飾器 | 用途 |
|--------|------|
| `@click.group()` | 命令群組 |
| `@cli.command()` | 子命令 |
| `@click.argument("name")` | 位置參數 |
| `@click.option("--opt")` | 選項 |
| `@click.pass_context` | 傳遞 context |
| `@click.confirmation_option()` | 確認提示 |
| `@click.version_option()` | 版本號 |
| `@click.help_option()` | 說明 |

---

## Rich 輸出速查

### Console 基本

```python
from rich.console import Console
console = Console()

console.print("[bold red]錯誤[/bold red] 訊息")
console.print("[green]✅ 成功[/green]")
console.log("帶時間戳的訊息")
console.print_json('{"key": "value"}')
```

### 常用 Markup 標籤

| 標籤 | 效果 |
|------|------|
| `[bold]` | 粗體 |
| `[italic]` | 斜體 |
| `[red]`, `[green]`, `[yellow]` | 前景色 |
| `[on red]` | 背景色 |
| `[link=URL]` | 超連結 |
| `[dim]` | 暗淡 |

### Table

```python
from rich.table import Table
table = Table(title="標題", show_lines=True)
table.add_column("欄位", style="cyan", justify="right")
table.add_row("值")
console.print(table)
```

### Progress

```python
from rich.progress import track, Progress

# 簡單版
for item in track(items, description="處理中..."):
    process(item)

# 進階版（多任務）
with Progress() as progress:
    task1 = progress.add_task("下載", total=100)
    task2 = progress.add_task("處理", total=50)
    progress.advance(task1)
```

### Panel / Tree

```python
from rich.panel import Panel
from rich.tree import Tree

console.print(Panel("內容", title="標題", border_style="blue"))

tree = Tree("root")
tree.add("child1").add("grandchild")
tree.add("child2")
console.print(tree)
```

---

## Textual TUI 速查

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Input, Static

class MyApp(App):
    CSS = """
    Screen { layout: vertical; }
    #main { height: 1fr; }
    """
    BINDINGS = [("q", "quit", "離開")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="輸入...")
        yield Static("內容", id="main")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#main", Static).update(event.value)
```

---

## pyproject.toml CLI 入口點

```toml
[project.scripts]
mycli = "mypackage.cli:app"          # Typer
mycli = "mypackage.cli:cli"          # Click

# 安裝後可直接執行：mycli --help
```

## 自動補全安裝

```bash
# Typer
typer --install-completion bash
typer --install-completion zsh
typer --install-completion fish
typer --install-completion powershell

# Click
eval "$(_MYCLI_COMPLETE=bash_source mycli)"  # bash
eval "$(_MYCLI_COMPLETE=zsh_source mycli)"   # zsh
```
