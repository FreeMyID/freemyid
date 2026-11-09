; Inno Setup script. Build after PyInstaller:
;   iscc /DAppVersion=0.3.0 packaging\windows\freemyid.iss
; Optional family installer: add /DFamilyBundle=C:\path\Mom.freemyid-profile
#ifndef AppVersion
  #define AppVersion "0.3.0"
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

[Messages]
; "Every wait has a reason": the first start of the app shows nothing for several seconds
; (files unpack, Windows scans the new program). Say so BEFORE the click so nobody double-clicks
; again or thinks it failed. Unverified on Windows (CI-only build).
FinishedLabel=Free My ID is installed.%n%nThe first time it opens, it can take up to a minute. A small "Free My ID is starting" box shows while you wait. That is normal. Please wait, and do not click it again; the window will show up by itself.
FinishedLabelNoIcons=Free My ID is installed. The first time it opens, the window can take up to a minute to appear. That is normal; please wait.

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
Filename: "{app}\FreeMyID.exe"; Description: "Open Free My ID now (the first time can take up to a minute)"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; A family registry.yaml must not survive uninstall/reinstall.
Type: files; Name: "{app}\registry.yaml"

[UninstallRun]
; Remove the daily background task (per-user, no admin needed) before the files go away.
Filename: "{app}\freemyid-cli.exe"; Parameters: "schedule remove"; Flags: runhidden; RunOnceId: "RemoveFreeMyIDTask"

[Code]
// "Ready to Install" stays on purpose (the disable-ready-page setting was removed: Inno showed the page anyway, VM
// checks 2026-11-07). A double-click never installs without one deliberate click. Site copy says "Click Install".

// A running Free My ID locks its own files, so a silent uninstall used to leave FreeMyID.exe and
// _internal behind. Close it first (the window and any scheduled run; /T takes the child processes too).
procedure CloseRunningApp;
var
  RC: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM FreeMyID.exe', '', SW_HIDE, ewWaitUntilTerminated, RC);
  Sleep(1500);   // let Windows release the file locks
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
    CloseRunningApp;
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
