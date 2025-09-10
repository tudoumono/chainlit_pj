# Builds python_dist/ using Python embeddable and installs minimal deps.
# Run on Windows PowerShell.
param(
  [string]$PythonVersion = "3.10.11",
  [string]$DistDir = "python_dist"
)

$ErrorActionPreference = 'Stop'

# 1) Download Python embeddable
$base = "https://www.python.org/ftp/python/$PythonVersion/"
$zip = "python-$PythonVersion-embed-amd64.zip"
$uri = "$base$zip"
$zipPath = Join-Path $PWD $zip
if (!(Test-Path $zipPath)) {
  Write-Host "Downloading $uri ..."
  Invoke-WebRequest -Uri $uri -OutFile $zipPath
}

# 2) Extract to python_dist
if (Test-Path $DistDir) { Remove-Item $DistDir -Recurse -Force }
Expand-Archive -Path $zipPath -DestinationPath $DistDir

# 3) Enable site-packages (edit _pth)
$pth = Get-ChildItem $DistDir -Filter "python*.pth" | Select-Object -First 1
if ($null -ne $pth) {
  (Get-Content $pth.FullName) | ForEach-Object { $_ -replace "^#import site$","import site" } | Set-Content $pth.FullName -Encoding UTF8
}

# 4) Create site-packages and install minimal wheels via pip bootstrap
$py = Join-Path $DistDir "python.exe"
& $py - << 'PY'
import ensurepip, sys
ensurepip.bootstrap()
print('Bootstrapped pip:', sys.version)
PY

# 5) Upgrade pip and install deps
& $py -m pip install --upgrade pip
& $py -m pip install chainlit fastapi uvicorn openai python-dotenv tenacity

Write-Host "python_dist is ready: $DistDir"
