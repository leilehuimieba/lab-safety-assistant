$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $RepoRoot ".env.web_demo"
$EnvTemplate = Join-Path $RepoRoot ".env.web_demo.example"
$RuntimeDir = Join-Path $RepoRoot "artifacts\local-web-demo"
$RuntimeFile = Join-Path $RuntimeDir "runtime.json"
$LaunchPyFile = Join-Path $RuntimeDir "launch_web_demo_local.py"
$LaunchEnvFile = Join-Path $RuntimeDir "launch_env.json"
$LogDir = Join-Path $RepoRoot "logs"
$LogFile = Join-Path $LogDir "web_demo_local.log"
$ErrFile = Join-Path $LogDir "web_demo_local.err.log"
$WebDemoDir = Join-Path $RepoRoot "web_demo"

function Read-EnvFile {
    param([string]$Path)
    $values = @{}
    foreach ($line in Get-Content -Path $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        $pair = $trimmed -split '=', 2
        if ($pair.Count -eq 2) {
            $values[$pair[0].Trim()] = $pair[1].Trim()
        }
    }
    return $values
}

function Wait-HttpReady {
    param([string]$Url, [int]$RetryCount = 25, [int]$SleepSeconds = 1)
    for ($i = 0; $i -lt $RetryCount; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        } catch {}
        Start-Sleep -Seconds $SleepSeconds
    }
    return $false
}

if (-not (Test-Path $EnvFile)) {
    if (-not (Test-Path $EnvTemplate)) {
        throw "Missing env template: $EnvTemplate"
    }
    Copy-Item -Path $EnvTemplate -Destination $EnvFile -Force
    Write-Host "[WARN] .env.web_demo was missing and has been created from template: $EnvFile"
    Write-Host "[WARN] Fill DIFY_APP_API_KEY or OPENAI_API_KEY before retrying."
    exit 1
}

$envMap = Read-EnvFile -Path $EnvFile
$demoPort = 8088
if ($envMap.ContainsKey('DEMO_PORT') -and $envMap['DEMO_PORT']) {
    $demoPort = [int]$envMap['DEMO_PORT']
}
$difyAppKey = [string]($envMap['DIFY_APP_API_KEY'])
$openaiApiKey = [string]($envMap['OPENAI_API_KEY'])

if ([string]::IsNullOrWhiteSpace($difyAppKey) -and [string]::IsNullOrWhiteSpace($openaiApiKey)) {
    Write-Host "[WARN] No DIFY_APP_API_KEY or OPENAI_API_KEY found in .env.web_demo."
    Write-Host "[WARN] Starting in structured fallback mode. Lab Q&A will still work, but agent mode and real Dify lane will be unavailable."
}

$existingConn = Get-NetTCPConnection -State Listen -LocalPort $demoPort -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existingConn) {
    $owner = Get-Process -Id $existingConn.OwningProcess -ErrorAction SilentlyContinue
    $ownerLabel = if ($owner) { "$($owner.ProcessName)($($owner.Id))" } else { "pid=$($existingConn.OwningProcess)" }
    throw "Port $demoPort is already occupied by $ownerLabel"
}

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
if (Test-Path $LogFile) { Remove-Item $LogFile -Force -ErrorAction SilentlyContinue }
if (Test-Path $ErrFile) { Remove-Item $ErrFile -Force -ErrorAction SilentlyContinue }

$envPayload = [ordered]@{
    DIFY_BASE_URL = [string]($envMap['DIFY_BASE_URL'])
    DIFY_APP_API_KEY = $difyAppKey
    DIFY_TIMEOUT = [string]($envMap['DIFY_TIMEOUT'])
    OPENAI_BASE_URL = [string]($envMap['OPENAI_BASE_URL'])
    OPENAI_API_KEY = $openaiApiKey
    OPENAI_MODEL = [string]($envMap['OPENAI_MODEL'])
    OPENAI_FALLBACK_MODELS = [string]($envMap['OPENAI_FALLBACK_MODELS'])
    OPENAI_TIMEOUT = [string]($envMap['OPENAI_TIMEOUT'])
    DEMO_PORT = [string]$demoPort
    WORKDIR = $WebDemoDir
}
$envPayload | ConvertTo-Json -Depth 4 | Set-Content -Path $LaunchEnvFile -Encoding UTF8

$pyLines = @(
    'import json, os, sys, uvicorn',
    'from pathlib import Path',
    'cfg = json.loads(Path(__file__).with_name("launch_env.json").read_text(encoding="utf-8-sig"))',
    'for key, value in cfg.items():',
    '    if key == "WORKDIR":',
    '        continue',
    '    os.environ[key] = str(value)',
    'os.chdir(cfg["WORKDIR"])',
    'sys.path.insert(0, str(Path(cfg["WORKDIR"]).parent))',
    'uvicorn.run("web_demo.app:app", host="127.0.0.1", port=int(cfg["DEMO_PORT"]))'
)
Set-Content -Path $LaunchPyFile -Value $pyLines -Encoding UTF8

$proc = Start-Process -FilePath "python" `
    -ArgumentList @($LaunchPyFile) `
    -WorkingDirectory $WebDemoDir `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $ErrFile `
    -PassThru `
    -WindowStyle Hidden

if (-not (Wait-HttpReady -Url "http://127.0.0.1:$demoPort/health" -RetryCount 25 -SleepSeconds 1)) {
    try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
    throw "Local web_demo failed to start. Check log: $LogFile ; err: $ErrFile"
}

$labLaneState = if ([string]::IsNullOrWhiteSpace($difyAppKey)) { "structured_fallback" } else { "dify_configured" }
$runtimeJson = @"
import json
import urllib.request
from pathlib import Path

with urllib.request.urlopen("http://127.0.0.1:$demoPort/api/meta", timeout=10) as resp:
    meta = json.loads(resp.read().decode("utf-8"))

runtime = {
    "started_at": "$(Get-Date -Format s)",
    "demo_port": $demoPort,
    "pid": $($proc.Id),
    "launch_file": r"$LaunchPyFile",
    "launch_env_file": r"$LaunchEnvFile",
    "log_file": r"$LogFile",
    "err_file": r"$ErrFile",
    "env_file": r"$EnvFile",
    "app_version": meta.get("app_version", ""),
    "acceptance_status": meta.get("acceptance_status", ""),
    "chat_lane_agent": meta.get("chat_lane_agent", ""),
    "chat_lane_lab": meta.get("chat_lane_lab", ""),
    "lab_lane_state": "$labLaneState",
    "runtime_model": meta.get("runtime_model", ""),
}

Path(r"$RuntimeFile").write_text(json.dumps(runtime, ensure_ascii=False, indent=4), encoding="utf-8")
print(json.dumps(runtime, ensure_ascii=False))
"@ | python -

$runtime = $runtimeJson | ConvertFrom-Json

Write-Host "[OK] Local web_demo started"
Write-Host "URL          : http://127.0.0.1:$demoPort"
Write-Host "Health       : http://127.0.0.1:$demoPort/health"
Write-Host "Chat lane    : $($runtime.chat_lane_lab)"
Write-Host "Lab mode     : $labLaneState"
Write-Host "Agent lane   : $($runtime.chat_lane_agent)"
Write-Host "Runtime model: $($runtime.runtime_model)"
Write-Host "Runtime      : $RuntimeFile"
Write-Host "Launch file  : $LaunchPyFile"
Write-Host "Launch env   : $LaunchEnvFile"
Write-Host "Log          : $LogFile"
Write-Host "Err Log      : $ErrFile"


