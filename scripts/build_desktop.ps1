# Build Tingyi desktop app (PyInstaller onedir + models + dictionary + .env + shortcuts)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Version = python -c "from tingyi import __version__; print(__version__)"
$BuildDir = Join-Path $Root "build"
$DistApp = Join-Path $Root "dist\Tingyi"
$ReleaseDir = Join-Path $Root "dist\Tingyi-v$Version-desktop"
$ZipPath = Join-Path $Root "dist\Tingyi-v$Version-desktop.zip"
$ExePath = Join-Path $ReleaseDir "Tingyi.exe"

function New-TingyiShortcut {
    param(
        [string]$ShortcutPath,
        [string]$TargetExe,
        [string]$WorkingDir,
        [string]$Description = "听译 - 语音转文字输入 (F9)"
    )
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($ShortcutPath)
    $link.TargetPath = $TargetExe
    $link.WorkingDirectory = $WorkingDir
    $link.Description = $Description
    $link.IconLocation = "$TargetExe,0"
    $link.Save()
}

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
    'TINGYI_VAD_MIN_SILENCE_MS=800',
    'TINGYI_VAD_HANGOVER_MS=300',
    'TINGYI_VAD_SPEECH_PAD_MS=450',
    'TINGYI_REFINE_MODEL=deepseek-chat',
    'TINGYI_PASTE_RESTORE_CLIPBOARD=false',
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

# 程序目录内快捷方式（双击启动，勿删 models/）
$AppShortcut = Join-Path $ReleaseDir "听译.lnk"
New-TingyiShortcut -ShortcutPath $AppShortcut -TargetExe $ExePath -WorkingDir $ReleaseDir

@'
听译 Tingyi Desktop v{0}

【推荐启动】
  双击「听译.lnk」或 Tingyi.exe
  （也可双击「创建桌面快捷方式.bat」把图标放到桌面）

【使用】
  1. 在 Cursor / 微信等输入框点一下光标
  2. 按 F9 开启持续监听（再按 F9 关闭）
  3. 说完停顿约 1.1 秒，自动识别并粘贴

【托盘】任务栏右下角图标，右键可「打开日志」「退出」

【日志】logs\tingyi.log（排查识别/粘贴问题）

【注意】勿删 models/ 文件夹；热键无效可管理员运行

【配置】编辑本目录 .env：
  TINGYI_HOTKEY_RECORD=f9
  TINGYI_VAD_MIN_SILENCE_MS=800
  TINGYI_PASTE_RESTORE_CLIPBOARD=false
  TINGYI_LOG_LEVEL=DEBUG
'@ -f $Version | Set-Content (Join-Path $ReleaseDir "README.txt") -Encoding utf8

@'
@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "Tingyi.exe"
'@ | Set-Content (Join-Path $ReleaseDir "启动听译.bat") -Encoding utf8

@'
@echo off
chcp 65001 >nul
set "TARGET=%~dp0Tingyi.exe"
set "WORKDIR=%~dp0"
set "LINK=%USERPROFILE%\Desktop\听译.lnk"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = New-Object -ComObject WScript.Shell; $l = $s.CreateShortcut('%LINK%'); $l.TargetPath = '%TARGET%'; $l.WorkingDirectory = '%WORKDIR%'; $l.Description = '听译 - 语音转文字 (F9)'; $l.IconLocation = '%TARGET%,0'; $l.Save()"
echo.
echo 已在桌面创建快捷方式：%LINK%
echo 双击桌面「听译」图标即可启动。
pause
'@ | Set-Content (Join-Path $ReleaseDir "创建桌面快捷方式.bat") -Encoding utf8

# 打包时自动在用户桌面创建快捷方式
$DesktopLink = Join-Path ([Environment]::GetFolderPath("Desktop")) "听译.lnk"
New-TingyiShortcut -ShortcutPath $DesktopLink -TargetExe $ExePath -WorkingDir $ReleaseDir
Write-Host "Desktop shortcut: $DesktopLink"

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $ReleaseDir -DestinationPath $ZipPath -CompressionLevel Optimal

$mb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Desktop package ready:"
Write-Host "  Folder:   $ReleaseDir"
Write-Host "  Shortcut: $ReleaseDir\听译.lnk"
Write-Host "  Desktop:  $DesktopLink"
Write-Host "  Zip:      $ZipPath  ($mb MB)"
Write-Host ""
Write-Host "Double-click desktop shortcut '听译' or run 听译.lnk in the folder."
