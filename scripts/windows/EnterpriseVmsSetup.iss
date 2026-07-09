#define MyAppName "Enterprise VMS"
#define MyAppPublisher "Enterprise VMS Project"
#ifndef MyAppVersion
  #define MyAppVersion "0.2.0"
#endif
#ifndef SourceDir
  #define SourceDir ".\windows-dist\EnterpriseVMS"
#endif
#ifndef OutputDir
  #define OutputDir ".\windows-dist\installer"
#endif

[Setup]
AppId={{6C30C5A5-E9D0-46AA-8B4A-BF287BE62532}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Enterprise VMS
DefaultGroupName=Enterprise VMS
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=EnterpriseVmsSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\bin\vms_client.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicons"; Description: "Create desktop shortcuts"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "{#SourceDir}\config\*"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "{#SourceDir}\scripts\*"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "{#SourceDir}\README-WINDOWS.txt"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\data"
Name: "{app}\logs"

[Icons]
Name: "{group}\Enterprise VMS Client"; Filename: "{app}\scripts\start-client.cmd"; WorkingDir: "{app}"
Name: "{group}\Enterprise VMS Server"; Filename: "{app}\scripts\start-server.cmd"; WorkingDir: "{app}"
Name: "{group}\Install Server Service"; Filename: "{app}\scripts\install-service.cmd"; WorkingDir: "{app}"
Name: "{group}\Uninstall Server Service"; Filename: "{app}\scripts\uninstall-service.cmd"; WorkingDir: "{app}"
Name: "{group}\Uninstall Enterprise VMS"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Enterprise VMS Client"; Filename: "{app}\scripts\start-client.cmd"; WorkingDir: "{app}"; Tasks: desktopicons
Name: "{autodesktop}\Enterprise VMS Server"; Filename: "{app}\scripts\start-server.cmd"; WorkingDir: "{app}"; Tasks: desktopicons

[Run]
Filename: "{app}\scripts\start-server.cmd"; Description: "Start Enterprise VMS Server now"; Flags: postinstall shellexec skipifsilent unchecked
Filename: "{app}\scripts\start-client.cmd"; Description: "Start Enterprise VMS Client now"; Flags: postinstall shellexec skipifsilent unchecked
