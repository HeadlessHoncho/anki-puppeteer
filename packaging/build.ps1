# Build AnkiPuppeteer-0.9.1-rc1-setup.exe
# Does not ship speech models. The installer downloads them (or uses --model).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

Write-Host "Python: $Py"
& $Py -m pip install -U pip pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install pyinstaller failed" }

Write-Host "Freezing onedir exe..."
& $Py -m PyInstaller --noconfirm --clean (Join-Path $Root "packaging\anki-puppeteer.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$Exe = Join-Path $Root "dist\AnkiPuppeteer\AnkiPuppeteer.exe"
if (-not (Test-Path $Exe)) { throw "Missing $Exe" }

function Find-ISCC {
    $candidates = @(
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 7\ISCC.exe"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    $where = Get-Command iscc -ErrorAction SilentlyContinue
    if ($where) { return $where.Source }
    return $null
}

$Iscc = Find-ISCC
if (-not $Iscc) {
    Write-Host "Inno Setup not found; installing a per-user copy..."
    $inst = Join-Path $env:TEMP "innosetup-6.7.3.exe"
    $url = "https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe"
    Invoke-WebRequest -Uri $url -OutFile $inst -UseBasicParsing
    $dest = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6"
    Start-Process -FilePath $inst -ArgumentList "/VERYSILENT", "/NORESTART", "/CURRENTUSER", "/DIR=`"$dest`"" -Wait
    $Iscc = Find-ISCC
}
if (-not $Iscc) { throw "ISCC.exe not found after Inno Setup install" }
Write-Host "ISCC: $Iscc"

& $Iscc (Join-Path $Root "packaging\installer.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compile failed" }

$Setup = Join-Path $Root "dist\AnkiPuppeteer-0.9.1-rc1-setup.exe"
if (-not (Test-Path $Setup)) { throw "Missing $Setup" }
$item = Get-Item $Setup
Write-Host ("Installer: {0} ({1:N1} MB)" -f $item.FullName, ($item.Length / 1MB))
