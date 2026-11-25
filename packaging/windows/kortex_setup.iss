; Script de Inno Setup para generar un unico KortexNexus-Setup-v2.0.0.exe
; Compilar con Inno Setup 6: iscc packaging\windows\kortex_setup.iss

#define MyAppName "Kortex Nexus"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "David Santiago Ortiz"
#define MyAppExeName "KortexNexus.exe"

[Setup]
AppId={{8F5E3B1D-9A77-4E21-9A2A-7B11C3B92000}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\KortexNexus
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\release
OutputBaseFilename=KortexNexus-Setup-v{#MyAppVersion}
SetupIconFile=..\..\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"
Name: "autostart"; Description: "Iniciar Kortex Daemon ligero con Windows"; GroupDescription: "Optimización automática:"

[Files]
Source: "..\..\dist\KortexNexus\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Kortex Daemon (Ligero)"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--daemon"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "KortexNexus"; ValueData: """{app}\{#MyAppExeName}"" --daemon"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
