# py-cli — 完整範例

## 範例 1：完整 CRUD CLI 工具

```python
"""
任務管理 CLI — Typer + Rich + JSON 檔案儲存
展示完整的子命令、表格輸出、確認提示
"""
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="📋 任務管理工具")
console = Console()
DATA_FILE = Path("tasks.json")

@dataclass
class Task:
    id: int
    title: str
    done: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

def _load_tasks() -> list[dict]:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return []

def _save_tasks(tasks: list[dict]) -> None:
    DATA_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

@app.command()
def add(title: str = typer.Argument(help="任務標題")) -> None:
    """新增任務"""
    tasks = _load_tasks()
    new_id = max((t["id"] for t in tasks), default=0) + 1
    task = Task(id=new_id, title=title)
    tasks.append(asdict(task))
    _save_tasks(tasks)
    console.print(f"[green]✅ 新增任務 #{new_id}: {title}[/green]")

@app.command(name="list")
def list_tasks(
    all_tasks: bool = typer.Option(False, "--all", "-a", help="顯示已完成的任務"),
) -> None:
    """列出任務"""
    tasks = _load_tasks()
    if not all_tasks:
        tasks = [t for t in tasks if not t["done"]]

    if not tasks:
        console.print("[yellow]沒有任務[/yellow]")
        return

    table = Table(title="任務列表")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("狀態", justify="center")
    table.add_column("標題", style="white")
    table.add_column("建立時間", style="dim")

    for t in tasks:
        status = "✅" if t["done"] else "⬜"
        table.add_row(str(t["id"]), status, t["title"], t["created_at"][:10])
    console.print(table)

@app.command()
def done(task_id: int = typer.Argument(help="任務 ID")) -> None:
    """標記任務完成"""
    tasks = _load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            _save_tasks(tasks)
            console.print(f"[green]✅ 任務 #{task_id} 已完成[/green]")
            return
    console.print(f"[red]找不到任務 #{task_id}[/red]")
    raise typer.Exit(code=1)

@app.command()
def remove(
    task_id: int = typer.Argument(help="任務 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="跳過確認"),
) -> None:
    """刪除任務"""
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        console.print(f"[red]找不到任務 #{task_id}[/red]")
        raise typer.Exit(code=1)

    if not force:
        confirmed = typer.confirm(f"確定要刪除「{task['title']}」？")
        if not confirmed:
            raise typer.Abort()

    new_tasks = [t for t in tasks if t["id"] != task_id]
    _save_tasks(new_tasks)
    console.print(f"[red]🗑️  已刪除任務 #{task_id}[/red]")

if __name__ == "__main__":
    app()
```

---

## 範例 2：Rich 進度條 + 並行處理

```python
"""
檔案處理器 — Rich Progress + ThreadPoolExecutor
展示進度條、併發下載、錯誤處理
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time
import random

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

console = Console()

def download_file(url: str) -> dict:
    """模擬檔案下載"""
    time.sleep(random.uniform(0.5, 2.0))
    if random.random() < 0.1:  # 10% 失敗率
        raise ConnectionError(f"下載失敗: {url}")
    return {"url": url, "size": random.randint(1000, 50000)}

def batch_download(urls: list[str], max_workers: int = 4) -> None:
    """帶進度條的批量下載"""
    results: list[dict] = []
    errors: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        console=console,
    ) as progress:
        task = progress.add_task("下載中", total=len(urls))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(download_file, url): url for url in urls}

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append(f"{url}: {e}")
                finally:
                    progress.advance(task)

    console.print(f"\n[green]成功: {len(results)}[/green]  [red]失敗: {len(errors)}[/red]")
    for err in errors:
        console.print(f"  [red]✗[/red] {err}")

if __name__ == "__main__":
    urls = [f"https://example.com/file-{i}.zip" for i in range(20)]
    batch_download(urls)
```

---

## 範例 3：Click 裝飾器風格 CLI

```python
"""
Click 風格 CLI — 適合需要更細粒度控制的場景
展示 group, pass_context, custom type
"""
import click
from pathlib import Path

class AliasedGroup(click.Group):
    """支援命令簡寫（如 st → status）"""
    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        # 嘗試前綴匹配
        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
        if len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        return None

@click.group(cls=AliasedGroup)
@click.option("--debug/--no-debug", default=False, help="除錯模式")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """檔案工具 CLI"""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug

@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--pattern", "-p", default="*", help="檔名 glob pattern")
@click.pass_context
def search(ctx: click.Context, path: Path, pattern: str) -> None:
    """搜尋檔案"""
    if ctx.obj["debug"]:
        click.echo(f"Debug: 搜尋 {path} / {pattern}")

    files = sorted(path.rglob(pattern))
    for f in files:
        size = f.stat().st_size
        click.echo(f"  {f.relative_to(path)}  ({size:,} bytes)")
    click.echo(f"\n共找到 {len(files)} 個檔案")

@cli.command()
@click.argument("src", type=click.Path(exists=True, path_type=Path))
@click.argument("dst", type=click.Path(path_type=Path))
@click.option("--dry-run", is_flag=True, help="模擬執行")
@click.confirmation_option(prompt="確定要複製？")
def copy(src: Path, dst: Path, dry_run: bool) -> None:
    """複製檔案或目錄"""
    action = "[模擬] " if dry_run else ""
    click.echo(f"{action}複製 {src} → {dst}")

if __name__ == "__main__":
    cli()
```

---

## 範例 4：Textual TUI Dashboard

```python
"""
系統監控 TUI — Textual App
展示即時更新、鍵盤綁定、反應式 UI
"""
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, ProgressBar, Label
from textual.reactive import reactive
from textual.timer import Timer
import random

class MetricWidget(Static):
    """單一指標顯示元件"""
    value: reactive[float] = reactive(0.0)

    def __init__(self, label: str, unit: str = "%") -> None:
        super().__init__()
        self._label = label
        self._unit = unit

    def render(self) -> str:
        color = "green" if self.value < 70 else "yellow" if self.value < 90 else "red"
        return f"[bold]{self._label}[/bold]\n[{color}]{self.value:.1f}{self._unit}[/{color}]"

class MonitorApp(App):
    """系統監控儀表板"""
    CSS = """
    Horizontal { height: 5; }
    MetricWidget { width: 1fr; border: solid green; padding: 0 1; }
    """
    BINDINGS = [
        ("q", "quit", "離開"),
        ("p", "toggle_pause", "暫停/恢復"),
    ]

    paused: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield MetricWidget("CPU", "%")
            yield MetricWidget("RAM", "%")
            yield MetricWidget("Disk", "%")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self._update_metrics)

    def _update_metrics(self) -> None:
        if self.paused:
            return
        widgets = self.query(MetricWidget)
        for widget in widgets:
            widget.value = min(100.0, max(0.0, widget.value + random.uniform(-5, 5)))

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused

if __name__ == "__main__":
    MonitorApp().run()
```

---

## 範例 5：CLI 測試（typer.testing）

```python
"""
CLI 測試 — 使用 CliRunner 進行自動化測試
展示指令測試、退出碼檢查、輸出驗證
"""
import typer
from typer.testing import CliRunner

# --- 被測 CLI ---
app = typer.Typer()

@app.command()
def greet(name: str, formal: bool = typer.Option(False, "--formal")) -> None:
    if formal:
        typer.echo(f"Good day, {name}.")
    else:
        typer.echo(f"Hey {name}!")

@app.command()
def divide(a: float, b: float) -> None:
    if b == 0:
        typer.echo("Error: 除數不能為零", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"{a / b:.2f}")

# --- 測試 ---
runner = CliRunner()

def test_greet_default() -> None:
    result = runner.invoke(app, ["greet", "Alice"])
    assert result.exit_code == 0
    assert "Hey Alice!" in result.output

def test_greet_formal() -> None:
    result = runner.invoke(app, ["greet", "Alice", "--formal"])
    assert result.exit_code == 0
    assert "Good day, Alice." in result.output

def test_divide_success() -> None:
    result = runner.invoke(app, ["divide", "10", "3"])
    assert result.exit_code == 0
    assert "3.33" in result.output

def test_divide_by_zero() -> None:
    result = runner.invoke(app, ["divide", "10", "0"])
    assert result.exit_code == 1

if __name__ == "__main__":
    test_greet_default()
    test_greet_formal()
    test_divide_success()
    test_divide_by_zero()
    print("✅ 所有測試通過")
```
