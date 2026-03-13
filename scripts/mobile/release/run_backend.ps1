param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv/Scripts/python.exe")) {
    throw "未找到 Python 虚拟环境，请先初始化 .venv"
}

Write-Host "启动后端服务: $Host`:$Port"
.venv/Scripts/python.exe -m uvicorn scripts.api.server:app --host $Host --port $Port
