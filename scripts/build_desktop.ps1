# Build Tingyi desktop app (PyInstaller onedir + models + dictionary + .env)
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

if (-not (Test-Path "$Root\.env")) {
    Write-Host "Syncing DeepSeek from work-experience project..."
    python -c @"
from pathlib import Path

def load_env(p):
    d = {}
    if not p.exists():
        return d
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        d[k.strip()] = v.strip()
    return d

src = load_env(Path(r'e:/工作经历挖掘/.env'))
lines = [
    '# Tingyi desktop config',
    'TINGYI_ASR_MODE=local',
    'TINGYI_HOTKEY_RECORD=f9',
    'TINGYI_AUTO_PASTE=true',
    'TINGYI_VAD_MIN_SILENCE_MS=500',
    'TINGYI_DICTIONARY_ENABLED=true',
    'TINGYI_RULE_REFINE_ENABLED=true',
    'TINGYI_REFINE_ASYNC=true',
    '',
]
for key in ('DEEPSEEK_API_KEY', 'DEEPSEEK_API_BASE', 'DEEPSEEK_MODEL'):
    if src.get(key):
        lines.append(f'{key}={src[key]}')
Path(r'$Root\.env').write_text('\n'.join(lines) + '\n', encoding='utf-8')
"@
}

pip install pyinstaller pystray Pillow keyboard pyperclip openai python-dotenv -q

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
Copy-Item "$Root\dictionary.json" $ReleaseDir -Force
Copy-Item "$Root\.env" $ReleaseDir -Force
Copy-Item "$Root\.env.example" $ReleaseDir -Force

@'
Tingyi Desktop v0.3.2

1. Double-click "Start Tingyi.bat" (or Tingyi.exe)
2. Click into WeChat / Cursor / any input field
3. Press F9 to START continuous listening (press F9 again to stop)
4. Speak; pause ~0.5s between sentences -> auto transcribe & paste
5. Dictionary + rule polish applied; DeepSeek refine runs in background if .env has key

Tray: bottom-right taskbar. Right-click -> Quit.

Do NOT delete models/ folder.
.env already includes DeepSeek API (synced from local setup). Edit to change hotkey/VAD.

.env options:
  TINGYI_HOTKEY_RECORD=f9
  TINGYI_VAD_MIN_SILENCE_MS=500
  DEEPSEEK_API_KEY=...
  TINGYI_REFINE_ASYNC=true
'@ | Set-Content (Join-Path $ReleaseDir "README.txt") -Encoding utf8

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
