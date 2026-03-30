; ═══════════════════════════════════════════════════════════════════════
; Istara Windows Installer — NSIS + MUI2
; Production-ready installer with dependency management
; ═══════════════════════════════════════════════════════════════════════
;
; Build: makensis nsis-installer.nsi
; Requires: NSIS 3.x (https://nsis.sourceforge.io)

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "nsDialogs.nsh"
!include "WinMessages.nsh"

; ── Metadata ──────────────────────────────────────────────────────────
Name "Istara"
!define VERSION "2026.03.30.6"
OutFile "Istara-Setup-${VERSION}.exe"
InstallDir "$PROGRAMFILES\Istara"
RequestExecutionLevel admin
BrandingText "Istara ${VERSION} — Local-first AI for UX Research"
Unicode True

; ── Variables ─────────────────────────────────────────────────────────
Var InstallMode       ; "full" or "client"
Var InstallPython     ; 1 = install
Var InstallNode       ; 1 = install
Var InstallOllama     ; 1 = install
Var LLMProvider       ; "lmstudio" or "ollama"
Var PythonDetected
Var NodeDetected
Var OllamaDetected
Var LMStudioDetected

; ── MUI Settings ──────────────────────────────────────────────────────
!define MUI_ICON "..\..\desktop\src-tauri\icons\icon.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEFINISHPAGE_BITMAP_NOSTRETCH

; ── Pages ─────────────────────────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME

; Custom: Install Mode Selection
Page custom PageInstallMode PageInstallModeLeave

; Custom: Dependency Check (Server mode only)
Page custom PageDependencies PageDependenciesLeave

; Custom: LLM Provider (Server mode only)
Page custom PageLLMProvider PageLLMProviderLeave

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ═══════════════════════════════════════════════════════════════════════
; CUSTOM PAGES
; ═══════════════════════════════════════════════════════════════════════

; ── Page: Install Mode ────────────────────────────────────────────────
Function PageInstallMode
    nsDialogs::Create 1018
    Pop $0

    ${NSD_CreateLabel} 0 0 100% 20u "Choose how to install Istara:"
    Pop $0

    ${NSD_CreateRadioButton} 20u 30u 90% 12u "Server (Full Install) — Run your own Istara server"
    Pop $1
    ${NSD_Check} $1

    ${NSD_CreateLabel} 40u 44u 85% 16u "Installs backend, frontend, AI agents, and web UI. Requires Python 3.12 and Node.js 20."
    Pop $0
    SetCtlColors $0 808080 transparent

    ${NSD_CreateRadioButton} 20u 68u 90% 12u "Client Only — Connect to an existing Istara server"
    Pop $2

    ${NSD_CreateLabel} 40u 82u 85% 16u "Installs the relay daemon and system tray app. Requires only Node.js 20."
    Pop $0
    SetCtlColors $0 808080 transparent

    nsDialogs::Show
FunctionEnd

Function PageInstallModeLeave
    ; Read radio button states
    ${NSD_GetState} $1 $0
    ${If} $0 == ${BST_CHECKED}
        StrCpy $InstallMode "full"
    ${Else}
        StrCpy $InstallMode "client"
    ${EndIf}
FunctionEnd

; ── Page: Dependencies ────────────────────────────────────────────────
Function PageDependencies
    ; Skip for client mode
    ${If} $InstallMode == "client"
        Abort
    ${EndIf}

    ; Detect installed software
    Call DetectDependencies

    nsDialogs::Create 1018
    Pop $0

    ${NSD_CreateLabel} 0 0 100% 16u "Istara needs these dependencies. Check the ones to install:"
    Pop $0

    ; Python
    ${If} $PythonDetected == "1"
        ${NSD_CreateCheckbox} 20u 24u 90% 12u "Python 3.12 — Already installed"
        Pop $1
        EnableWindow $1 0
    ${Else}
        ${NSD_CreateCheckbox} 20u 24u 90% 12u "Python 3.12 — Download and install"
        Pop $1
        ${NSD_Check} $1
    ${EndIf}

    ; Node.js
    ${If} $NodeDetected == "1"
        ${NSD_CreateCheckbox} 20u 42u 90% 12u "Node.js 20 — Already installed"
        Pop $2
        EnableWindow $2 0
    ${Else}
        ${NSD_CreateCheckbox} 20u 42u 90% 12u "Node.js 20 — Download and install"
        Pop $2
        ${NSD_Check} $2
    ${EndIf}

    ; Ollama
    ${If} $OllamaDetected == "1"
        ${NSD_CreateCheckbox} 20u 60u 90% 12u "Ollama — Already installed"
        Pop $3
        EnableWindow $3 0
    ${Else}
        ${NSD_CreateCheckbox} 20u 60u 90% 12u "Ollama — Download and install (optional)"
        Pop $3
    ${EndIf}

    ${NSD_CreateLabel} 20u 84u 90% 20u "LM Studio must be installed separately from lmstudio.ai (GUI installer)."
    Pop $0
    SetCtlColors $0 808080 transparent

    nsDialogs::Show
FunctionEnd

Function PageDependenciesLeave
    ${NSD_GetState} $1 $0
    ${If} $0 == ${BST_CHECKED}
        StrCpy $InstallPython "1"
    ${Else}
        StrCpy $InstallPython "0"
    ${EndIf}

    ${NSD_GetState} $2 $0
    ${If} $0 == ${BST_CHECKED}
        StrCpy $InstallNode "1"
    ${Else}
        StrCpy $InstallNode "0"
    ${EndIf}

    ${NSD_GetState} $3 $0
    ${If} $0 == ${BST_CHECKED}
        StrCpy $InstallOllama "1"
    ${Else}
        StrCpy $InstallOllama "0"
    ${EndIf}
FunctionEnd

; ── Page: LLM Provider ────────────────────────────────────────────────
Function PageLLMProvider
    ${If} $InstallMode == "client"
        Abort
    ${EndIf}

    nsDialogs::Create 1018
    Pop $0

    ${NSD_CreateLabel} 0 0 100% 16u "Choose your LLM provider:"
    Pop $0

    ${NSD_CreateRadioButton} 20u 24u 90% 12u "LM Studio (Recommended) — GUI for managing AI models"
    Pop $1
    ${NSD_Check} $1

    ${NSD_CreateRadioButton} 20u 44u 90% 12u "Ollama — CLI-based, lightweight"
    Pop $2

    ${NSD_CreateLabel} 20u 68u 90% 24u "After installation, download a model (recommended: Qwen 3.5 4B or Gemma 3 12B) from your chosen provider."
    Pop $0
    SetCtlColors $0 808080 transparent

    nsDialogs::Show
FunctionEnd

Function PageLLMProviderLeave
    ${NSD_GetState} $1 $0
    ${If} $0 == ${BST_CHECKED}
        StrCpy $LLMProvider "lmstudio"
    ${Else}
        StrCpy $LLMProvider "ollama"
    ${EndIf}
FunctionEnd

; ═══════════════════════════════════════════════════════════════════════
; DEPENDENCY DETECTION
; ═══════════════════════════════════════════════════════════════════════

Function DetectDependencies
    ; Python
    nsExec::ExecToStack 'python --version'
    Pop $0
    ${If} $0 == "0"
        StrCpy $PythonDetected "1"
    ${Else}
        nsExec::ExecToStack 'python3 --version'
        Pop $0
        ${If} $0 == "0"
            StrCpy $PythonDetected "1"
        ${Else}
            StrCpy $PythonDetected "0"
        ${EndIf}
    ${EndIf}

    ; Node.js
    nsExec::ExecToStack 'node --version'
    Pop $0
    ${If} $0 == "0"
        StrCpy $NodeDetected "1"
    ${Else}
        StrCpy $NodeDetected "0"
    ${EndIf}

    ; Ollama
    nsExec::ExecToStack 'ollama --version'
    Pop $0
    ${If} $0 == "0"
        StrCpy $OllamaDetected "1"
    ${Else}
        StrCpy $OllamaDetected "0"
    ${EndIf}
FunctionEnd

; ═══════════════════════════════════════════════════════════════════════
; INSTALLATION
; ═══════════════════════════════════════════════════════════════════════

Section "Install Dependencies"
    ; Download and install Python
    ${If} $InstallPython == "1"
        DetailPrint "Downloading Python 3.12..."
        inetc::get "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" "$TEMP\python-3.12.8.exe" /END
        DetailPrint "Installing Python 3.12..."
        nsExec::ExecToLog '"$TEMP\python-3.12.8.exe" /quiet PrependPath=1 Include_pip=1'
        Delete "$TEMP\python-3.12.8.exe"
    ${EndIf}

    ; Download and install Node.js
    ${If} $InstallNode == "1"
        DetailPrint "Downloading Node.js 20..."
        inetc::get "https://nodejs.org/dist/v20.18.0/node-v20.18.0-x64.msi" "$TEMP\node-v20.18.0.msi" /END
        DetailPrint "Installing Node.js 20..."
        nsExec::ExecToLog 'msiexec /i "$TEMP\node-v20.18.0.msi" /quiet /norestart'
        Delete "$TEMP\node-v20.18.0.msi"
    ${EndIf}

    ; Download and install Ollama
    ${If} $InstallOllama == "1"
        DetailPrint "Downloading Ollama..."
        inetc::get "https://ollama.com/download/OllamaSetup.exe" "$TEMP\OllamaSetup.exe" /END
        DetailPrint "Installing Ollama..."
        nsExec::ExecToLog '"$TEMP\OllamaSetup.exe" /S'
        Delete "$TEMP\OllamaSetup.exe"
    ${EndIf}
SectionEnd

Section "Istara Files"
    SetOutPath $INSTDIR

    ; Copy Istara source code
    DetailPrint "Installing Istara files..."

    ; Backend
    SetOutPath "$INSTDIR\backend"
    File /r /x "__pycache__" /x "*.pyc" /x ".env" /x "data" /x "venv" \
        "..\..\backend\*"

    ; Frontend
    SetOutPath "$INSTDIR\frontend"
    File /r /x "node_modules" /x ".next" /x "out" \
        "..\..\frontend\*"

    ; Relay
    SetOutPath "$INSTDIR\relay"
    File /r /x "node_modules" \
        "..\..\relay\*"

    ; Desktop app (Tauri binary)
    SetOutPath "$INSTDIR"
    File "..\..\desktop\src-tauri\target\release\Istara.exe"

    ; Config template
    File "..\..\\.env.example"

    ; Service wrapper
    File "istara-service.bat"

    ; Create data directories
    CreateDirectory "$INSTDIR\data"
    CreateDirectory "$INSTDIR\data\uploads"
    CreateDirectory "$INSTDIR\data\projects"
    CreateDirectory "$INSTDIR\data\lance_db"
    CreateDirectory "$INSTDIR\data\backups"
SectionEnd

Section "Setup Backend"
    ${If} $InstallMode == "full"
        ; Create Python virtual environment
        DetailPrint "Creating Python virtual environment..."
        nsExec::ExecToLog 'python -m venv "$INSTDIR\venv"'

        ; Install backend dependencies
        DetailPrint "Installing backend dependencies (this may take several minutes)..."
        nsExec::ExecToLog '"$INSTDIR\venv\Scripts\pip.exe" install -r "$INSTDIR\backend\requirements.txt"'

        ; Install frontend dependencies
        DetailPrint "Installing frontend dependencies..."
        SetOutPath "$INSTDIR\frontend"
        nsExec::ExecToLog 'npm ci'

        ; Build frontend
        DetailPrint "Building frontend..."
        nsExec::ExecToLog 'npm run build'
    ${EndIf}

    ${If} $InstallMode == "client"
        ; Client only needs relay deps
        DetailPrint "Installing relay dependencies..."
        SetOutPath "$INSTDIR\relay"
        nsExec::ExecToLog 'npm install --production'
    ${EndIf}
SectionEnd

Section "Shortcuts & Registry"
    ; Start Menu
    CreateDirectory "$SMPROGRAMS\Istara"
    CreateShortcut "$SMPROGRAMS\Istara\Istara.lnk" "$INSTDIR\Istara.exe"
    CreateShortcut "$SMPROGRAMS\Istara\Uninstall.lnk" "$INSTDIR\uninstall.exe"

    ; Desktop shortcut (optional)
    CreateShortcut "$DESKTOP\Istara.lnk" "$INSTDIR\Istara.exe"

    ; Add to PATH
    EnVar::AddValue "PATH" "$INSTDIR"

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Registry for Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Istara" \
        "DisplayName" "Istara"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Istara" \
        "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Istara" \
        "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Istara" \
        "Publisher" "Istara Team"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Istara" \
        "DisplayIcon" "$INSTDIR\Istara.exe"

    ; Optional: Auto-start on login
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" \
        "Istara" "$\"$INSTDIR\Istara.exe$\""
SectionEnd

; ═══════════════════════════════════════════════════════════════════════
; UNINSTALLER
; ═══════════════════════════════════════════════════════════════════════

Section "Uninstall"
    ; Stop services
    nsExec::ExecToLog 'taskkill /f /im Istara.exe'
    nsExec::ExecToLog 'taskkill /f /im python.exe /fi "WINDOWTITLE eq uvicorn"'
    nsExec::ExecToLog 'taskkill /f /im node.exe'

    ; Remove auto-start
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Istara"

    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Istara"

    ; Remove shortcuts
    RMDir /r "$SMPROGRAMS\Istara"
    Delete "$DESKTOP\Istara.lnk"

    ; Remove program files (but NOT data directory)
    RMDir /r "$INSTDIR\backend"
    RMDir /r "$INSTDIR\frontend"
    RMDir /r "$INSTDIR\relay"
    RMDir /r "$INSTDIR\venv"
    Delete "$INSTDIR\Istara.exe"
    Delete "$INSTDIR\.env.example"
    Delete "$INSTDIR\istara-service.bat"
    Delete "$INSTDIR\uninstall.exe"

    ; Ask about data
    MessageBox MB_YESNO "Keep your research data (projects, documents, database)?$\n$\nClick Yes to keep, No to delete everything." IDYES keepdata
        RMDir /r "$INSTDIR\data"
    keepdata:

    RMDir "$INSTDIR"
SectionEnd
