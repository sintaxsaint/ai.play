; ai.play Windows Installer
; Nullsoft Scriptable Install System (NSIS)
; Installs the ai.play runtime + registers .aip file association
; Adds `aip` command to PATH

!define APPNAME "ai.play"
!define VERSION "0.1"
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

    SetOutPath "$INSTDIR"

    ; Copy all runtime files
    File "dist\aip\aip.exe"
    File "dist\aip\_internal\*.*"

    ; Copy the Python source files (for live compilation)
    File "aiplay.py"
    File "lexer.py"
    File "parser.py"
    File "ast_nodes.py"
    File "interpreter.py"
    File "runtime.py"
    File "format_detector.py"
    File "memory_engine.py"
    File "server.py"
    File "ui_server.py"
    File "voice_engine.py"
    File "video_engine.py"
    File "skills_engine.py"
    File "user_memory.py"
    File "aip.ico"

    ; Write install dir to registry
    WriteRegStr HKLM "Software\aiplay" "InstallDir" "$INSTDIR"

    ; ── Add to system PATH ──────────────────
    ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
    StrCpy $1 "$0;$INSTDIR"
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$1"
    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=500

    ; ── .aip file association ───────────────
    ; Register .aip extension
    WriteRegStr HKCR ".aip" "" "aiplay.file"
    WriteRegStr HKCR ".aip" "Content Type" "text/x-aiplay"

    ; Register file type
    WriteRegStr HKCR "aiplay.file" "" "ai.play Source File"
    WriteRegStr HKCR "aiplay.file\DefaultIcon" "" "$INSTDIR\aip.ico"

    ; Double-click: open terminal and run
    WriteRegStr HKCR "aiplay.file\shell\open" "" "Run with ai.play"
    WriteRegStr HKCR "aiplay.file\shell\open\command" "" \
        '"cmd.exe" /k "$INSTDIR\aip.exe" "%1"'

    ; Right-click: Run with ai.play
    WriteRegStr HKCR "aiplay.file\shell\run" "" "Run with ai.play"
    WriteRegStr HKCR "aiplay.file\shell\run\command" "" \
        '"cmd.exe" /k "$INSTDIR\aip.exe" "%1"'

    ; Right-click: Syntax Check
    WriteRegStr HKCR "aiplay.file\shell\check" "" "Syntax Check"
    WriteRegStr HKCR "aiplay.file\shell\check\command" "" \
        '"cmd.exe" /k "$INSTDIR\aip.exe" check "%1"'

    ; Right-click: Edit (opens in Notepad by default, VS Code if installed)
    WriteRegStr HKCR "aiplay.file\shell\edit" "" "Edit"
    WriteRegStr HKCR "aiplay.file\shell\edit\command" "" \
        '"notepad.exe" "%1"'

    ; ── Uninstaller ──────────────────────────
    WriteUninstaller "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${UNINSTALL_REG}" "DisplayName" "ai.play"
    WriteRegStr HKLM "${UNINSTALL_REG}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "${UNINSTALL_REG}" "Publisher" "${PUBLISHER}"
    WriteRegStr HKLM "${UNINSTALL_REG}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${UNINSTALL_REG}" "InstallLocation" "$INSTDIR"
    WriteRegDWORD HKLM "${UNINSTALL_REG}" "NoModify" 1
    WriteRegDWORD HKLM "${UNINSTALL_REG}" "NoRepair" 1

    ; ── Notify shell of file association change ─
    System::Call 'shell32.dll::SHChangeNotify(i, i, i, i) v (0x8000000, 0, 0, 0)'

SectionEnd

; ─────────────────────────────────────────
; UNINSTALLER
; ─────────────────────────────────────────
Section "Uninstall"
    ; Remove from PATH
    ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
    ; Simple removal — replace ;$INSTDIR with nothing
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

    ; Remove uninstall registry entry
    DeleteRegKey HKLM "${UNINSTALL_REG}"
    DeleteRegKey HKLM "Software\aiplay"

    System::Call 'shell32.dll::SHChangeNotify(i, i, i, i) v (0x8000000, 0, 0, 0)'
SectionEnd

; ── String replace helper for uninstaller ──
Function un.StrReplace
    Exch $R2 ; replace with
    Exch
    Exch $R1 ; find
    Exch 2
    Exch $R0 ; source
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
