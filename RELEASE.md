# FlipText 发布指南

这份文档面向维护者，记录 Windows 版本的发布打包流程。普通用户应从 GitHub Release 下载 zip，解压后直接运行 `FlipText.exe`，不需要安装 Python、uv 或 AutoHotkey。

## 目标发布包

推荐的 GitHub Release asset 名称：

```text
FlipText-v1.1.1-win-x64.zip
```

推荐的 zip 内部结构：

```text
FlipText-v1.1.1/
  FlipText.exe
  helpers/
    FlipTextHelper.exe
    _internal/
      ...
  README.md
  LICENSE
```

发布包内部建议使用 `FlipText.exe` 作为主程序文件名。版本号放在 zip 文件名、Git tag 和 GitHub Release 标题中统一管理。

## 不应打入发布包的内容

不要包含：

- `.git/`
- `.venv/`
- `.uv-cache/`
- `__pycache__/`
- `.vscode/`
- `build/`
- `dist/`
- `testground/`
- `FlipText.log`
- `*.pyc`
- 用户配置文件
- API Key
- 中间生成的 `.spec` 文件

生成的 exe 和 zip 应作为 GitHub Release assets 上传，不应提交到 Git 仓库。

## 构建 Python Helper

`FlipTextHelper.exe` 是编译版 AutoHotkey 主程序在发布模式下调用的 Python 辅助程序。它封装了：

- `settings`：打开设置窗口
- `config ...`：转发到 `config_cli.py`
- `translate ...`：转发到 `llm_translate.py`

建议使用 PyInstaller onedir 方式构建：

```powershell
uv run pyinstaller --noconfirm --clean --onedir --name FlipTextHelper --console fliptext_helper.py
```

构建完成后复制：

```text
dist\FlipTextHelper\FlipTextHelper.exe
dist\FlipTextHelper\_internal\
```

到发布目录：

```text
release\FlipText-v1.1.1\helpers\FlipTextHelper.exe
release\FlipText-v1.1.1\helpers\_internal\
```

## 构建 AutoHotkey 主程序

使用 Ahk2Exe 编译 `FlipText.ahk`。请选择 AutoHotkey v2 x64 base binary，并嵌入 `icon.ico`。

命令形态示例：

```powershell
Ahk2Exe.exe /in FlipText.ahk /out release\FlipText-v1.1.1\FlipText.exe /base "<path-to-AutoHotkey64.exe>" /icon icon.ico
```

编译后的主程序会优先查找：

```text
helpers\FlipTextHelper.exe
```

如果该 helper 不存在，则回退到开发模式，尝试使用 `.venv\Scripts\python.exe` 和源码中的 `.py` 文件。

## 组装发布目录

创建目录：

```text
release\FlipText-v1.1.1\
```

复制以下内容：

- `FlipText.exe`
- `helpers\FlipTextHelper.exe`
- `helpers\_internal\`
- `README.md`
- `LICENSE`

然后将 `FlipText-v1.1.1` 目录压缩为：

```text
FlipText-v1.1.1-win-x64.zip
```

## 发布前检查清单

上传 GitHub Release 前，请确认：

- Git tag 和 Release 标题使用同一个版本号，例如 `v1.1.1`。
- zip 中不包含 `.venv`、`.uv-cache`、日志、用户配置、API Key、`build`、`dist` 或 `.spec` 文件。
- 在包含空格的路径中测试。
- 如有条件，在包含中文或其他非 ASCII 字符的路径中测试。
- 在未安装 Python、uv、AutoHotkey 的干净 Windows 环境中测试。
- 可以启动 `FlipText.exe`。
- 可以打开 `Settings`。
- `Reload Config` 可用。
- 配置写入 `%APPDATA%\FlipText\config.json`。
- 日志写入 `%APPDATA%\FlipText\FlipText.log`。
- `F1` 可以显示快捷键映射。
- `F1+1` 可以执行 Edge 翻译。
- 配置错误的 LLM 行为时，只显示 LLM 错误，不自动回退 Edge。
- 配置可用的 LLM 行为时，LLM 翻译正常。
- `Tab` 替换和插入行为正常。
- `Esc` 可以关闭弹窗。
- 退出并重新启动后，配置仍然持久化。

## GitHub Release Notes 建议

Hotfix 版本的说明保持简洁、具体即可。例如：

```text
FlipText v1.1.1

- Added release-mode Python helper support.
- Kept source-run development mode through .venv.
- Moved logs to %APPDATA%\FlipText\FlipText.log.
- Fixed Settings dirty-state tracking.
- Clarified that LLM failures do not automatically fall back to Edge.
```
