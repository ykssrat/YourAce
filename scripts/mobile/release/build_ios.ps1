param(
    [string]$AppRoot = "scripts/mobile/react_native_app"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $AppRoot)) {
    throw "移动端项目目录不存在: $AppRoot"
}

Push-Location $AppRoot
try {
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
        throw "未检测到 npx，请先安装 Node.js 环境"
    }

    Write-Host "开始构建 iOS release..."
    npx react-native run-ios --configuration Release
    if ($LASTEXITCODE -ne 0) {
        throw "iOS 打包失败，退出码: $LASTEXITCODE"
    }

    Write-Host "iOS 打包完成。"
}
finally {
    Pop-Location
}
