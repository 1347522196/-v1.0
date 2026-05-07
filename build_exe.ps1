$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Local virtual environment not found. Please create .venv first."
}

python -m pip --python $venvPython install -r requirements-build.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --default-timeout 60
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install build dependencies."
}

& $venvPython -m PyInstaller --noconfirm AmazonHardwareLauncher.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

Write-Host ""
Write-Host "Build finished. Deliver this exe:" -ForegroundColor Green
Write-Host (Join-Path $projectRoot "dist\SellerSpriteLite.exe") -ForegroundColor Green
