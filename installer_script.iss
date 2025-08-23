; =========================
; GUI Scale Drawing Installer
; =========================

#define MyAppName       "GUI Scale Drawing"
#ifexist "VERSION"
  #define MyAppVersion  Trim(LoadStringFromFile("VERSION", "utf-8"))
#else
  #define MyAppVersion  "1.0.0"
#endif
#define MyAppPublisher  "Charles Leach, Jr."
#define MyAppExeName    "ScaleDrawing.exe"
#define ProjRoot        SourcePath
#define DistExe         ProjRoot + "\dist\" + MyAppExeName
#define AppIcon         ProjRoot + "\gui_icon.ico"
#define ReadmeFile      ProjRoot + "\README.md"

[Setup]
AppId={{9B3F8E84-8A7B-4D54-9F6C-23F7E7F4F1E2}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}

; Per-user install in a writable location (no admin/UAC)
DefaultDirName={userappdata}\{#MyAppName}
PrivilegesRequired=lowest

; Start menu folder
DefaultGroupName={#MyAppName}

; Output installer in the same folder as the script
OutputDir=.
OutputBaseFilename=setup_gui_scale_drawing_{#MyAppVersion}

; Use your icon in the installer UI
SetupIconFile={#AppIcon}
UninstallDisplayIcon={app}\{#MyAppExeName}

Compression=lzma
SolidCompression=yes
WizardStyle=modern
 ; WizardImageFile=compiler:WizModernImage-IS.bmp
 ; WizardSmallImageFile=compiler:WizModernSmallImage-IS.bmp

[Files]
; The app exe you just built with PyInstaller
Source: "{#DistExe}"; DestDir: "{app}"; Flags: ignoreversion
; Optional: include readme and icon in install dir
Source: "{#ReadmeFile}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppIcon}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\gui_icon.ico"
; Optional desktop shortcut (see [Tasks] below)
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\gui_icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
; Offer to launch the app after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

