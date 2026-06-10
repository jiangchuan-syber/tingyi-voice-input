# 打包带模型的本地完整版
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Version = python -c "from tingyi import __version__; print(__version__)"
$OutDir = Join-Path $Root "dist\tingyi-voice-input-$Version-full"
$ZipPath = Join-Path $Root "dist\tingyi-voice-input-v$Version-full.zip"

if (-not (Test-Path "$Root\models\sensevoice")) {
    Write-Error "未找到 models/，请先运行: python -m tingyi --download-models"
}

if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutDir | Out-Null

$ExcludeDirs = @('.git', '.venv', 'venv', 'cache', 'recordings', 'dist', '.cursor', '.vscode', '.idea')

Get-ChildItem $Root -Force | ForEach-Object {
    if ($_.Name -in $ExcludeDirs) { return }
    if ($_.PSIsContainer) {
        Copy-Item $_.FullName (Join-Path $OutDir $_.Name) -Recurse -Force
    } elseif ($_.Name -ne '.env') {
        Copy-Item $_.FullName (Join-Path $OutDir $_.Name) -Force
    }
}

Get-ChildItem $OutDir -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force

Copy-Item "$Root\scripts\package_launchers\setup.bat" $OutDir -Force
Copy-Item "$Root\scripts\package_launchers\listen.bat" $OutDir -Force
Copy-Item "$Root\scripts\package_docs\完整版说明.txt" $OutDir -Force

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $OutDir -DestinationPath $ZipPath -CompressionLevel Optimal

$folderMb = [math]::Round(((Get-ChildItem $OutDir -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 2)
$zipMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
Write-Host ""
Write-Host "完成"
Write-Host "  文件夹: $OutDir  ($folderMb MB)"
Write-Host "  压缩包: $ZipPath  ($zipMb MB)"
