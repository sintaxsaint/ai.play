; ai.play Windows Installer
; Nullsoft Scriptable Install System (NSIS)

!define APPNAME "ai.play"
!define VERSION "0.6"
!define PUBLISHER "sintaxsaint"
!define INSTALL_DIR "$PROGRAMFILES64\aiplay"
!define UNINSTALL_REG "Software\Microsoft\Windows\CurrentVersion\Uninstall\aiplay"

Name "${APPNAME} ${VERSION}"
OutFile "aiplay-setup.exe"
Icon "aip.ico"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKLM "Software\aiplay" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

; ─────────────────────────────────────────
; PAGES
; ─────────────────────────────────────────
Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

; ─────────────────────────────────────────
; INSTALLER
; ─────────────────────────────────────────
Section "ai.play Runtime" SecMain
    SectionIn RO

    ; ── Auto-uninstall old version if present ──
    ReadRegStr $0 HKLM "${UNINSTALL_REG}" "UninstallString"
    StrCmp $0 "" skip_uninstall
        ExecWait '"$0" /S'
    skip_uninstall:

    ; ── Copy runtime files ──────────────────
    SetOutPath "$INSTDIR"
    File "dist\aip\aip.exe"
    File "aip.ico"

    ; Copy _internal recursively (gets all DLLs and subfolders)
    SetOutPath "$INSTDIR\_internal"
    File /r "dist\aip\_internal\*"

    ; ── Copy Python source files ────────────
    SetOutPath "$INSTDIR"
    File "aiplay.py"
    File "lexer.py"
    File "parser.py"
    File "ast_nodes.py"
    File "interpreter.py"
    File "runtime.py"
    File "format_detector.py"
    File "memory_engine.py"
    File "skills_engine.py"
    File "module_engine.py"
    File "user_memory.py"
    File "server.py"
    File "ui_server.py"
    File "intent_engine.py"
    File "voice_engine.py"
    File "video_engine.py"
    File "notify_engine.py"
    File "vision_trainer.py"
    File "ai_yes.py"
    File "call_handler.py"

    ; ── Create modules directory ────────────
    CreateDirectory "$INSTDIR\modules"

    ; ── Registry ────────────────────────────
    WriteRegStr HKLM "Software\aiplay" "InstallDir" "$INSTDIR"

    ; ── Add to system PATH ──────────────────
    ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
    ; Only add if not already in PATH
    StrCpy $1 $0
    Push $1
    Push "$INSTDIR"
    Call StrContains
    Pop $2
    StrCmp $2 "" 0 skip_path
        StrCpy $1 "$0;$INSTDIR"
        WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$1"
        SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=500
    skip_path:

    ; ── .aip file association ───────────────
    WriteRegStr HKCR ".aip" "" "aiplay.file"
    WriteRegStr HKCR ".aip" "Content Type" "text/x-aiplay"
    WriteRegStr HKCR "aiplay.file" "" "ai.play Source File"
    WriteRegStr HKCR "aiplay.file\DefaultIcon" "" "$INSTDIR\aip.ico"
    WriteRegStr HKCR "aiplay.file\shell\open" "" "Run with ai.play"
    WriteRegStr HKCR "aiplay.file\shell\open\command" "" '"cmd.exe" /k "$INSTDIR\aip.exe" "%1"'
    WriteRegStr HKCR "aiplay.file\shell\run" "" "Run with ai.play"
    WriteRegStr HKCR "aiplay.file\shell\run\command" "" '"cmd.exe" /k "$INSTDIR\aip.exe" "%1"'
    WriteRegStr HKCR "aiplay.file\shell\check" "" "Syntax Check"
    WriteRegStr HKCR "aiplay.file\shell\check\command" "" '"cmd.exe" /k "$INSTDIR\aip.exe" check "%1"'
    WriteRegStr HKCR "aiplay.file\shell\edit" "" "Edit"
    WriteRegStr HKCR "aiplay.file\shell\edit\command" "" '"notepad.exe" "%1"'

    ; ── Uninstaller ──────────────────────────
    WriteUninstaller "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${UNINSTALL_REG}" "DisplayName" "ai.play"
    WriteRegStr HKLM "${UNINSTALL_REG}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "${UNINSTALL_REG}" "Publisher" "${PUBLISHER}"
    WriteRegStr HKLM "${UNINSTALL_REG}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${UNINSTALL_REG}" "InstallLocation" "$INSTDIR"
    WriteRegDWORD HKLM "${UNINSTALL_REG}" "NoModify" 1
    WriteRegDWORD HKLM "${UNINSTALL_REG}" "NoRepair" 1

    System::Call 'shell32.dll::SHChangeNotify(i, i, i, i) v (0x8000000, 0, 0, 0)'

SectionEnd

; ─────────────────────────────────────────
; UNINSTALLER
; ─────────────────────────────────────────
Section "Uninstall"
    ; Remove from PATH
    ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
    Push "$0"
    Push ";$INSTDIR"
    Push ""
    Call un.StrReplace
    Pop $1
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$1"
    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=500

    ; Remove file associations
    DeleteRegKey HKCR ".aip"
    DeleteRegKey HKCR "aiplay.file"

    ; Remove install dir
    RMDir /r "$INSTDIR"

    ; Remove registry
    DeleteRegKey HKLM "${UNINSTALL_REG}"
    DeleteRegKey HKLM "Software\aiplay"

    System::Call 'shell32.dll::SHChangeNotify(i, i, i, i) v (0x8000000, 0, 0, 0)'
SectionEnd

; ─────────────────────────────────────────
; HELPERS
; ─────────────────────────────────────────
Function StrContains
    Exch $R1 ; string to find
    Exch
    Exch $R0 ; string to search
    Push $R2
    Push $R3
    StrLen $R2 $R1
    StrCpy $R3 0
    loop:
        StrCpy $R4 $R0 $R2 $R3
        StrCmp $R4 "" done_notfound
        StrCmp $R4 $R1 done_found
        IntOp $R3 $R3 + 1
        Goto loop
    done_found:
        StrCpy $R0 $R1
        Goto done
    done_notfound:
        StrCpy $R0 ""
    done:
    Pop $R3
    Pop $R2
    Exch $R0
    Exch
    Pop $R1
FunctionEnd

Function un.StrReplace
    Exch $R2
    Exch
    Exch $R1
    Exch 2
    Exch $R0
    Push $R3
    Push $R4
    Push $R5
    StrLen $R3 $R1
    StrCpy $R4 0
    loop:
        StrCpy $R5 $R0 $R3 $R4
        StrCmp $R5 $R1 found
        StrCmp $R5 "" done
        IntOp $R4 $R4 + 1
        Goto loop
    found:
        StrCpy $R5 $R0 $R4
        StrCpy $R0 $R0 "" $R4
        StrLen $R4 $R1
        StrCpy $R0 $R0 "" $R4
        StrCpy $R0 "$R5$R2$R0"
        Goto loop
    done:
    Pop $R5
    Pop $R4
    Pop $R3
    Push $R0
    Exch
    Pop $R0
    Exch
    Pop $R1
    Exch
    Pop $R2
FunctionEnd
