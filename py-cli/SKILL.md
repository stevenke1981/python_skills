---
name: py-cli
description: >
  Python CLI tool development with modern frameworks.
  Trigger when user mentions typer, click, rich, textual, argparse,
  command-line interface, CLI app, terminal UI, console output,
  progress bar, subcommands, argument parsing, shell completion.
  Also trigger when user asks about building terminal tools,
  interactive prompts, or TUI applications.
---

# Python CLI 工具開發

## Quick Start（30 秒上手）

```python
"""最小 Typer CLI — 一個檔案即可運行"""
import typer

app = typer.Typer(help="我的第一個 CLI 工具")

@app.command()
def hello(
    name: str = typer.Argument(help="你的名字"),
    greeting: str = typer.Option("你好", "--greeting", "-g", help="問候語"),
    loud: bool = typer.Option(False, "--loud", "-l", help="大聲模式"),
) -> None:
    """向某人打招呼"""
    message = f"{greeting}, {name}!"
    if loud:
        message = message.upper()
    typer.echo(message)

if __name__ == "__main__":
    app()
```

```bash
# 執行
python cli.py Alice --greeting Hi --loud
# HI, ALICE!

# 自動 --help
python cli.py --help
```

## 核心概念

### 1. Typer 型別驅動設計

Typer 透過 Python type hints 自動產生 CLI 介面、驗證、補全與說明文件。

```python
from pathlib import Path
from enum import StrEnum
import typer

class OutputFormat(StrEnum):
    JSON = "json"
    CSV = "csv"
    TABLE = "table"

app = typer.Typer()

@app.command()
def convert(
    input_file: Path = typer.Argument(..., exists=True, help="輸入檔案"),
    output: Path = typer.Option("output.json", help="輸出檔案"),
    fmt: OutputFormat = typer.Option(OutputFormat.JSON, help="輸出格式"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """轉換檔案格式"""
    if verbose:
        typer.echo(f"讀取 {input_file} → {fmt.value} → {output}")
```

### 2. 子命令與命令群組

```python
app = typer.Typer(help="專案管理工具")
db_app = typer.Typer(help="資料庫操作")
app.add_typer(db_app, name="db")

@app.command()
def init(name: str) -> None:
    """初始化專案"""
    typer.echo(f"初始化: {name}")

@db_app.command()
def migrate(revision: str = "head") -> None:
    """執行資料庫遷移"""
    typer.echo(f"遷移到: {revision}")

@db_app.command()
def seed() -> None:
    """填入種子資料"""
    typer.echo("填入種子資料...")

# CLI: mycli init myproject
# CLI: mycli db migrate --revision abc123
# CLI: mycli db seed
```

### 3. Rich Console 美化輸出

```python
from rich.console import Console
from rich.table import Table
from rich.progress import track
import time

console = Console()

def show_users(users: list[dict]) -> None:
    """用 Rich Table 顯示使用者列表"""
    table = Table(title="使用者列表", show_lines=True)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("名稱", style="green")
    table.add_column("信箱", style="magenta")
    table.add_column("狀態", justify="center")

    for user in users:
        status = "✅" if user["active"] else "❌"
        table.add_row(str(user["id"]), user["name"], user["email"], status)

    console.print(table)

def process_files(files: list[str]) -> None:
    """帶進度條的檔案處理"""
    for f in track(files, description="處理中..."):
        time.sleep(0.1)  # 模擬處理
    console.print("[bold green]全部完成！[/bold green]")
```

### 4. 互動式 Prompt

```python
import typer
from rich.prompt import Prompt, Confirm, IntPrompt

def setup_wizard() -> dict:
    """設定精靈 — 互動式收集設定"""
    name = Prompt.ask("專案名稱", default="my-project")
    port = IntPrompt.ask("伺服器埠號", default=8000)
    db_type = Prompt.ask(
        "資料庫類型",
        choices=["sqlite", "postgres", "mysql"],
        default="sqlite",
    )
    use_docker = Confirm.ask("是否使用 Docker？", default=True)

    return {"name": name, "port": port, "db": db_type, "docker": use_docker}
```

### 5. 錯誤處理與退出碼

```python
import typer
from rich.console import Console

console = Console(stderr=True)  # 錯誤輸出到 stderr

def safe_main(func):
    """CLI 錯誤處理包裝器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            console.print(f"[red]檔案不存在:[/red] {e}")
            raise typer.Exit(code=1)
        except PermissionError as e:
            console.print(f"[red]權限不足:[/red] {e}")
            raise typer.Exit(code=2)
        except KeyboardInterrupt:
            console.print("\n[yellow]使用者中斷[/yellow]")
            raise typer.Exit(code=130)
    return wrapper
```

## 實戰 Patterns

### Pattern 1：設定檔整合

**場景**：CLI 需要讀取設定檔（`~/.config/myapp/config.toml`）

```python
from pathlib import Path
from dataclasses import dataclass, field
import tomllib

APP_DIR = Path(typer.get_app_dir("myapp"))
CONFIG_PATH = APP_DIR / "config.toml"

@dataclass(frozen=True)
class AppConfig:
    api_url: str = "https://api.example.com"
    timeout: int = 30
    verbose: bool = False

def load_config() -> AppConfig:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
        return AppConfig(**{k: v for k, v in data.items() if k in AppConfig.__dataclass_fields__})
    return AppConfig()
```

### Pattern 2：Callback + Context 全域選項

**場景**：所有子命令共用 `--verbose`, `--config` 等全域選項。

```python
from typing import Optional
import typer

app = typer.Typer()
state = {"verbose": False}

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="詳細輸出"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="設定檔路徑"),
) -> None:
    """全域選項 — 在所有子命令之前執行"""
    state["verbose"] = verbose
    if config:
        state["config"] = load_config(config)

@app.command()
def deploy(env: str = "staging") -> None:
    if state["verbose"]:
        typer.echo(f"部署到 {env}（詳細模式）")
```

### Pattern 3：Textual TUI 互動介面

**場景**：需要完整的終端機 UI（類似 htop、lazygit）。

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable

class LogViewer(App):
    """簡單的日誌檢視器 TUI"""
    BINDINGS = [
        ("q", "quit", "離開"),
        ("r", "refresh", "重新載入"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("時間", "等級", "訊息")
        table.add_rows([
            ("10:01", "INFO", "伺服器啟動"),
            ("10:02", "WARN", "記憶體使用率 85%"),
            ("10:03", "ERROR", "連線逾時"),
        ])

if __name__ == "__main__":
    LogViewer().run()
```

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| **typer** | CLI 框架（型別驅動） | `pip install typer` | 基於 Click，自動補全 |
| **click** | CLI 框架（裝飾器風格） | `pip install click` | 生態系最大，Flask 同作者 |
| **rich** | 美化終端輸出 | `pip install rich` | Table, Progress, Panel, Tree |
| **textual** | 終端 UI 框架（TUI） | `pip install textual` | Rich 團隊出品，CSS-like 佈局 |
| **prompt_toolkit** | 進階互動式輸入 | `pip install prompt_toolkit` | 自動補全、語法高亮 |
| **questionary** | 互動式問卷 | `pip install questionary` | 確認、選單、多選 |
| **trogon** | 自動 TUI from CLI | `pip install trogon` | 為 Click/Typer app 生成 TUI |
| **shellingham** | 偵測當前 shell | `pip install shellingham` | Typer 自動補全所需 |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | Typer 0.15+, Rich 13+ |
| 3.12 | ✅ 完整支援 | |
| 3.11 | ✅ | StrEnum 首次加入 |
| 3.10 | ⚠️ 部分 | 無 StrEnum，用 `str, Enum` 替代 |
