# Builds python_dist/ using Python embeddable and installs minimal deps.
# Run on Windows PowerShell.
param(
  [string]$PythonVersion = "3.10.11",
  [string]$DistDir = "python_dist",
  [switch]$UseUv = $true
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

# 4) Create site-packages and (prefer) uv to install deps
$py = Join-Path $DistDir "python.exe"
$pyHome = Split-Path $py -Parent
$site = Join-Path $pyHome "Lib/site-packages"
if (!(Test-Path $site)) { New-Item -ItemType Directory -Path $site | Out-Null }

function Install-With-Uv($target) {
  try {
    $hasUv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $hasUv) { return $false }
    Write-Host "Installing deps with uv into $target ..."
    # Prefer requirements.in to stay in sync with the repo
    $req = Join-Path $PWD 'requirements.in'
    if (Test-Path $req) {
      uv pip install -r $req --target "$target" --no-cache-dir --no-compile --prefer-binary --only-binary=:all:
    } else {
      # Minimal fallback set aligned with the app
      uv pip install chainlit openai python-dotenv tenacity fastapi uvicorn --target "$target" `
        --no-cache-dir --no-compile --prefer-binary --only-binary=:all:
    }
    return $true
  } catch {
    Write-Warning "uv installation failed: $_"
    return $false
  }
}

function Bootstrap-Pip-And-Install($pythonExe, $target) {
  # Embeddable Python lacks ensurepip; use pip.pyz to bootstrap
  $pipPyz = Join-Path $env:TEMP "pip.pyz"
  if (!(Test-Path $pipPyz)) {
    Write-Host "Downloading pip.pyz ..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/pip/pip.pyz" -OutFile $pipPyz
  }
  Write-Host "Bootstrapping pip into $target ..."
  & $pythonExe $pipPyz install --no-cache-dir --no-compile --target "$target" pip setuptools wheel
  Write-Host "Bootstrapped pip."
  # Use pip (from the embedded target) to install deps into target
  # Note: call the interpreter with -m pip and specify --target again
  & $pythonExe -m pip install --upgrade pip --no-cache-dir --prefer-binary --only-binary=:all:
  $req = Join-Path $PWD 'requirements.in'
  if (Test-Path $req) {
    & $pythonExe -m pip install --no-cache-dir --prefer-binary --only-binary=:all: --no-compile `
      -r $req --target "$target"
  } else {
    & $pythonExe -m pip install --no-cache-dir --prefer-binary --only-binary=:all: --no-compile `
      chainlit openai python-dotenv tenacity fastapi uvicorn --target "$target"
  }
}

# Try uv first (if requested); fallback to pip bootstrap
$installed = $false
if ($UseUv) {
  $installed = Install-With-Uv -target $site
}
if (-not $installed) {
  Bootstrap-Pip-And-Install -pythonExe $py -target $site
}

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
