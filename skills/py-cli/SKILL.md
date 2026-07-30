---
name: py-cli
description: >
  Build and review robust Python command-line applications with argparse, Typer, Click, Rich, or Textual. Use for commands, subcommands, options, config precedence, environment variables, stdin/stdout/stderr contracts, exit codes, JSON output, progress, shell completion, non-interactive automation, atomic file operations, packaging entry points, and CLI testing across Windows, macOS, and Linux.
compatibility: Agent Skills-compatible. Framework APIs vary by version; inspect the lockfile and preserve existing command contracts before refactoring.
metadata:
  author: stevenke1981
  version: "2.0.0"
  last-reviewed: "2026-07-30"
---

# Python CLI 應用工程

## 目標與邊界

用此 skill 建立對人友善、對 script 穩定、可在 CI 非互動執行的命令列工具。CLI 是公開 API：command、option、exit code、stdout 格式與設定優先序都需要相容性管理。

若需求是桌面視窗，使用 `py-gui`；若只是 library 內部函式，不要為了展示而建立多餘 CLI。

## 執行流程

1. **定義命令契約**：command/subcommand、參數、option、stdin、stdout、stderr、exit code 與副作用。
2. **辨識使用者**：互動式人類、shell script、CI、排程、容器或遠端執行。
3. **選擇框架**：依複雜度、既有依賴、型別與 plugin 需求決定 argparse、Typer、Click 或 Textual。
4. **定義設定優先序**：CLI > environment > config file > defaults，並提供來源可觀測性。
5. **分離核心邏輯**：command function 只解析、呼叫 service、格式化結果與轉換錯誤。
6. **設計安全副作用**：dry-run、確認、atomic write、idempotency 與 path validation。
7. **支援自動化**：`--json`、`--no-input`、穩定 exit code、禁用顏色/動畫與可預測輸出。
8. **測試與打包**：CliRunner/subprocess、entry point、Windows 路徑與 shell completion。

## 框架選擇

| 需求 | 優先方案 |
|---|---|
| 零第三方依賴、標準庫工具 | `argparse` |
| 型別提示、快速開發、Rich 整合 | Typer |
| 大型成熟 CLI、plugin、細緻 context | Click |
| 終端機全螢幕互動 UI | Textual |
| 少數固定參數 | 不需要額外 framework |

不要在既有 Click/Typer 專案中無理由切換框架；command contract 的穩定性比框架偏好重要。

## CLI 輸出契約

### stdout

- 只輸出主要結果或可供 pipe 的資料。
- `--json` 輸出單一有效 JSON document 或明確 JSON Lines。
- machine-readable 模式不得混入 spinner、banner、warning 或 debug log。

### stderr

- 診斷、warning、progress 與錯誤訊息。
- 敏感參數必須遮蔽。
- 非 TTY 時停用動態 repaint 與 ANSI color，除非使用者明確要求。

### exit code

建議穩定分類並寫入文件：

| Code | 意義 |
|---:|---|
| 0 | 成功 |
| 1 | 一般執行失敗 |
| 2 | 使用方式或驗證錯誤 |
| 3 | 找不到資源／設定 |
| 4 | 權限或認證失敗 |
| 5 | 暫時性外部服務失敗 |
| 130 | 使用者中斷（常見 shell 慣例） |

不要把所有失敗都轉成 0，也不要讓 stack trace 成為一般使用者唯一訊息。

## Typer 結構範例

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer


app = typer.Typer(no_args_is_help=True)


@dataclass(frozen=True, slots=True)
class AppContext:
    config_path: Path | None
    json_output: bool


@app.callback()
def main(
    ctx: typer.Context,
    config: Annotated[
        Path | None,
        typer.Option("--config", exists=True, dir_okay=False, readable=True),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    ctx.obj = AppContext(config_path=config, json_output=json_output)


@app.command()
def greet(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name to greet.")],
) -> None:
    settings = ctx.find_object(AppContext)
    if settings is None:
        raise RuntimeError("application context was not initialized")

    payload = {"message": f"Hello, {name}!"}
    if settings.json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False))
    else:
        typer.echo(payload["message"])


if __name__ == "__main__":
    app()
```

避免用 module-level mutable dict 保存 command 狀態。context、service 或 immutable settings 應由 callback/組合根建立並注入。

## argparse 結構

對小型零依賴工具：

```python
import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="example-tool")
    parser.add_argument("path")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run(path=args.path, json_output=args.json_output)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

實際程式需 import `sys`；將 `argv` 注入可讓 unit test 不必 patch 全域 `sys.argv`。

## 設定優先序

固定規則：

```text
command-line option
  > environment variable
  > project/user config file
  > application default
```

- 每個 setting 只在一個地方 resolve。
- `--show-config` 可顯示非敏感 effective settings 與來源。
- config path 使用 `pathlib` 與 platform-appropriate user config directory。
- 不自動讀取目前目錄中的未知設定檔，除非文件明確說明，避免不可信專案影響執行。
- API key 不寫入一般明文 config；優先 environment、OS credential store 或 secret manager。

## 非互動與 CI

提供：

- `--no-input` 或明確 `--yes`
- `--json` / `--format`
- `--quiet` / `--verbose`
- timeout、retry 與 concurrency options
- `--dry-run` 對寫入、刪除、部署、發信等副作用
- stable exit codes
- environment 變數對應

規則：

- stdin 不是 TTY 時不要突然 prompt。
- `--yes` 只能略過已文件化確認，不能放寬權限或 validation。
- CI 中 progress bar 不得汙染 machine output。
- secret 不可出現在 process title、shell history 或 command echo；必要時從 stdin/file descriptor/secret store 讀取。

## Path 與檔案操作

- 使用 `Path`，但不要假設路徑分隔符與大小寫規則。
- 接收 input path 時檢查 exists/type/readability。
- output 避免覆蓋，除非 `--force` 或明確策略。
- 寫檔使用同目錄 temporary file + flush/fsync（依需求）+ atomic replace。
- archive extraction 防 path traversal、symlink 與 decompression bomb。
- `-` 可作 stdin/stdout 時，清楚區分 text 與 binary mode。

## 錯誤處理

command boundary 將 domain error 映射為 CLI error：

```python
class UserFacingError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def render_failure(exc: UserFacingError, *, debug: bool) -> None:
    typer.echo(f"error: {exc}", err=True)
    if debug:
        raise exc
    raise typer.Exit(exc.exit_code)
```

- 預期錯誤顯示短訊息與修正方式。
- `--debug` 才顯示 traceback。
- 不捕捉 `BaseException`；保留 `KeyboardInterrupt`/`SystemExit` 語意。
- 使用者中斷時清理資源並回傳適當 exit code。
- partial success 要有明確 summary 與非零/零政策。

## Progress 與 Rich

- 只有 TTY 且非 JSON/quiet 模式才顯示動態 progress。
- progress total 不確定時使用 spinner，但仍顯示目前階段。
- log 與 progress 避免互相覆蓋。
- 支援 `NO_COLOR` 或 framework 等效設定。
- screen reader/redirect 情境提供純文字模式。

## Plugin 與 Subcommand

- 大型 CLI 可用 entry points 發現 plugin。
- plugin API 需版本化、隔離 import error 並可列出停用原因。
- 不在 `--help` 時載入大型模型、網路 client 或所有 plugin 副作用。
- subcommand 名稱與 option 一旦發布即視為相容契約。
- deprecated option 提供 warning、替代方式與移除版本。

## 測試策略

### Typer/Click Runner

```python
from typer.testing import CliRunner


runner = CliRunner()


def test_greet_json() -> None:
    result = runner.invoke(app, ["--json", "greet", "Ada"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"message": "Hello, Ada!"}
```

測試還應涵蓋：

- `--help` 與 no-args behavior
- invalid argument 與 exit code
- stdout/stderr 分離
- JSON 可解析且無額外文字
- config precedence
- no-input / TTY 差異
- temp directory、atomic write 與 `--force`
- Ctrl-C、timeout 與 partial failure
- entry point 安裝後用 subprocess smoke test
- Windows quoting/path、macOS/Linux permission

## 打包與 Entry Point

```toml
[project.scripts]
example-tool = "example_tool.cli:app"
```

依框架確認 target 是 callable/app。建 wheel 後在乾淨 venv 測：

```bash
example-tool --help
example-tool --version
```

不要只用 `python -m package.cli` 測試而忽略安裝 entry point。

## 交付標準

- command、option、stdin/stdout/stderr 與 exit code 契約已文件化。
- 核心邏輯與 CLI framework 分離，可直接 unit test。
- 設定優先序固定，effective config 可檢查且不洩漏秘密。
- 非互動模式無 prompt、動畫或混雜 machine output。
- 副作用有 dry-run、確認、atomic write 與可回復策略。
- 錯誤映射穩定，一般模式不輸出無用 traceback。
- Windows、macOS、Linux 的 path/encoding/entry point 已測。
- wheel 安裝後的實際 command 已 smoke test。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)

## 版本相容性

| 環境 | 建議 |
|---|---|
| Python 3.14 | 穩定維護基準 |
| Python 3.10–3.13 | 支援；依專案最低版本調整 typing 語法 |
| Typer/Click/Rich | 依 lockfile 與官方文件驗證 context、testing 與 output API |
| Windows/macOS/Linux | 每個平台執行 entry point smoke test |
| Preview Python | 只作 compatibility job，不作唯一發布環境 |
