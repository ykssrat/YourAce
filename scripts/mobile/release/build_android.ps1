param(
    [string]$AppRoot = "scripts/mobile/react_native_app"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $AppRoot)) {
    throw "App root not found: $AppRoot"
}

Push-Location $AppRoot
try {
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
        throw "npx not found. Please install Node.js first."
    }

    Write-Host "Start Android release build..."
    npx react-native run-android --mode release
    if ($LASTEXITCODE -ne 0) {
        throw "Android build failed, exit code: $LASTEXITCODE"
    }

    Write-Host "Android build finished."
}
finally {
    Pop-Location
}
