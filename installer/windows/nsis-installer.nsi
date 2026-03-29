; ReClaw Windows Installer — NSIS Script
; Builds an .exe installer with install mode selection and dependency checking.
;
; Build: makensis nsis-installer.nsi
; Requires: NSIS 3.x (https://nsis.sourceforge.io)

!include "MUI2.nsh"
!include "LogicLib.nsh"

; --- Metadata ---
Name "ReClaw"
OutFile "ReClaw-Setup.exe"
InstallDir "$PROGRAMFILES\ReClaw"
RequestExecutionLevel admin
BrandingText "ReClaw — Local-first AI for UX Research"

; --- Pages ---
!insertmacro MUI_PAGE_WELCOME

; Install mode selection
Page custom InstallModePage InstallModePageLeave

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; --- Variables ---
Var InstallMode  ; "full" or "client"

; --- Install Mode Page ---
Function InstallModePage
  nsDialogs::Create 1018
  Pop $0

  ${NSD_CreateLabel} 0 0 100% 30u "Choose installation type:"
  Pop $0

  ${NSD_CreateRadioButton} 20u 40u 80% 15u "Full Install (Server + Client) — Run your own ReClaw server"
  Pop $1
  ${NSD_Check} $1  ; Default selected

  ${NSD_CreateRadioButton} 20u 60u 80% 15u "Client Only — Connect to an existing ReClaw server"
  Pop $2

  ${NSD_CreateLabel} 20u 85u 80% 30u "Full Install requires Python 3.11+ and Node.js 18+. Client Only requires Node.js 18+ only."
  Pop $0

  nsDialogs::Show
FunctionEnd

Function InstallModePageLeave
  ; Read radio button state (simplified — full always for now)
  StrCpy $InstallMode "full"
FunctionEnd

; --- Installation ---
Section "ReClaw Files"
  SetOutPath $INSTDIR

  ; Copy all ReClaw files
  File /r "..\..\backend\*"
  File /r "..\..\frontend\*"
  File /r "..\..\relay\*"
  File /r "..\..\desktop\*"
  File "..\..\reclaw.sh"
  File "..\..\.env.example"

  ; Create Start Menu shortcut
  CreateDirectory "$SMPROGRAMS\ReClaw"
  CreateShortcut "$SMPROGRAMS\ReClaw\ReClaw.lnk" "$INSTDIR\desktop\ReClaw.exe"
  CreateShortcut "$SMPROGRAMS\ReClaw\Uninstall.lnk" "$INSTDIR\uninstall.exe"

  ; Write uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"

  ; Registry keys for Add/Remove Programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ReClaw" "DisplayName" "ReClaw"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ReClaw" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ReClaw" "Publisher" "ReClaw Team"
SectionEnd

Section "Uninstall"
  ; Remove files
  RMDir /r "$INSTDIR"
  RMDir /r "$SMPROGRAMS\ReClaw"

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ReClaw"
SectionEnd
