[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$ServerHost = "175.178.90.193",
    [string]$User = "root",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\labsafe_new.pem",
    [string]$RemoteReleaseDir = "/root/lab-safe-assistant-github-release",
    [string]$RemoteStageDir = "/root/deploy_staging",
    [string]$Commitish = "HEAD",
    [switch]$AllowDirty,
    [switch]$ReseedDemoData,
    [switch]$SkipRestart,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $FilePath $($Arguments -join ' ')"
    }
}

function New-TempDirectory {
    $path = Join-Path ([System.IO.Path]::GetTempPath()) ("lab_safe_deploy_" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    return $path
}

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
if (-not (Test-Path $RepoRoot)) {
    throw "Repo root not found: $RepoRoot"
}
if (-not (Test-Path $KeyPath)) {
    throw "SSH key not found: $KeyPath"
}

$RepoRoot = (Resolve-Path $RepoRoot).Path
Set-Location $RepoRoot

Write-Step "Checking local repository state"
$gitStatus = git status --porcelain
if ($LASTEXITCODE -ne 0) {
    throw "git status failed."
}
if ($gitStatus -and -not $AllowDirty) {
    throw "Working tree is dirty. Commit or stash changes, or rerun with -AllowDirty if you intentionally want to deploy the current HEAD only."
}

$commitSha = (git rev-parse $Commitish).Trim()
if (-not $commitSha) {
    throw "Unable to resolve commitish: $Commitish"
}
Write-Host "Commit: $commitSha"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tempDir = New-TempDirectory
$archivePath = Join-Path $tempDir "lab-safe-release_$timestamp.zip"
$remoteArchive = "$RemoteStageDir/lab-safe-release_$timestamp.zip"
$remoteRunner = "$RemoteStageDir/run_release_$timestamp.sh"
$sshTarget = "$User@$ServerHost"
$sshBaseArgs = @("-i", $KeyPath, "-o", "StrictHostKeyChecking=accept-new", "-o", "ServerAliveInterval=30")
$scpBaseArgs = @("-i", $KeyPath, "-o", "StrictHostKeyChecking=accept-new")

try {
    Write-Step "Creating release archive from git archive"
    Invoke-External -FilePath "git" -Arguments @("archive", "--format=zip", "--output=$archivePath", $commitSha)

    Write-Step "Preparing remote staging directory"
    Invoke-External -FilePath "ssh" -Arguments ($sshBaseArgs + @($sshTarget, "mkdir -p $RemoteStageDir"))

    Write-Step "Uploading release archive"
    Invoke-External -FilePath "scp" -Arguments ($scpBaseArgs + @($archivePath, "${sshTarget}:$remoteArchive"))

    $remoteScriptTemplate = @'
#!/usr/bin/env bash
set -euo pipefail

RELEASE_DIR='__REMOTE_RELEASE_DIR__'
STAGE_DIR='__REMOTE_STAGE_DIR__'
ARCHIVE_PATH='__REMOTE_ARCHIVE__'
STAMP='__STAMP__'
RESEED_DEMO_DATA='__RESEED__'
SKIP_RESTART='__SKIP_RESTART__'
SKIP_SMOKE='__SKIP_SMOKE__'

INCOMING_DIR="${RELEASE_DIR}.__incoming_${STAMP}"
BACKUP_DIR="${RELEASE_DIR}_backup_${STAMP}"

echo "[remote] release dir: ${RELEASE_DIR}"
echo "[remote] incoming dir: ${INCOMING_DIR}"
echo "[remote] backup dir: ${BACKUP_DIR}"

rm -rf "${INCOMING_DIR}"
mkdir -p "${INCOMING_DIR}"

python3 - "${ARCHIVE_PATH}" "${INCOMING_DIR}" <<'PY'
from pathlib import Path
from zipfile import ZipFile
import sys

archive = Path(sys.argv[1])
target = Path(sys.argv[2])
if not archive.exists():
    raise SystemExit(f"archive missing: {archive}")
with ZipFile(archive) as zf:
    zf.extractall(target)
PY

preserve_file() {
  local relative_path="$1"
  if [[ -f "${RELEASE_DIR}/${relative_path}" ]]; then
    mkdir -p "$(dirname "${INCOMING_DIR}/${relative_path}")"
    cp -a "${RELEASE_DIR}/${relative_path}" "${INCOMING_DIR}/${relative_path}"
  fi
}

preserve_dir() {
  local relative_path="$1"
  if [[ -d "${RELEASE_DIR}/${relative_path}" ]]; then
    mkdir -p "$(dirname "${INCOMING_DIR}/${relative_path}")"
    cp -a "${RELEASE_DIR}/${relative_path}" "${INCOMING_DIR}/${relative_path}"
  fi
}

preserve_file ".env.web_demo"
preserve_dir ".venv"
preserve_dir ".venv-web-demo"
preserve_dir "logs"
preserve_dir "run"

for sub_dir in checklists training incidents low_confidence_followups ops; do
  preserve_dir "artifacts/${sub_dir}"
done

if [[ -d "${RELEASE_DIR}" ]]; then
  mv "${RELEASE_DIR}" "${BACKUP_DIR}"
fi
mv "${INCOMING_DIR}" "${RELEASE_DIR}"
rm -f "${ARCHIVE_PATH}"

cd "${RELEASE_DIR}"

find deploy scripts -type f -name '*.sh' -exec sed -i 's/\r$//' {} +
find deploy scripts -type f -name '*.sh' -exec chmod +x {} +

if [[ -x ".venv/bin/pip" ]]; then
  .venv/bin/pip install -r web_demo/requirements.txt >/dev/null 2>&1 || true
fi

if [[ "${RESEED_DEMO_DATA}" == "1" ]]; then
  echo "[remote] reseeding fixed demo data"
  python3 scripts/demo/seed_fixed_demo_data.py
fi

if [[ "${SKIP_RESTART}" != "1" ]]; then
  echo "[remote] restarting web demo"
  bash deploy/stop_web_demo.sh || true
  bash deploy/start_web_demo.sh
else
  echo "[remote] skip restart requested"
fi

if [[ "${SKIP_SMOKE}" != "1" ]]; then
  echo "[remote] running smoke check"
  bash deploy/server_smoke_check.sh --repo-root "${RELEASE_DIR}"
else
  echo "[remote] skip smoke requested"
fi

echo "[remote] deployment complete"
echo "[remote] current release: ${RELEASE_DIR}"
echo "[remote] backup kept at: ${BACKUP_DIR}"
'@

    $remoteScript = $remoteScriptTemplate.Replace("__REMOTE_RELEASE_DIR__", $RemoteReleaseDir)
    $remoteScript = $remoteScript.Replace("__REMOTE_STAGE_DIR__", $RemoteStageDir)
    $remoteScript = $remoteScript.Replace("__REMOTE_ARCHIVE__", $remoteArchive)
    $remoteScript = $remoteScript.Replace("__STAMP__", $timestamp)
    $remoteScript = $remoteScript.Replace("__RESEED__", [string]([int][bool]$ReseedDemoData))
    $remoteScript = $remoteScript.Replace("__SKIP_RESTART__", [string]([int][bool]$SkipRestart))
    $remoteScript = $remoteScript.Replace("__SKIP_SMOKE__", [string]([int][bool]$SkipSmoke))

    $localRunner = Join-Path $tempDir "run_release.sh"
    Set-Content -Path $localRunner -Value $remoteScript -Encoding Ascii

    Write-Step "Uploading remote release runner"
    Invoke-External -FilePath "scp" -Arguments ($scpBaseArgs + @($localRunner, "${sshTarget}:$remoteRunner"))

    Write-Step "Executing remote deployment"
    Invoke-External -FilePath "ssh" -Arguments ($sshBaseArgs + @($sshTarget, "bash $remoteRunner"))

    Write-Step "Cleaning remote runner"
    Invoke-External -FilePath "ssh" -Arguments ($sshBaseArgs + @($sshTarget, "rm -f $remoteRunner"))

    Write-Step "Remote deployment finished"
    Write-Host "Release dir : $RemoteReleaseDir"
    Write-Host "Archive sent: $remoteArchive"
    Write-Host "Runner used : $remoteRunner"
    Write-Host "Smoke check : $(if ($SkipSmoke) { 'skipped' } else { 'executed' })"
}
finally {
    if (Test-Path $tempDir) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force
    }
}
