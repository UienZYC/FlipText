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
  Co-authored with LLMs
</p>

## LLM Settings
FlipText now supports an optional Python-backed LLM translation engine in addition to the original Edge-based translation flow.

Users no longer need to maintain provider keys and model selections in a repo-side INI file. Instead:

- provider, key, and model settings are managed through the `Settings` window from the tray menu
- configuration is stored in a user-local config file under your Windows roaming profile
- the tray menu lets you switch `Edge` / `LLM` and quickly switch active LLM models
- if the selected LLM configuration fails, FlipText automatically falls back to the original Edge translation

The LLM path keeps AutoHotkey for:

- hotkey capture
- popup UI
- `Tab` replacement/insert
- Edge fallback

Python handles:

- provider/model configuration
- API calls
- per-model timeout settings
- customizable system prompts and user prompt templates
- response parsing

One-time local setup:

```powershell
uv sync
```

After that, run `FlipText.ahk`, open `Settings` from the tray menu, add a provider, paste the API key, add one or more models, and set the active model.

Each LLM model can now customize both parts of the conversation sent to the API:

- `System prompt`: the instruction that defines the model's role and output rules
- `User prompt template`: the request body built for each translation

The user prompt template supports these placeholders:

- `{source_lang}`
- `{target_lang}`
- `{text}`

FlipText logs the fully composed system and user prompts for each LLM request to `FlipText.log`, which makes it easier to inspect how each conversation is assembled.

## Prompt Presets

FlipText now supports non-translation prompt presets for the active LLM model.

- Press `F1`, then `1` to keep using the original translation action
- Press `F1`, then another configured shortcut such as `2` or `q` to run a saved prompt preset
- Prompt presets are managed in `Settings`
- Each preset stores a name, a single-character shortcut, and a system prompt
- The selected text is sent as the user message for preset runs
