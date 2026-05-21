<p align="center">
  <img src="https://github.com/UienZYC/FlipText/blob/main/icon.ico?raw=true" alt="FlipText Logo" width="128" height="128">
</p>

<h1 align="center">FlipText</h1>
<p align="center">
  <strong>Flip your text, flip the language.</strong><br>
  极简、优雅的输入框内“原地”中英互译与替换工具
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v1.0.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6.svg" alt="Platform">
  <img src="https://img.shields.io/badge/built%20with-AutoHotkey_v2-334455.svg" alt="Built with AHK">
  <img src="https://img.shields.io/badge/AI-Assisted-purple.svg" alt="AI Assisted">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
</p>

## 简介
**FlipText** 是一个为提高输入日常英语效率而生的翻译工具，不同于传统的划词翻译软件——它侧重于按下`Tab`时的单行文本译文替换，省去了复制粘贴的过程，让跨语言交流和写作更流畅。

在任何输入框中（代码编辑器、聊天窗口、文档、网页内输入框等），打字后，`F1`将光标所在行进行中英互译，`Tab`替换或插入译文

适用于大多数支持 `Ctrl+C` / `Ctrl+V` 的场景

## 功能
**选区翻译**：`F1`优先翻译鼠标选中的文本。

**整行翻译**：若无选区，自动识别光标所在行并翻译（无需手动全选）。

**原地替换**：在翻译弹窗出现时，按下 `Tab` 键，译文会自动**替换**掉原来的选区或整行。

**随处插入**：翻译后，您可以点击屏幕任何其他位置，或使用箭头按键移动光标，再按 `Tab`，译文将**粘贴**到新光标处。

**安静交互**：翻译弹窗跟随当前鼠标位置，轻量UI，不抢占用焦点，中英互译，`Esc`关闭弹窗。

**免费**：基于 Microsoft Edge 内部翻译接口，公平使用，无需配置 Key，仅供个人学习与合理使用。


## 快速上手
[Releases 页面](https://github.com/UienZYC/FlipText/releases)下载最新版本zip压缩包解压到本地

双击exe文件运行后，可在任务栏托盘区查看到图标

按`F1`优先对鼠标选中文本进行中英互译，若无选中，则自动选取光标所在行，并进行翻译

译文弹窗显示在鼠标所在位置

查看翻译后，按`Tab`，自动将选区替换为译文，若无选中，则将光标所在当前行替换为译文。

查看翻译后，可移动光标至其他任意可输入文本区域，按`Tab`，将译文黏贴到光标处。

`Esc`关闭弹窗

任务栏图标右键Exit退出

## 注意
本软件由自动化脚本语言 **AutoHotkey (v2)** 编写。由于 AHK 的工作原理涉及键盘监听（为了响应热键）和模拟按键（为了自动复制粘贴），**可能会被部分杀毒软件误报为病毒**。您可以下载 `.ahk` 源码自行审查或编译。

**重要文件操作**：处理 Excel 表格或极其重要的文档时，建议先小范围测试，以免自动替换功能误删内容（虽然可以用 `Ctrl+Z` 撤销）。

**兼容性**：`Ctrl+C` `Ctrl+V` `Home` `End`任一无法生效的区域无法使用本软件。


<p align="left">
  由 LLM 协作完成
</p>

## 当前实现说明

FlipText 是一个基于 AutoHotkey v2 的 Windows 文本翻译辅助工具。AutoHotkey 负责全局快捷键、文本捕获、弹窗展示，以及按 `Tab` 后的替换或插入行为；Python 则作为本地辅助层，负责配置管理、设置窗口，以及可选的 OpenAI 兼容 LLM 请求。

当前代码支持两类翻译行为：

- `Edge Translate`：AutoHotkey 直接调用 Edge/Microsoft Translator 相关接口。
- `LLM prompt`：AutoHotkey 调用 `llm_translate.py`，将选中的文本发送给已配置的 OpenAI 兼容服务商和提示词。

LLM 翻译失败时不会自动回退到 Edge 翻译。如果 LLM 请求失败，FlipText 会显示错误弹窗，并将详细信息写入 `%APPDATA%\FlipText\FlipText.log`。

## 普通用户：下载和使用

请从 GitHub Release 下载发布包，例如：

```text
FlipText-v1.1.1-win-x64.zip
```

解压后运行其中的 `FlipText.exe` 即可。发布包内会包含 Python 辅助程序：

```text
FlipText.exe
helpers/
  FlipTextHelper.exe
  _internal/
README.md
LICENSE
```

普通用户不需要安装 Python、uv 或 AutoHotkey。建议将发布包解压到用户目录下，例如桌面、下载目录或其他自己有写入权限的位置。

## 开发者：源码运行

源码运行要求：

- Windows
- AutoHotkey v2
- Python 3.11 或更高版本
- `uv`

在项目目录中执行一次以下命令，安装 Python 辅助组件依赖：

```powershell
uv sync
```

然后运行 AutoHotkey 脚本：

```powershell
FlipText.ahk
```

源码运行时，脚本会查找 `.venv\Scripts\python.exe` 和 `.venv\Scripts\pythonw.exe` 作为 Python 运行环境；该环境由 `uv sync` 创建。

开发者如需构建 GitHub Release 发布包，请参考 [RELEASE.md](RELEASE.md)。

## 运行时入口

发布版运行 `FlipText.exe` 时，主程序会优先调用旁置的：

```text
helpers\FlipTextHelper.exe
```

如果 helper 不存在，则回退到源码开发模式，尝试调用 `.venv\Scripts\python.exe` 加仓库中的 Python 脚本。

当前托盘菜单提供：

- `Settings`：打开 Tkinter 设置窗口。
- `Reload Config`：重新加载用户配置，并重建快捷键绑定。

当前没有用于直接切换 Edge/LLM 模式或切换模型的托盘菜单项。模型选择和快捷键绑定需要在 `Settings` 中管理。

## 默认快捷键

默认配置会创建以下绑定：

- `F1`：显示当前快捷键映射列表。
- `F1+1`：执行内置的 Edge 翻译行为。

更多快捷键可以在设置窗口的 `Behaviors` 页面中配置。一个快捷键绑定对应一个行为。

翻译结果出现后：

- 按 `Tab` 可替换原选区或当前行文本；如果已经移动到其他输入位置，则会在当前光标处插入译文。
- 按 `Esc` 可关闭弹窗。

## 设置窗口

设置窗口分为三个页面：

- `Models`：配置服务商、Base URL、API Key、模型、启用状态，以及每个模型的超时时间。
- `Prompts`：配置可复用提示词，包括 system prompt 和 user prompt template。
- `Behaviors`：配置具体行为，例如 `Edge Translate`、`Show Shortcuts`，或某个 LLM 模型与提示词的组合，并为这些行为绑定快捷键。

LLM 的 user prompt template 支持以下变量：

- `{text}`
- `{source_lang}`
- `{target_lang}`

语言方向由代码按以下规则推导：

- 如果选中文本包含中文字符，则 `source_lang=zh`，`target_lang=en`。
- 否则为 `source_lang=en`，`target_lang=zh`。

## 配置、日志和临时文件

FlipText 不会把用户配置、API Key 或运行日志写入发布包目录。当前代码会在以下非程序所在目录写入文件。

用户配置保存在 Windows 漫游配置目录下，通常为：

```text
%APPDATA%\FlipText\config.json
```

这里会保存 Settings 中配置的 provider、Base URL、API Key、模型、提示词、行为和快捷键绑定。

运行日志写入：

```text
%APPDATA%\FlipText\FlipText.log
```

日志可能包含 LLM prompt 组装内容、LLM 错误、行为错误、完整提示词和被选中的原文内容。

运行过程中的临时中间文件写入：

```text
%TEMP%\FlipText\
```

当前会使用的临时文件包括：

- `llm_input.txt`
- `llm_output.json`
- `config_summary.json`
- `config_summary.json.error.log`（仅在配置摘要命令失败时可能出现）

这些临时文件可能短暂包含被选中的待翻译文本或错误详情。

## 已知限制

- 当前版本仅支持 Windows。
- FlipText 依赖目标应用支持常见键盘和剪贴板操作，例如 `Ctrl+C`、`Ctrl+V`、`Home` 和 `End`。
- LLM 请求需要先配置服务商、API Key、模型、提示词和行为绑定。
- LLM 失败时只显示错误，不会自动通过 Edge 重试。
- Edge 翻译路径依赖外部 Microsoft/Edge 翻译接口。
- 当前仓库尚未包含自动化测试或可执行文件构建脚本。
