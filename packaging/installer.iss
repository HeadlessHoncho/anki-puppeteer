#define MyAppName "Anki Puppeteer"
#define MyAppVersion "0.9.1-rc1"
#define MyAppPublisher "Daniel G."
#define MyAppURL "https://github.com/HeadlessHoncho/anki-puppeteer"
#define MyAppExeName "AnkiPuppeteer.exe"

[Setup]
AppId={{B8E31F4A-7C2D-4E9A-91B5-6D3F8A2C1E47}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\AnkiPuppeteer
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
InfoAfterFile=after-install.txt
OutputDir=..\dist
OutputBaseFilename=AnkiPuppeteer-0.9.1-rc1-setup
SetupIconFile=..\assets\anki-puppeteer.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=no
RestartIfNeededByRun=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\AnkiPuppeteer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config.example.toml"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Open Anki and review cards by voice"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "{code:GetSetupArgs}"; StatusMsg: "Installing speech tools (needs internet unless you pointed at a local model)..."; Flags: waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "Start {#MyAppName}"; Flags: nowait postinstall skipifsilent unchecked

[Code]
var
  ModelPage: TInputOptionWizardPage;
  ModelPathPage: TInputFileWizardPage;

function CmdModel: String;
begin
  Result := Trim(ExpandConstant('{param:MODEL}'));
end;

procedure InitializeWizard;
begin
  ModelPage := CreateInputOptionPage(wpSelectDir,
    'Speech model', 'Choose a local Whisper speech model.',
    'Anki Puppeteer transcribes on this PC. Models are not inside this installer.' + #13#10 + #13#10 +
    'Download uses about 75 MB plus a small whisper.cpp CPU package. Pointing at an existing ggml-*.bin skips the model download.',
    True, False);
  ModelPage.Add('Download ggml-tiny.en.bin (~75 MB) now');
  ModelPage.Add('Use an existing local Whisper model (ggml-*.bin)');
  ModelPage.SelectedValueIndex := 0;

  ModelPathPage := CreateInputFilePage(ModelPage.ID,
    'Existing speech model', 'Point at a ggml-*.bin file already on this PC.',
    'Typical names: ggml-tiny.en.bin, ggml-base.en.bin, ggml-small.en.bin, ggml-large-v3.bin.');
  ModelPathPage.Add('Model file:', 'Whisper models (ggml-*.bin)|ggml-*.bin;*.bin|All files|*.*', '.bin');

  if CmdModel <> '' then
  begin
    ModelPage.SelectedValueIndex := 1;
    ModelPathPage.Values[0] := CmdModel;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if WizardSilent then
  begin
    if (PageID = ModelPage.ID) or (PageID = ModelPathPage.ID) then
      Result := True;
    Exit;
  end;
  if PageID = ModelPathPage.ID then
    Result := ModelPage.SelectedValueIndex <> 1;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Chosen: String;
begin
  Result := True;
  if CurPageID = ModelPathPage.ID then
  begin
    Chosen := Trim(ModelPathPage.Values[0]);
    if (Chosen = '') or (not FileExists(Chosen)) then
    begin
      MsgBox('Choose an existing ggml-*.bin speech model, or go back and download tiny.en.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function GetSetupArgs(Param: String): String;
var
  Model: String;
begin
  Model := CmdModel;
  if (Model = '') and Assigned(ModelPage) and (ModelPage.SelectedValueIndex = 1) then
    Model := Trim(ModelPathPage.Values[0]);
  if Model <> '' then
    Result := '--setup --model "' + Model + '"'
  else
    Result := '--setup';
end;
