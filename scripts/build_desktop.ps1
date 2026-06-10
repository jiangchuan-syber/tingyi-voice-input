# Build Tingyi desktop app (PyInstaller onedir + models)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Version = python -c "from tingyi import __version__; print(__version__)"
$BuildDir = Join-Path $Root "build"
$DistApp = Join-Path $Root "dist\Tingyi"
$ReleaseDir = Join-Path $Root "dist\Tingyi-v$Version-desktop"
$ZipPath = Join-Path $Root "dist\Tingyi-v$Version-desktop.zip"

if (-not (Test-Path "$Root\models\sensevoice")) {
    Write-Error "models/ not found. Run: python -m tingyi --download-models"
}

pip install pyinstaller pystray Pillow keyboard pyperclip -q

if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }
if (Test-Path $DistApp) { Remove-Item $DistApp -Recurse -Force }

python -m PyInstaller --noconfirm "$Root\scripts\tingyi.spec"

if (-not (Test-Path "$DistApp\Tingyi.exe")) {
    Write-Error "PyInstaller failed: Tingyi.exe not found"
}

if (Test-Path $ReleaseDir) { Remove-Item $ReleaseDir -Recurse -Force }
New-Item -ItemType Directory -Path $ReleaseDir | Out-Null

Copy-Item "$DistApp\*" $ReleaseDir -Recurse -Force
Copy-Item "$Root\models" $ReleaseDir -Recurse -Force

@'
Tingyi Desktop

1. Double-click "Start Tingyi.bat" (or Tingyi.exe)
2. Click into WeChat / Cursor / any input field
3. Press F9, speak, pause ~1.2s
4. Text is pasted automatically

Tray icon: bottom-right taskbar. Right-click to quit.

Do NOT delete the models/ folder.
If hotkey fails, run as Administrator.

.env options (create in this folder):
  TINGYI_HOTKEY_RECORD=f9
  TINGYI_VAD_MIN_SILENCE_MS=1500
'@ | Set-Content (Join-Path $ReleaseDir "README.txt") -Encoding ascii

Copy-Item "$Root\.env.example" (Join-Path $ReleaseDir ".env.example") -Force

@'
@echo off
cd /d "%~dp0"
start "" "Tingyi.exe"
'@ | Set-Content (Join-Path $ReleaseDir "Start Tingyi.bat") -Encoding ascii

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $ReleaseDir -DestinationPath $ZipPath -CompressionLevel Optimal

$mb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Desktop package ready:"
Write-Host "  Folder: $ReleaseDir"
Write-Host "  Zip:    $ZipPath  ($mb MB)"
Write-Host ""
Write-Host "Run: Start Tingyi.bat  or  Tingyi.exe"
Write-Host "Hotkey: F9 (edit .env to change)"
