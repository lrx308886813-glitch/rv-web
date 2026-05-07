$ErrorActionPreference = "Stop"

$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Dir

$MediaMtx = Join-Path $Dir "mediamtx.exe"
$MediaMtxConfig = Join-Path $Dir "mediamtx.yml"
$SiteServer = Join-Path $Dir "camera_site_server.py"
$SiteUrl = "http://localhost:8080/index.html"

if (-not (Test-Path -LiteralPath $MediaMtx)) {
  throw "mediamtx.exe is missing in $Dir"
}

$existingMediaMtx = Get-Process mediamtx -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -eq $MediaMtx }

if (-not $existingMediaMtx) {
  Start-Process `
    -FilePath $MediaMtx `
    -ArgumentList @($MediaMtxConfig) `
    -WorkingDirectory $Dir `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $Dir "mediamtx.out.log") `
    -RedirectStandardError (Join-Path $Dir "mediamtx.err.log")
}

$siteHealthy = $false
try {
  $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/api/status" -TimeoutSec 2
  $siteHealthy = ($response.StatusCode -eq 200)
} catch {
  $siteHealthy = $false
}

if (-not $siteHealthy) {
  $sitePids = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($pidValue in $sitePids) {
    $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($process -and $process.ProcessName -match "python") {
      Stop-Process -Id $pidValue -Force
    }
  }

  $python = (Get-Command python.exe -ErrorAction Stop).Source
  Start-Process `
    -FilePath $python `
    -ArgumentList @($SiteServer) `
    -WorkingDirectory $Dir `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $Dir "site.out.log") `
    -RedirectStandardError (Join-Path $Dir "site.err.log")
}

Start-Sleep -Seconds 2
Start-Process $SiteUrl
