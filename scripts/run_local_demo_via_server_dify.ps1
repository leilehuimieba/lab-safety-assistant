param(
    [string]$ServerHost = "175.178.90.193",
    [string]$ServerUser = "root",
    [string]$SshKeyPath = "C:\Users\33371\.ssh\labsafe_new.pem",
    [string]$RemoteEnvPath = "/root/lab-safe-assistant-github-release/.env.web_demo",
    [int]$TunnelPort = 18080,
    [int]$DemoPort = 8090,
    [string]$PythonExe = "python",
    [string]$DifyAppKey = ""
)

$ErrorActionPreference = "Stop"

function Test-CommandExists {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-PortOwner {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) {
        return $null
    }

    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($proc) {
        return "$($proc.ProcessName)($($proc.Id))"
    }
    return "pid=$($conn.OwningProcess)"
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$RetryCount = 20,
        [int]$SleepSeconds = 1
    )

    for ($i = 0; $i -lt $RetryCount; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        } catch {
        }
        Start-Sleep -Seconds $SleepSeconds
    }

    return $false
}

if (-not (Test-CommandExists "ssh")) {
    throw "ssh is not available in PATH."
}

if (-not (Test-CommandExists $PythonExe)) {
    throw "Python executable '$PythonExe' is not available in PATH."
}

if (-not (Test-Path $SshKeyPath)) {
    throw "SSH key not found: $SshKeyPath"
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$WebDemoDir = Join-Path $RepoRoot "web_demo"
$RuntimeDir = Join-Path $RepoRoot "artifacts\local-dify-bridge"
$RuntimeFile = Join-Path $RuntimeDir "runtime.json"

if (-not (Test-Path $WebDemoDir)) {
    throw "web_demo directory not found: $WebDemoDir"
}

$demoOwner = Get-PortOwner -Port $DemoPort
if ($demoOwner) {
    throw "DemoPort $DemoPort is already in use by $demoOwner. Use another port or stop the existing process."
}

$tunnelOwner = Get-PortOwner -Port $TunnelPort
if ($tunnelOwner) {
    throw "TunnelPort $TunnelPort is already in use by $tunnelOwner. Use another tunnel port or stop the existing process."
}

$sshTarget = "$ServerUser@$ServerHost"

if (-not $DifyAppKey) {
    $remoteCmd = @"
python3 - <<'PY'
from pathlib import Path
path = Path(r'$RemoteEnvPath')
text = path.read_text(encoding='utf-8')
for line in text.splitlines():
    if line.startswith('DIFY_APP_API_KEY='):
        print(line.split('=', 1)[1].strip())
        break
PY
"@
    $DifyAppKey = (& ssh -i $SshKeyPath -o StrictHostKeyChecking=no $sshTarget $remoteCmd | Select-Object -First 1).Trim()
}

if (-not $DifyAppKey) {
    throw "DIFY_APP_API_KEY is empty. Pass -DifyAppKey manually or ensure the remote env file contains it."
}

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$tunnelProc = Start-Process -FilePath "ssh" `
    -ArgumentList @(
        "-i", $SshKeyPath,
        "-o", "StrictHostKeyChecking=no",
        "-N",
        "-L", "127.0.0.1:${TunnelPort}:127.0.0.1:8080",
        $sshTarget
    ) `
    -PassThru `
    -WindowStyle Hidden

if (-not (Wait-HttpReady -Url "http://127.0.0.1:$TunnelPort" -RetryCount 15 -SleepSeconds 1)) {
    try { Stop-Process -Id $tunnelProc.Id -Force -ErrorAction SilentlyContinue } catch {}
    throw "SSH tunnel is not ready on http://127.0.0.1:$TunnelPort"
}

$demoCommand = @"
`$env:DIFY_BASE_URL='http://127.0.0.1:$TunnelPort'
`$env:DIFY_APP_API_KEY='$DifyAppKey'
`$env:DIFY_TIMEOUT='120'
`$env:DEMO_PORT='$DemoPort'
$PythonExe -m uvicorn web_demo.app:app --host 127.0.0.1 --port $DemoPort
"@

$demoProc = Start-Process -FilePath "powershell" `
    -ArgumentList @("-NoLogo", "-NoProfile", "-Command", $demoCommand) `
    -WorkingDirectory $WebDemoDir `
    -PassThru `
    -WindowStyle Hidden

if (-not (Wait-HttpReady -Url "http://127.0.0.1:$DemoPort/health" -RetryCount 20 -SleepSeconds 1)) {
    try { Stop-Process -Id $demoProc.Id -Force -ErrorAction SilentlyContinue } catch {}
    try { Stop-Process -Id $tunnelProc.Id -Force -ErrorAction SilentlyContinue } catch {}
    throw "Local demo is not ready on http://127.0.0.1:$DemoPort/health"
}

$meta = Invoke-RestMethod -Uri "http://127.0.0.1:$DemoPort/api/meta" -Method Get -TimeoutSec 15

$runtime = [ordered]@{
    started_at = (Get-Date).ToString("s")
    server_host = $ServerHost
    server_user = $ServerUser
    remote_env_path = $RemoteEnvPath
    tunnel_port = $TunnelPort
    demo_port = $DemoPort
    tunnel_pid = $tunnelProc.Id
    demo_pid = $demoProc.Id
}
$runtime | ConvertTo-Json -Depth 4 | Set-Content -Path $RuntimeFile -Encoding UTF8

Write-Host "[OK] Local Dify bridge is ready."
Write-Host "Demo URL   : http://127.0.0.1:$DemoPort"
Write-Host "Health URL : http://127.0.0.1:$DemoPort/health"
Write-Host "Tunnel URL : http://127.0.0.1:$TunnelPort"
Write-Host "Chat lane  : $($meta.chat_lane_lab)"
Write-Host "Runtime    : $RuntimeFile"
Write-Host ""
Write-Host "Stop command:"
Write-Host "powershell -ExecutionPolicy Bypass -File scripts/stop_local_demo_via_server_dify.ps1"
