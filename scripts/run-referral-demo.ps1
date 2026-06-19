# Launch the "referral" full stack (frontend + gateway + scenario-019 + platform-auth).
# Keep this file ASCII-only: Windows PowerShell 5.1 reads .ps1 as the system codepage
# (GBK on zh-CN) and a non-ASCII char breaks parsing. Chinese notes live in the README.
#
# Prereqs: (1) DB up: docker compose -f infra/docker/compose.dev.yml up -d
#          (2) deps synced: uv sync   (run in repo root)
# Usage:   powershell -ExecutionPolicy Bypass -File scripts\run-referral-demo.ps1
# Then open http://127.0.0.1:8080  (login: doctor_card / 123456)

$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

# v2ray system proxy hijacks localhost; disable proxy for local calls.
$env:HTTP_PROXY = ""; $env:HTTPS_PROXY = ""; $env:http_proxy = ""; $env:https_proxy = ""
$env:NO_PROXY = "localhost,127.0.0.1"

$secret = "local-dev-secret"
$env:PLATFORM_AUTH_JWT_SECRET = $secret
$env:GATEWAY_JWT_SECRET = $secret
$env:GATEWAY_USE_LOCALHOST = "true"
$env:GATEWAY_WEB_ROOT = Join-Path $root "apps\portal"
$env:SCENARIO_019_DATABASE_URL = "postgresql+psycopg://dev:dev@localhost:5432/hospital"
$env:PLATFORM_PATIENT_DATABASE_URL = "postgresql+psycopg://dev:dev@localhost:5432/hospital"
$env:PLATFORM_PATIENT_PII_KEY = "dev-only-pii-key-change-me"
$env:PLATFORM_ARCHIVE_DATABASE_URL = "postgresql+psycopg://dev:dev@localhost:5432/hospital"

foreach ($p in 8101, 8019, 8006, 8002, 8102, 8104, 8105, 8106, 8107, 8080) {
  try { (Get-NetTCPConnection -LocalPort $p -State Listen -EA SilentlyContinue).OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -EA SilentlyContinue } } catch {}
}

# Backends run detached; the gateway runs in the FOREGROUND so this script stays
# alive as the long-lived server process (preview tracks it / Ctrl+C stops everything).
function Start-Bg($dir, $port) {
  Start-Process -FilePath $py -WindowStyle Hidden -WorkingDirectory $dir `
    -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--port', "$port")
}
Start-Bg (Join-Path $root "services\platform-auth") 8101
Start-Bg (Join-Path $root "services\scenario-019-backend") 8019
Start-Bg (Join-Path $root "services\scenario-006-backend") 8006
Start-Bg (Join-Path $root "services\scenario-002-backend") 8002
Start-Bg (Join-Path $root "services\platform-patient") 8102
Start-Bg (Join-Path $root "services\platform-archive") 8105
Start-Bg (Join-Path $root "services\platform-iot") 8106
Start-Bg (Join-Path $root "services\platform-file") 8104
Start-Bg (Join-Path $root "services\platform-consent") 8107

foreach ($u in 'http://127.0.0.1:8101/health', 'http://127.0.0.1:8019/health', 'http://127.0.0.1:8006/health', 'http://127.0.0.1:8002/health', 'http://127.0.0.1:8102/health', 'http://127.0.0.1:8105/health', 'http://127.0.0.1:8106/health', 'http://127.0.0.1:8104/health', 'http://127.0.0.1:8107/health') {
  for ($i = 0; $i -lt 50; $i++) { try { Invoke-RestMethod $u -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Milliseconds 400 } }
}

Write-Host "Referral stack -> http://127.0.0.1:8080  (login: doctor_card / 123456)"
Set-Location (Join-Path $root "services\gateway")
& $py -m uvicorn app.main:app --port 8080
