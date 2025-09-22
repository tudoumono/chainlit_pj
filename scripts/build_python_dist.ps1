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
#   Embeddable Python uses e.g. python310._pth (note the leading underscore)
$pth = Get-ChildItem $DistDir -Filter "python*._pth" | Select-Object -First 1
if ($null -ne $pth) {
  (Get-Content $pth.FullName) | ForEach-Object { $_ -replace "^#import site$","import site" } | Set-Content $pth.FullName -Encoding UTF8
} else {
  Write-Warning "_pth file not found under $DistDir; site-packages may not be enabled."
}

# 4) Create site-packages and bootstrap pip for embeddable Python
$py = Join-Path $DistDir "python.exe"
$pyHome = Split-Path $py -Parent
$site = Join-Path $pyHome "Lib/site-packages"
if (!(Test-Path $site)) { New-Item -ItemType Directory -Path $site | Out-Null }

# Note: Windows embeddable Python doesn't include ensurepip/pip by design.
# Use pip's official zipapp (pip.pyz) to bootstrap into our site-packages.
$pipPyz = Join-Path $env:TEMP "pip.pyz"
if (!(Test-Path $pipPyz)) {
  Write-Host "Downloading pip.pyz ..."
  Invoke-WebRequest -Uri "https://bootstrap.pypa.io/pip/pip.pyz" -OutFile $pipPyz
}

Write-Host "Bootstrapping pip into $site ..."
& $py $pipPyz install --no-cache-dir --no-compile --target "$site" pip setuptools wheel
Write-Host "Bootstrapped pip."

# 5) Upgrade pip and install deps without cache/bytecode
#    - --no-cache-dir: avoid writing to user cache
#    - --prefer-binary/--only-binary: prefer wheels when available
#    - --no-compile: avoid creating .pyc at build time (we also set
#      PYTHONDONTWRITEBYTECODE at runtime from Electron)
& $py -m pip install --upgrade pip --no-cache-dir --prefer-binary --only-binary=:all:
& $py -m pip install --no-cache-dir --prefer-binary --only-binary=:all: --no-compile `
    chainlit fastapi uvicorn openai python-dotenv tenacity

# 6) Prune unnecessary files to reduce size
Write-Host "Pruning site-packages at $site ..."

function Remove-IfExists($path) { if (Test-Path $path) { Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue } }

# Remove pip and wheel (keep setuptools/pkg_resources, required by some deps like gevent)
Get-ChildItem -Path $site -Directory -Filter "pip*" -ErrorAction SilentlyContinue | ForEach-Object { Remove-IfExists $_.FullName }
Get-ChildItem -Path $site -Directory -Filter "wheel*" -ErrorAction SilentlyContinue | ForEach-Object { Remove-IfExists $_.FullName }

# Remove tests and __pycache__ from installed packages
Get-ChildItem -Path $site -Recurse -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -in @("tests","testing","__pycache__") } |
  ForEach-Object { Remove-IfExists $_.FullName }

# Remove stray *.pyc / *.pyo files
Get-ChildItem -Path $site -Recurse -Include *.pyc,*.pyo -File -ErrorAction SilentlyContinue |
  ForEach-Object { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }

# Optional: trim dist-info metadata for tooling we removed
Get-ChildItem -Path $site -Directory -Filter "pip-*.dist-info" -ErrorAction SilentlyContinue | ForEach-Object { Remove-IfExists $_.FullName }
Get-ChildItem -Path $site -Directory -Filter "wheel-*.dist-info" -ErrorAction SilentlyContinue | ForEach-Object { Remove-IfExists $_.FullName }

Write-Host "python_dist is ready: $DistDir"
