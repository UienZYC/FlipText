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
global CONFIG_PATH := A_ScriptDir "\FlipText.ini"
global LOG_PATH := A_ScriptDir "\FlipText.log"
global PROFILE_MENU := Menu()

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

    if (TransGui) {
        TransGui.Destroy()
        TransGui := ""
    }

    StartTranslation(targetText)
}

StartTranslation(text) {
    try {
        config := LoadGeneralConfig()
        if (config["engine"] = "llm") {
            StartLoadingState(config["active_profile"])

            try {
                result := PythonTranslate(text, config["active_profile"])
                StopLoadingState()
                G_STATE.Result := result["text"]
                G_STATE.Source := result["source"]
            } catch as err {
                StopLoadingState()
                LogDebug("LLM translation failed. " err.Message)
                G_STATE.Result := EdgeTranslate(text)
                G_STATE.Source := "Edge fallback: " config["active_profile"]
            }
        } else {
            G_STATE.LastDurationMs := 0
            G_STATE.Result := EdgeTranslate(text)
            G_STATE.Source := "Edge"
        }

        keys := ["~LButton","~Up","~Down","~Left","~Right","~BS","~Del","~Enter","~NumpadEnter"]
        for k in keys
            Hotkey k, MarkAsMoved, "On"

        Hotkey "Tab", DoReplace, "On"
        Hotkey "Esc", ClearUI, "On"

        UpdateTransGui(G_STATE.Result)
    } catch {
        UpdateTransGui("Translation Error")
        SetTimer(ClearUI, -2000)
    }
}

UpdateTransGui(newStr) {
    global TransGui, TransSourceCtrl, TransBodyCtrl, G_STATE

    if (TransGui) {
        TransGui.Destroy()
        TransGui := ""
        TransSourceCtrl := ""
        TransBodyCtrl := ""
    }

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
    global TransGui, TransSourceCtrl, TransBodyCtrl, G_STATE
    StopLoadingState()
    if (TransGui) {
        TransGui.Destroy()
        TransGui := ""
    }
    TransSourceCtrl := ""
    TransBodyCtrl := ""
    G_STATE.Source := ""
    G_STATE.LastDurationMs := 0

    keys := ["~LButton","~Up","~Down","~Left","~Right","~BS","~Del","~Enter","~NumpadEnter","Tab","Esc"]
    for k in keys
        try Hotkey k, "Off"
}

MarkAsMoved(*) => G_STATE.IsMoved := true

StartLoadingState(profileName) {
    global G_STATE

    G_STATE.Source := "LLM: " profileName
    G_STATE.IsLoading := true
    G_STATE.LoadingStartedAt := A_TickCount
    G_STATE.LoadingTimeoutMs := LoadProfileTimeoutMs(profileName)
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

    text := "Translating with LLM... " FormatSeconds(remainingMs) " left"
    if (elapsedMs > 0)
        text .= " | " FormatDuration(elapsedMs) " elapsed"

    if (TransBodyCtrl)
        TransBodyCtrl.Text := text
}

ShowLoadingGui() {
    global TransGui, TransSourceCtrl, TransBodyCtrl, G_STATE

    if (TransGui) {
        TransGui.Destroy()
        TransGui := ""
    }

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

PythonTranslate(text, profileName) {
    global CONFIG_PATH, LOG_PATH

    tempDir := A_Temp "\FlipText"
    if !DirExist(tempDir)
        DirCreate(tempDir)

    inputPath := tempDir "\llm_input.txt"
    outputPath := tempDir "\llm_output.json"

    try FileDelete(inputPath)
    try FileDelete(outputPath)

    FileAppend(text, inputPath, "UTF-8")

    pythonPath := A_ScriptDir "\.venv\Scripts\python.exe"
    if !FileExist(pythonPath) {
        throw Error("Python environment not found at " pythonPath ". Run uv sync first.")
    }

    cmd := A_ComSpec ' /C ""' pythonPath '" "' A_ScriptDir '\llm_translate.py" --config "' CONFIG_PATH '" --profile "' profileName '" --text-file "' inputPath '" --result-file "' outputPath '" --log-file "' LOG_PATH '""'
    exitCode := RunWait(cmd, A_ScriptDir, "Hide")
    if !FileExist(outputPath) {
        throw Error("Python translator did not produce output. Exit code " exitCode ".")
    }

    result := JSON_Parse(FileRead(outputPath, "UTF-8"))
    if !result.ok {
        throw Error(result.error)
    }

    translated := result.text
    if (Trim(translated, " `t`r`n") = "") {
        throw Error("Python translator returned empty text.")
    }

    source := result.source
    if (source = "") {
        source := "LLM: " profileName
    }

    return Map("text", translated, "source", source)
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

SetupTrayMenu() {
    EnsureConfigFile()
    A_TrayMenu.Add()
    A_TrayMenu.Add("Use Edge Translation", SetEngineEdge)
    A_TrayMenu.Add("Use LLM Translation", SetEngineLLM)
    A_TrayMenu.Add("LLM Profiles", PROFILE_MENU)
    A_TrayMenu.Add("Reload Config", ReloadConfigFromMenu)
    A_TrayMenu.Add("Open Config", OpenConfigFile)
    UpdateTrayChecks()
}

UpdateTrayChecks() {
    config := LoadGeneralConfig()

    try A_TrayMenu.Uncheck("Use Edge Translation")
    try A_TrayMenu.Uncheck("Use LLM Translation")

    if (config["engine"] = "llm")
        A_TrayMenu.Check("Use LLM Translation")
    else
        A_TrayMenu.Check("Use Edge Translation")

    RebuildProfileMenu(config["active_profile"])
}

RebuildProfileMenu(activeProfile) {
    global PROFILE_MENU

    try PROFILE_MENU.Delete()

    for _, profileName in GetProfileNames() {
        PROFILE_MENU.Add(profileName, SelectLLMProfile)
        if (profileName = activeProfile)
            PROFILE_MENU.Check(profileName)
    }
}

SelectLLMProfile(profileName, *) {
    SetActiveProfile(profileName)
}

SetActiveProfile(profileName) {
    global CONFIG_PATH

    IniWrite(NormalizeProfileName(profileName), CONFIG_PATH, "General", "active_profile")
    UpdateTrayChecks()
    ToolTip "LLM profile: " profileName
    SetTimer () => ToolTip(), -1000
}

SetEngineEdge(*) {
    SetEngine("edge")
}

SetEngineLLM(*) {
    SetEngine("llm")
}

SetEngine(engine) {
    global CONFIG_PATH

    IniWrite(engine, CONFIG_PATH, "General", "engine")
    UpdateTrayChecks()
    ToolTip "Translation engine: " ((engine = "llm") ? "LLM" : "Edge")
    SetTimer () => ToolTip(), -1000
}

ReloadConfigFromMenu(*) {
    UpdateTrayChecks()
    ToolTip "Config reloaded"
    SetTimer () => ToolTip(), -1000
}

OpenConfigFile(*) {
    global CONFIG_PATH
    Run CONFIG_PATH
}

LoadGeneralConfig() {
    EnsureConfigFile()

    config := Map()
    config["engine"] := NormalizeEngine(ReadIniValue("General", "engine", "edge"))
    config["active_profile"] := NormalizeProfileName(ReadIniValue("General", "active_profile", "default"))

    profileNames := GetProfileNames()
    if !ProfileExists(config["active_profile"], profileNames)
        config["active_profile"] := profileNames[1]

    return config
}

LoadProfileTimeoutMs(profileName) {
    timeoutValue := ReadProfileValue(profileName, "timeout_ms", "30000")
    return NormalizeTimeout(timeoutValue, 30000)
}

GetProfileNames() {
    global CONFIG_PATH

    profiles := []
    seen := Map()

    if FileExist(CONFIG_PATH) {
        configText := FileRead(CONFIG_PATH, "UTF-8")
        pos := 1
        while RegExMatch(configText, "m)^\[LLM\.([^\]\r\n]+)\]$", &m, pos) {
            profileName := NormalizeProfileName(m[1])
            if (profileName != "" && !seen.Has(profileName)) {
                profiles.Push(profileName)
                seen[profileName] := true
            }
            pos := m.Pos + m.Len
        }

        if RegExMatch(configText, "m)^\[LLM\]$") && !seen.Has("default")
            profiles.Push("default")
    }

    if (profiles.Length = 0)
        profiles.Push("default")

    return profiles
}

ProfileExists(profileName, profileNames) {
    for _, item in profileNames {
        if (item = profileName)
            return true
    }
    return false
}

EnsureConfigFile() {
    global CONFIG_PATH

    if FileExist(CONFIG_PATH)
        return

    IniWrite("edge", CONFIG_PATH, "General", "engine")
    IniWrite("default", CONFIG_PATH, "General", "active_profile")
    IniWrite("false", CONFIG_PATH, "LLM.default", "enabled")
    IniWrite("https://api.openai.com/v1", CONFIG_PATH, "LLM.default", "base_url")
    IniWrite("", CONFIG_PATH, "LLM.default", "api_key")
    IniWrite("", CONFIG_PATH, "LLM.default", "model")
    IniWrite("15000", CONFIG_PATH, "LLM.default", "timeout_ms")
    IniWrite("You are a professional translator. Translate the user's text accurately and naturally. Return only the translated text. Preserve line breaks, formatting, and tone. Do not add explanations, quotation marks, notes, or extra text.", CONFIG_PATH, "LLM.default", "system_prompt")
}

ReadIniValue(section, key, defaultValue) {
    global CONFIG_PATH

    try {
        return IniRead(CONFIG_PATH, section, key, defaultValue)
    } catch {
        return defaultValue
    }
}

ReadProfileValue(profileName, key, defaultValue) {
    profileName := NormalizeProfileName(profileName)
    value := ReadIniValue("LLM." profileName, key, "__MISSING__")
    if (value != "__MISSING__")
        return value
    return ReadIniValue("LLM", key, defaultValue)
}

NormalizeEngine(value) {
    value := StrLower(Trim(value))
    return (value = "llm") ? "llm" : "edge"
}

NormalizeTimeout(value, defaultValue := 15000) {
    value := Trim(value)
    if !RegExMatch(value, "^\d+$")
        return defaultValue

    timeout := value + 0
    if (timeout < 1000)
        return defaultValue

    return timeout
}

NormalizeProfileName(value) {
    value := Trim(value)
    if (value = "")
        return "default"
    return RegExReplace(value, "[\[\]\r\n]", "")
}

LogDebug(message) {
    global LOG_PATH

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
