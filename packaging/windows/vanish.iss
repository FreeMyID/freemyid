; Inno Setup script. Build after PyInstaller:
;   iscc /DAppVersion=0.1.0 packaging\windows\vanish.iss
; Optional family installer: add /DFamilyBundle=C:\path\Mom.vanish-profile
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{6B1E5C0A-3F52-4C55-9C1B-5A4B0E7A21D1}
AppName=Vanish
AppVersion={#AppVersion}
AppPublisher=Vanish
DefaultDirName={localappdata}\Programs\Vanish
DefaultGroupName=Vanish
DisableProgramGroupPage=yes
DisableDirPage=yes
DisableReadyPage=yes
SetupIconFile=vanish.ico
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=VanishSetup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Vanish
UninstallDisplayIcon={app}\Vanish.exe
CloseApplications=yes

[Files]
Source: "vanish.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\Vanish\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs
#ifdef FamilyBundle
; Pre-filled details for a family member. The app offers to import it on first launch; the
; person still reviews everything and gives their own permission.
Source: "{#FamilyBundle}"; DestDir: "{app}"; Flags: ignoreversion
#endif

[Icons]
Name: "{autoprograms}\Vanish"; Filename: "{app}\Vanish.exe"; IconFilename: "{app}\vanish.ico"
Name: "{autodesktop}\Vanish"; Filename: "{app}\Vanish.exe"; IconFilename: "{app}\vanish.ico"

[Run]
Filename: "{app}\Vanish.exe"; Description: "Start Vanish now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove the daily background task (per-user, no admin needed) before the files go away.
Filename: "{app}\vanish-cli.exe"; Parameters: "schedule remove"; Flags: runhidden; RunOnceId: "RemoveVanishTask"

[Code]
function DataDir: String;
begin
  // Never read VANISH_HOME here: a stray value could point at a personal folder.
  Result := ExpandConstant('{userappdata}') + '\Vanish';
end;

function IsVanishData: Boolean;
begin
  Result := FileExists(DataDir + '\vanish.db') or FileExists(DataDir + '\.vanish-home');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  RC: Integer;
begin
  // usUninstall runs BEFORE files are removed, so vanish-cli.exe still exists and can also
  // delete the encryption key and mailbox passwords from Windows Credential Manager.
  if CurUninstallStep = usUninstall then
  begin
    if IsVanishData then
      // SuppressibleMsgBox: a silent uninstall (/SUPPRESSMSGBOXES) answers IDNO = keep the data.
      // A plain MsgBox is never suppressed and would hang a silent uninstall forever.
      if SuppressibleMsgBox('Do you also want to delete the information Vanish saved on this computer '
                + '(the people you added, reports and screenshots)?' + #13#10 + #13#10
                + 'Choose No if you might use Vanish again.', mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES then
      begin
        Exec(ExpandConstant('{app}\vanish-cli.exe'), 'wipe --yes', '', SW_HIDE, ewWaitUntilTerminated, RC);
        // Only remove what is verifiably Vanish's own folder.
        if IsVanishData then
          DelTree(DataDir, True, True, True);
      end;
  end;
end;
