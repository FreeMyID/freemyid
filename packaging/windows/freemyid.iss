; Inno Setup script. Build after PyInstaller:
;   iscc /DAppVersion=0.1.0 packaging\windows\freemyid.iss
; Optional family installer: add /DFamilyBundle=C:\path\Mom.freemyid-profile
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{90CB7231-F487-4012-93B4-C1CE0AC4DF82}
AppName=Free My ID
AppVersion={#AppVersion}
AppPublisher=Free My ID
DefaultDirName={localappdata}\Programs\FreeMyID
DefaultGroupName=Free My ID
DisableProgramGroupPage=yes
DisableDirPage=yes
DisableReadyPage=yes
SetupIconFile=freemyid.ico
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=FreeMyIDSetup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Free My ID
UninstallDisplayIcon={app}\FreeMyID.exe
CloseApplications=yes

[Files]
Source: "freemyid.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\FreeMyID\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs
#ifdef FamilyBundle
; Pre-filled details for a family member. The app offers to import it on first launch; the
; person still reviews everything and gives their own permission.
Source: "{#FamilyBundle}"; DestDir: "{app}"; Flags: ignoreversion
#endif
#ifdef FamilyRegistry
; Private full broker list for a family build (iscc /DFamilyRegistry=path\registry.yaml).
; Never used for public releases. The app validates it like an update before using it.
Source: "{#FamilyRegistry}"; DestDir: "{app}"; DestName: "registry.yaml"; Flags: ignoreversion
#endif

[Icons]
Name: "{autoprograms}\Free My ID"; Filename: "{app}\FreeMyID.exe"; IconFilename: "{app}\freemyid.ico"
Name: "{autodesktop}\Free My ID"; Filename: "{app}\FreeMyID.exe"; IconFilename: "{app}\freemyid.ico"

[Run]
Filename: "{app}\FreeMyID.exe"; Description: "Start Free My ID now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; A family registry.yaml must not survive uninstall/reinstall.
Type: files; Name: "{app}\registry.yaml"

[UninstallRun]
; Remove the daily background task (per-user, no admin needed) before the files go away.
Filename: "{app}\freemyid-cli.exe"; Parameters: "schedule remove"; Flags: runhidden; RunOnceId: "RemoveFreeMyIDTask"

[Code]
// v0.1.0 still showed "Ready to Install" with DisableReadyPage=yes (VM walkthrough, Windows 11):
// skip it explicitly as well so older people see no extra "Install" step.
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = wpReady);
end;

// The 90e160a build still showed "Ready to Install" even with the skip above (VM re-check):
// press Install for the person as soon as that page appears.
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpReady then
    WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

function DataDir: String;
begin
  // Never read FREEMYID_HOME here: a stray value could point at a personal folder.
  Result := ExpandConstant('{userappdata}') + '\FreeMyID';
end;

function IsFreeMyIDData: Boolean;
begin
  Result := FileExists(DataDir + '\freemyid.db') or FileExists(DataDir + '\.freemyid-home');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  RC: Integer;
begin
  // usUninstall runs BEFORE files are removed, so freemyid-cli.exe still exists and can also
  // delete the encryption key and mailbox passwords from Windows Credential Manager.
  if CurUninstallStep = usUninstall then
  begin
    if IsFreeMyIDData then
      // SuppressibleMsgBox: a silent uninstall (/SUPPRESSMSGBOXES) answers IDNO = keep the data.
      // A plain MsgBox is never suppressed and would hang a silent uninstall forever.
      if SuppressibleMsgBox('Do you also want to delete the information Free My ID saved on this computer '
                + '(the people you added, reports and screenshots)?' + #13#10 + #13#10
                + 'Choose No if you might use Free My ID again.', mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES then
      begin
        Exec(ExpandConstant('{app}\freemyid-cli.exe'), 'wipe --yes', '', SW_HIDE, ewWaitUntilTerminated, RC);
        // Only remove what is verifiably Free My ID's own folder.
        if IsFreeMyIDData then
          DelTree(DataDir, True, True, True);
      end;
  end;
end;
