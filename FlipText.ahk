#Requires AutoHotkey v2.0
Persistent

; 坐标模式设置为屏幕坐标
CoordMode "Mouse", "Screen"

; 全局状态管理
global G_STATE := { 
    Result: "", 
    X: 0, Y: 0, 
    IsMoved: false, 
    Mode: "Select"
}

global TransGui := "" 

; 脚本入口
F1::
{
    global TransGui 

    MouseGetPos(&mx, &my) 
    G_STATE.X := mx + 15
    G_STATE.Y := my + 15

    originalClipboard := ClipboardAll() ; 备份剪贴板
    A_Clipboard := ""                   ; 清空剪贴板
    G_STATE.IsMoved := false 
    
    targetText := ""
    try {
        Send "^c"
        ; SendEvent "^c"
        if !ClipWait(0.15) {    ; 如果在0.15s内没有直接复制到内容，说明当前没有选区
            G_STATE.Mode := "Line"
            Send "{vkE8}"       ; 使用 vkE8 防误触，不抢焦点
            BlockInput(true)    ; 开启输入阻塞 
            ; 选中整行
            Send "{End}"
            Sleep 15
            Send "+{Home}" 
            
            Sleep 50            ; 关键等待
            Send "^c"
            ClipWait(0.15)      ; 0.15s是测试得到的比较合适的时间
            Send "{End}"        ; 不使用right是因为可能会跳到下一行
            BlockInput(false)   ; 关闭输入阻塞
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
        ; 提示用户获取失败
        ToolTip "Failed to get text automatically, please select text first."
        ; 设置一个定时器，1秒后自动关闭这个提示
        SetTimer () => ToolTip(), -1000 
        return
    }

    if (TransGui) {
        TransGui.Destroy()
        TransGui := ""
    }

    StartEdgeTranslation(targetText)
}

StartEdgeTranslation(text) {
    try {
        G_STATE.Result := EdgeTranslate(text)
        
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

; 自适应 UI
UpdateTransGui(newStr) {
    global TransGui
    
    if (TransGui) {
        TransGui.Destroy()
    }
    
    TransGui := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20")
    TransGui.BackColor := "FFFFE1"
    TransGui.SetFont("s11 w700", "Microsoft YaHei")
    
    if (InStr(newStr, "`n") || StrLen(newStr) > 50) {
        TransGui.Add("Text", "c003366 w600 Wrap", newStr)
    } else {
        TransGui.Add("Text", "c003366", newStr)
    }
    
    TransGui.Show("x" G_STATE.X " y" G_STATE.Y " NoActivate AutoSize")
    WinSetTransparent(200, TransGui)
}

; 替换
DoReplace(*) {
    global G_STATE
    res := G_STATE.Result
    isLine := (G_STATE.Mode == "Line")
    moved := G_STATE.IsMoved
    
    ClearUI()
    
    if (res == "") {
        return
    }

    ; 1. 备份旧剪贴板
    tempClip := ClipboardAll()
    A_Clipboard := "" ; 先清空，确保检测准确
    A_Clipboard := res
    
    ; 2. 关键：确保译文确实进入了剪贴板
    if !ClipWait(0.5) {
        ; 如果剪贴板写入失败，恢复备份并退出
        A_Clipboard := tempClip
        return
    }

    ; 3. 设置按键延迟，模拟真实手速
    oldKeyDelay := A_KeyDelay
    SetKeyDelay 20, 20 ; 按下时长20ms，间隔20ms
    
    if (isLine && !moved) {
        BlockInput(true)
        
        ; 选中行
        SendEvent "{End}+{Home}" 
        
        ; 选中后强制等待200ms，等待编辑器高亮渲染完成
        Sleep 200 
        
        ; 粘贴
        SendEvent "^v"           
        
        ; 粘贴后强制等待300ms，确保编辑器读取完剪贴板
        Sleep 300 
        
        BlockInput(false)
    } else {
        SendEvent "^v"
        Sleep 300 ; 即使是普通插入，也等待一下
    }
    
    SetKeyDelay oldKeyDelay
    
    ; 4. 恢复旧剪贴板
    A_Clipboard := tempClip
}

ClearUI(*) {
    global TransGui
    if (TransGui) {
        TransGui.Destroy()
        TransGui := ""
    }
    
    keys := ["~LButton","~Up","~Down","~Left","~Right","~BS","~Del","~Enter","~NumpadEnter","Tab","Esc"]
    for k in keys
        try Hotkey k, "Off"
}

MarkAsMoved(*) => G_STATE.IsMoved := true

EdgeTranslate(text) {
    whr := ComObject("WinHttp.WinHttpRequest.5.1")
    whr.Open("GET", "https://edge.microsoft.com/translate/auth", false), whr.Send()
    token := whr.ResponseText
    is_hz := RegExMatch(text, "[\x{4E00}-\x{9FFF}]")
    from := (is_hz ? "zh" : "en"), to := (is_hz ? "en" : "zh")
    url := "https://api-edge.cognitive.microsofttranslator.com/translate?from=" from "&to=" to "&api-version=3.0"
    whr.Open("POST", url, false)
    whr.SetRequestHeader("Authorization", "Bearer " token), whr.SetRequestHeader("Content-Type", "application/json")

    ; whr.Send('[{"Text":"' StrReplace(StrReplace(text, '"', '\"'), '`n', '\n') '"}]')

    cleanText := StrReplace(text, "\", "\\")        ; 1. 先把 \ 变成 \\
    cleanText := StrReplace(cleanText, '"', '\"')   ; 2. 再把 " 变成 \" 注: 中文引号不需转义
    cleanText := StrReplace(cleanText, "`r", "")    ; 3. 去掉回车符
    cleanText := StrReplace(cleanText, "`n", "\n")  ; 4. 换行符转义 

    body := '[{"Text":"' cleanText '"}]'
    whr.Send(body)

    if RegExMatch(whr.ResponseText, '"text":"(.*?)"', &m)
        return JSON_Unescape(m[1])
    return "Error"
}

JSON_Unescape(str) {
    static doc := ComObject("htmlfile")
    doc.write("<meta http-equiv='X-UA-Compatible' content='IE=edge'>")
    return doc.parentWindow.JSON.parse('"' . str . '"')
}