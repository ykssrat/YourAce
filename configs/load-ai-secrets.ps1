# 从 configs/secrets.local.json 读取密钥并写入当前会话的环境变量。
# 用法（在仓库根目录或任意目录）:
#   . D:\git_project\YourAce\configs\load-ai-secrets.ps1
# 若从 configs 目录执行:
#   . .\load-ai-secrets.ps1

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$secretsPath = Join-Path $here "secrets.local.json"

if (-not (Test-Path $secretsPath)) {
    Write-Host "未找到 $secretsPath" -ForegroundColor Yellow
    Write-Host "请复制 configs/secrets.example.json 为 configs/secrets.local.json 并填入 api_key。" -ForegroundColor Yellow
    exit 1
}

$raw = Get-Content -LiteralPath $secretsPath -Raw -Encoding UTF8
$cfg = $raw | ConvertFrom-Json

if (-not $cfg.deepseek) {
    Write-Error "secrets.local.json 缺少 deepseek 节点。"
}

$key = [string]$cfg.deepseek.api_key
if ([string]::IsNullOrWhiteSpace($key) -or $key -match "填入|your-key|YOUR_KEY|在此") {
    Write-Error "请在 secrets.local.json 的 deepseek.api_key 中填入真实 DeepSeek API Key。"
}

$base = [string]$cfg.deepseek.base_url
if ([string]::IsNullOrWhiteSpace($base)) {
    $base = "https://api.deepseek.com/v1"
}

$model = [string]$cfg.deepseek.model
if ([string]::IsNullOrWhiteSpace($model)) {
    $model = "deepseek-v4-pro"
}

# DeepSeek 使用 OpenAI 兼容协议：多数 CLI / SDK 用 OPENAI_* 指向自定义 Base URL。
$env:DEEPSEEK_API_KEY = $key
$env:OPENAI_API_KEY = $key
$env:OPENAI_BASE_URL = $base.TrimEnd("/")
$env:DEEPSEEK_BASE_URL = $base.TrimEnd("/")
$env:DEEPSEEK_MODEL = $model

Write-Host "已加载 DeepSeek 环境变量（当前 PowerShell 会话）:" -ForegroundColor Green
Write-Host "  DEEPSEEK_API_KEY / OPENAI_API_KEY = <hidden>"
Write-Host "  OPENAI_BASE_URL / DEEPSEEK_BASE_URL = $($env:OPENAI_BASE_URL)"
Write-Host "  DEEPSEEK_MODEL = $($env:DEEPSEEK_MODEL)"
Write-Host ""
Write-Host "Cursor：打开 Cursor Settings → Models / API Keys，启用 OpenAI API Override，Base URL 填 $($env:OPENAI_BASE_URL)，Key 与 secrets.local.json 中一致；模型名填 $($env:DEEPSEEK_MODEL)（或 deepseek-v4-flash）。" -ForegroundColor Cyan
