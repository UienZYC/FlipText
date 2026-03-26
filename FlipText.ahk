#Requires AutoHotkey v2.0
Persistent

CoordMode "Mouse", "Screen"

global G_STATE := {
    Result: "",
    X: 0, Y: 0,
    IsMoved: false,
    Mode: "Select",
    Source: "",
    IsLoading: false,
    LoadingStartedAt: 0,
    LoadingTimeoutMs: 0,
    LastDurationMs: 0
}

global TransGui := ""
global TransSourceCtrl := ""
global TransBodyCtrl := ""
global LOG_PATH := A_ScriptDir "\FlipText.log"
global PROFILE_MENU := Menu()
global CONFIG_SUMMARY := ""
global CONFIG_LAST_MTIME := ""

SetupTrayMenu()

F1::
{
    global TransGui

    MouseGetPos(&mx, &my)
    G_STATE.X := mx + 15
    G_STATE.Y := my + 15

    originalClipboard := ClipboardAll()
    A_Clipboard := ""
    G_STATE.IsMoved := false

    targetText := ""
    try {
        Send "^c"
        if !ClipWait(0.15) {
            G_STATE.Mode := "Line"
            Send "{vkE8}"
            BlockInput(true)
            Send "{End}"
            Sleep 15
            Send "+{Home}"
            Sleep 50
            Send "^c"
            ClipWait(0.15)
            Send "{End}"
            BlockInput(false)
        } else {
            G_STATE.Mode := "Select"
        }
        targetText := Trim(A_Clipboard, " `t`r`n")
    }

    if (originalClipboard != "") {
        Sleep 100
        A_Clipboard := originalClipboard
    }

    if (targetText == "") {
        ToolTip "Failed to get text automatically, please select text first."
        SetTimer () => ToolTip(), -1000
        return
    }

    ClearPopup()
    action := WaitForPromptAction()
    if !IsObject(action)
        return

    StartPromptAction(targetText, action)
}

StartPromptAction(text, action) {
    summary := LoadConfigSummary()

    try {
        if (action.type = "translation")
            RunTranslationAction(text, summary)
        else if (action.type = "preset")
            RunPresetAction(text, summary, action)
        else
            throw Error("Unknown action type: " action.type)

        keys := ["~LButton","~Up","~Down","~Left","~Right","~BS","~Del","~Enter","~NumpadEnter"]
        for k in keys
            Hotkey k, MarkAsMoved, "On"

        Hotkey "Tab", DoReplace, "On"
        Hotkey "Esc", ClearUI, "On"

        UpdateTransGui(G_STATE.Result)
    } catch as err {
        LogDebug("Prompt action error. " err.Message)
        UpdateTransGui("Prompt Error")
        SetTimer(ClearUI, -2000)
    }
}

RunTranslationAction(text, summary) {
    if (summary.engine = "llm" && summary.active_profile_id != "") {
        StartLoadingState(summary.active_profile_label, summary.active_timeout_ms)

        try {
            result := PythonTranslate(text, summary.active_profile_id)
            StopLoadingState()
            G_STATE.Result := result["text"]
            G_STATE.Source := result["source"]
        } catch as err {
            StopLoadingState()
            LogDebug("LLM translation failed. " err.Message)
            G_STATE.Result := EdgeTranslate(text)
            fallbackLabel := (summary.active_profile_label != "") ? summary.active_profile_label : "LLM"
            G_STATE.Source := "Edge fallback: " fallbackLabel
        }
    } else {
        G_STATE.LastDurationMs := 0
        G_STATE.Result := EdgeTranslate(text)
        G_STATE.Source := "Edge"
    }
}

RunPresetAction(text, summary, action) {
    if (summary.active_profile_id = "")
        throw Error("No active LLM profile is configured for prompt presets.")

    StartLoadingState(action.name, summary.active_timeout_ms)
    try {
        result := PythonTranslate(text, summary.active_profile_id, action.id)
    } catch as err {
        StopLoadingState()
        throw err
    }
    StopLoadingState()
    G_STATE.Result := result["text"]
    G_STATE.Source := result["source"]
}

UpdateTransGui(newStr) {
    global TransGui, TransSourceCtrl, TransBodyCtrl, G_STATE

    ClearPopup()

    TransGui := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20")
    TransGui.BackColor := "FFFFE1"

    sourceLine := ""
    if (G_STATE.Source != "") {
        sourceLine := "Source: " G_STATE.Source
        if (!G_STATE.IsLoading && G_STATE.LastDurationMs > 0)
            sourceLine .= " | " FormatDuration(G_STATE.LastDurationMs)
    }

    if (sourceLine != "") {
        TransGui.SetFont("s9", "Microsoft YaHei")
        TransSourceCtrl := TransGui.Add("Text", "c666666", sourceLine)
    }

    TransGui.SetFont("s11 w700", "Microsoft YaHei")
    bodyOpts := (InStr(newStr, "`n") || StrLen(newStr) > 50) ? "c003366 w600 Wrap" : "c003366"
    TransBodyCtrl := TransGui.Add("Text", bodyOpts, newStr)

    TransGui.Show("x" G_STATE.X " y" G_STATE.Y " NoActivate AutoSize")
    WinSetTransparent(200, TransGui)
}

ShowLoadingGui() {
    global TransGui, TransSourceCtrl, TransBodyCtrl, G_STATE

    ClearPopup()

    TransGui := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20")
    TransGui.BackColor := "FFFFE1"

    TransGui.SetFont("s9", "Microsoft YaHei")
    TransSourceCtrl := TransGui.Add("Text", "c666666", "Source: " G_STATE.Source)

    TransGui.SetFont("s11 w700", "Microsoft YaHei")
    TransBodyCtrl := TransGui.Add("Text", "c003366 w360", "")

    UpdateLoadingGui()
    TransGui.Show("x" G_STATE.X " y" G_STATE.Y " NoActivate AutoSize")
    WinSetTransparent(200, TransGui)
}

ClearPopup() {
    global TransGui, TransSourceCtrl, TransBodyCtrl

    if (TransGui) {
        TransGui.Destroy()
        TransGui := ""
    }
    TransSourceCtrl := ""
    TransBodyCtrl := ""
}

DoReplace(*) {
    global G_STATE
    res := G_STATE.Result
    isLine := (G_STATE.Mode == "Line")
    moved := G_STATE.IsMoved

    ClearUI()

    if (res == "") {
        return
    }

    tempClip := ClipboardAll()
    A_Clipboard := ""
    A_Clipboard := res

    if !ClipWait(0.5) {
        A_Clipboard := tempClip
        return
    }

    oldKeyDelay := A_KeyDelay
    SetKeyDelay 20, 20

    if (isLine && !moved) {
        BlockInput(true)
        SendEvent "{End}+{Home}"
        Sleep 200
        SendEvent "^v"
        Sleep 300
        BlockInput(false)
    } else {
        SendEvent "^v"
        Sleep 300
    }

    SetKeyDelay oldKeyDelay
    A_Clipboard := tempClip
}

ClearUI(*) {
    global G_STATE
    StopLoadingState()
    ClearPopup()
    G_STATE.Source := ""
    G_STATE.LastDurationMs := 0

    keys := ["~LButton","~Up","~Down","~Left","~Right","~BS","~Del","~Enter","~NumpadEnter","Tab","Esc"]
    for k in keys
        try Hotkey k, "Off"
}

MarkAsMoved(*) => G_STATE.IsMoved := true

StartLoadingState(profileLabel, timeoutMs) {
    global G_STATE

    G_STATE.Source := "LLM: " profileLabel
    G_STATE.IsLoading := true
    G_STATE.LoadingStartedAt := A_TickCount
    G_STATE.LoadingTimeoutMs := timeoutMs
    G_STATE.LastDurationMs := 0
    ShowLoadingGui()
    SetTimer(UpdateLoadingGui, 250)
    Sleep 50
}

StopLoadingState() {
    global G_STATE

    if G_STATE.IsLoading
        G_STATE.LastDurationMs := A_TickCount - G_STATE.LoadingStartedAt

    G_STATE.IsLoading := false
    G_STATE.LoadingStartedAt := 0
    G_STATE.LoadingTimeoutMs := 0
    SetTimer(UpdateLoadingGui, 0)
}

UpdateLoadingGui() {
    global G_STATE, TransBodyCtrl

    if !G_STATE.IsLoading
        return

    elapsedMs := A_TickCount - G_STATE.LoadingStartedAt
    remainingMs := G_STATE.LoadingTimeoutMs - elapsedMs
    if (remainingMs < 0)
        remainingMs := 0

    text := "Running with LLM... " FormatSeconds(remainingMs) " left"
    if (elapsedMs > 0)
        text .= " | " FormatDuration(elapsedMs) " elapsed"

    if (TransBodyCtrl)
        TransBodyCtrl.Text := text
}

PythonTranslate(text, profileId, presetId := "") {
    tempDir := A_Temp "\FlipText"
    if !DirExist(tempDir)
        DirCreate(tempDir)

    inputPath := tempDir "\llm_input.txt"
    outputPath := tempDir "\llm_output.json"
    try FileDelete(inputPath)
    try FileDelete(outputPath)

    FileAppend(text, inputPath, "UTF-8")

    args := "--profile-id " QuoteArg(profileId)
        . (presetId != "" ? " --preset-id " QuoteArg(presetId) : "")
        . " --text-file " QuoteArg(inputPath)
        . " --result-file " QuoteArg(outputPath)
        . " --log-file " QuoteArg(LOG_PATH)
    exitCode := RunPythonWait("llm_translate.py", args)

    if !FileExist(outputPath)
        throw Error("Python translator did not produce output. Exit code " exitCode ".")

    result := JSON_Parse(FileRead(outputPath, "UTF-8"))
    if !result.ok
        throw Error(result.error)

    translated := result.text
    if (Trim(translated, " `t`r`n") = "")
        throw Error("Python translator returned empty text.")

    return Map("text", translated, "source", result.source)
}

SetupTrayMenu() {
    A_TrayMenu.Add()
    A_TrayMenu.Add("Settings", OpenSettings)
    A_TrayMenu.Add("Use Edge Translation", SetEngineEdge)
    A_TrayMenu.Add("Use LLM Translation", SetEngineLLM)
    A_TrayMenu.Add("LLM Models", PROFILE_MENU)
    A_TrayMenu.Add("Reload Config", ReloadConfigFromMenu)
    UpdateTrayChecks()
    SetTimer(WatchConfigChanges, 1000)
}

UpdateTrayChecks() {
    global CONFIG_SUMMARY, CONFIG_LAST_MTIME

    CONFIG_SUMMARY := LoadConfigSummary()
    try CONFIG_LAST_MTIME := FileGetTime(UserConfigPath(), "M")

    try A_TrayMenu.Uncheck("Use Edge Translation")
    try A_TrayMenu.Uncheck("Use LLM Translation")

    if (CONFIG_SUMMARY.engine = "llm")
        A_TrayMenu.Check("Use LLM Translation")
    else
        A_TrayMenu.Check("Use Edge Translation")

    RebuildProfileMenu(CONFIG_SUMMARY)
}

RebuildProfileMenu(summary) {
    global PROFILE_MENU

    try PROFILE_MENU.Delete()

    for _, profile in GetSummaryProfiles(summary) {
        label := profile.label
        if !profile.enabled
            label .= " [Disabled]"
        PROFILE_MENU.Add(label, SelectLLMProfile)
        if (profile.id = summary.active_profile_id)
            PROFILE_MENU.Check(label)
    }

    if (GetSummaryProfiles(summary).Length = 0)
        PROFILE_MENU.Add("(No models configured)", NoOpMenu)
}

NoOpMenu(*) {
}

SelectLLMProfile(itemName, *) {
    summary := CONFIG_SUMMARY
    for _, profile in GetSummaryProfiles(summary) {
        label := profile.label
        if !profile.enabled
            label .= " [Disabled]"
        if (label = itemName) {
            SetActiveProfile(profile.id)
            return
        }
    }
}

SetActiveProfile(profileId) {
    RunConfigCli("set-active-profile", "--profile-id " QuoteArg(profileId))
    UpdateTrayChecks()
    ToolTip "Active model updated"
    SetTimer () => ToolTip(), -1000
}

SetEngineEdge(*) {
    SetEngine("edge")
}

SetEngineLLM(*) {
    SetEngine("llm")
}

SetEngine(engine) {
    RunConfigCli("set-engine", "--engine " QuoteArg(engine))
    UpdateTrayChecks()
    ToolTip "Translation engine: " ((engine = "llm") ? "LLM" : "Edge")
    SetTimer () => ToolTip(), -1000
}

ReloadConfigFromMenu(*) {
    UpdateTrayChecks()
    ToolTip "Config reloaded"
    SetTimer () => ToolTip(), -1000
}

WatchConfigChanges() {
    global CONFIG_LAST_MTIME

    configPath := UserConfigPath()
    currentMtime := ""
    try currentMtime := FileGetTime(configPath, "M")
    catch
        currentMtime := ""

    if (currentMtime = "")
        return

    if (CONFIG_LAST_MTIME = "") {
        CONFIG_LAST_MTIME := currentMtime
        return
    }

    if (currentMtime != CONFIG_LAST_MTIME) {
        CONFIG_LAST_MTIME := currentMtime
        UpdateTrayChecks()
    }
}

OpenSettings(*) {
    LaunchPython("settings_app.py", "")
}

LoadConfigSummary() {
    tempDir := A_Temp "\FlipText"
    if !DirExist(tempDir)
        DirCreate(tempDir)

    resultPath := tempDir "\config_summary.json"
    try FileDelete(resultPath)

    try {
        exitCode := RunPythonWait("config_cli.py", "summary --result-file " QuoteArg(resultPath))
    } catch as err {
        LogDebug("Failed to run config summary command. " err.Message)
        return DefaultSummary()
    }

    if !FileExist(resultPath) {
        LogDebug("Failed to load config summary. Exit code " exitCode ".")
        return DefaultSummary()
    }

    try {
        return ParseSummaryText(FileRead(resultPath, "UTF-8"))
    } catch as err {
        LogDebug("Invalid config summary text. " err.Message)
        return DefaultSummary()
    }
}

UserConfigPath() {
    appData := EnvGet("APPDATA")
    if (appData = "")
        throw Error("APPDATA is not available.")
    return appData "\FlipText\config.json"
}

DefaultSummary() {
    return {
        engine: "edge",
        active_profile_id: "",
        active_profile_label: "",
        active_timeout_ms: 30000,
        profiles: [],
        prompt_presets: []
    }
}

ParseSummaryText(text) {
    summary := DefaultSummary()
    profiles := []

    for _, rawLine in StrSplit(text, "`n", "`r") {
        line := Trim(rawLine)
        if (line = "")
            continue

        pos := InStr(line, "=")
        if (pos <= 0)
            continue

        key := SubStr(line, 1, pos - 1)
        value := SubStr(line, pos + 1)

        if (key = "ok") {
            if (value != "1")
                throw Error("summary command returned failure")
        } else if (key = "error") {
            throw Error(UnescapeSummaryValue(value))
        } else if (key = "engine") {
            summary.engine := UnescapeSummaryValue(value)
        } else if (key = "active_profile_id") {
            summary.active_profile_id := UnescapeSummaryValue(value)
        } else if (key = "active_profile_label") {
            summary.active_profile_label := UnescapeSummaryValue(value)
        } else if (key = "active_timeout_ms") {
            summary.active_timeout_ms := IntegerOrDefault(value, 30000)
        } else if (key = "profile") {
            parts := SplitEscapedProfile(value)
            if (parts.Length >= 4) {
                profiles.Push({
                    id: UnescapeSummaryValue(parts[1]),
                    label: UnescapeSummaryValue(parts[2]),
                    enabled: (parts[3] = "1"),
                    timeout_ms: IntegerOrDefault(parts[4], 30000)
                })
            }
        } else if (key = "prompt_preset") {
            parts := SplitEscapedProfile(value)
            if (parts.Length >= 4) {
                summary.prompt_presets.Push({
                    id: UnescapeSummaryValue(parts[1]),
                    shortcut: UnescapeSummaryValue(parts[2]),
                    name: UnescapeSummaryValue(parts[3]),
                    label: UnescapeSummaryValue(parts[4])
                })
            }
        }
    }

    summary.profiles := profiles
    return summary
}

SplitEscapedProfile(value) {
    parts := []
    current := ""
    escaping := false

    Loop Parse, value {
        ch := A_LoopField
        if escaping {
            current .= "\" ch
            escaping := false
            continue
        }
        if (ch = "\") {
            escaping := true
            continue
        }
        if (ch = "|") {
            parts.Push(current)
            current := ""
            continue
        }
        current .= ch
    }

    parts.Push(current)
    return parts
}

UnescapeSummaryValue(value) {
    value := StrReplace(value, "\\n", "`n")
    value := StrReplace(value, "\\p", "|")
    value := StrReplace(value, "\\e", "=")
    value := StrReplace(value, "\\\\", "\")
    return value
}

IntegerOrDefault(value, defaultValue) {
    if RegExMatch(Trim(value), "^\d+$")
        return value + 0
    return defaultValue
}

GetSummaryProfiles(summary) {
    try return summary.profiles
    catch
        return []
}

GetPromptPresets(summary) {
    try return summary.prompt_presets
    catch
        return []
}

WaitForPromptAction() {
    summary := LoadConfigSummary()
    ToolTip BuildPromptActionHint(summary)

    ih := InputHook("L1 T3")
    ih.Start()
    ih.Wait()

    SetTimer () => ToolTip(), -10

    key := StrLower(ih.Input)
    if (key = "") {
        ToolTip "Prompt action cancelled"
        SetTimer () => ToolTip(), -1000
        return ""
    }

    if (key = "1")
        return { type: "translation", key: key, name: "Translate" }

    for _, preset in GetPromptPresets(summary) {
        if (preset.shortcut = key)
            return { type: "preset", id: preset.id, key: key, name: preset.name }
    }

    ToolTip "No prompt action mapped to '" key "'"
    SetTimer () => ToolTip(), -1000
    return ""
}

BuildPromptActionHint(summary) {
    text := "Press 1 for translation"
    for _, preset in GetPromptPresets(summary) {
        if (preset.shortcut != "")
            text .= "`n" preset.shortcut ": " preset.name
    }
    return text
}

RunConfigCli(command, args) {
    exitCode := RunPythonWait("config_cli.py", command " " args)
    if (exitCode != 0)
        throw Error("Config command failed: " command)
}

RunPythonWait(scriptName, args) {
    pythonPath := PythonExePath()
    scriptPath := A_ScriptDir "\" scriptName
    cmd := QuoteArg(pythonPath) " " QuoteArg(scriptPath)
    if (args != "")
        cmd .= " " args
    return RunWait(cmd, A_ScriptDir, "Hide")
}

LaunchPython(scriptName, args) {
    pythonPath := PythonGuiExePath()
    scriptPath := A_ScriptDir "\" scriptName
    cmd := QuoteArg(pythonPath) " " QuoteArg(scriptPath)
    if (args != "")
        cmd .= " " args
    Run cmd, A_ScriptDir, "Hide"
}

PythonExePath() {
    pythonPath := A_ScriptDir "\.venv\Scripts\python.exe"
    if !FileExist(pythonPath)
        throw Error("Python environment not found at " pythonPath ". Run uv sync first.")
    return pythonPath
}

PythonGuiExePath() {
    pythonwPath := A_ScriptDir "\.venv\Scripts\pythonw.exe"
    if FileExist(pythonwPath)
        return pythonwPath
    return PythonExePath()
}

QuoteArg(value) {
    return '"' StrReplace(value, '"', '\"') '"'
}

EdgeTranslate(text) {
    whr := ComObject("WinHttp.WinHttpRequest.5.1")
    whr.Open("GET", "https://edge.microsoft.com/translate/auth", false)
    whr.Send()
    token := whr.ResponseText

    is_hz := RegExMatch(text, "[\x{4E00}-\x{9FFF}]")
    from := (is_hz ? "zh" : "en")
    to := (is_hz ? "en" : "zh")
    url := "https://api-edge.cognitive.microsofttranslator.com/translate?from=" from "&to=" to "&api-version=3.0"

    whr.Open("POST", url, false)
    whr.SetRequestHeader("Authorization", "Bearer " token)
    whr.SetRequestHeader("Content-Type", "application/json")

    cleanText := StrReplace(text, "\", "\\")
    cleanText := StrReplace(cleanText, '"', '\"')
    cleanText := StrReplace(cleanText, "`r", "")
    cleanText := StrReplace(cleanText, "`n", "\n")

    body := '[{"Text":"' cleanText '"}]'
    whr.Send(body)

    if RegExMatch(whr.ResponseText, '"text":"((?:[^"\\]|\\.)*)"', &m)
        return JSON_Unescape(m[1])

    return "Error"
}

LogDebug(message) {
    timestamp := FormatTime(, "yyyy-MM-dd HH:mm:ss")
    FileAppend(timestamp " " message "`n", LOG_PATH, "UTF-8")
}

FormatSeconds(ms) {
    seconds := Ceil(ms / 1000)
    if (seconds < 0)
        seconds := 0
    return seconds "s"
}

FormatDuration(ms) {
    seconds := ms / 1000.0
    return Format("{:.1f}s", seconds)
}

JSON_Parse(str) {
    static doc := ComObject("htmlfile")
    doc.write("<meta http-equiv='X-UA-Compatible' content='IE=edge'>")
    return doc.parentWindow.JSON.parse(str)
}

JSON_Unescape(str) {
    return JSON_Parse('"' . str . '"')
}
