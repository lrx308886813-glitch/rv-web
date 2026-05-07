$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MediaMtx = Join-Path $Dir "mediamtx.exe"

Get-Process mediamtx -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -eq $MediaMtx } |
  Stop-Process -Force

$sitePids = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique

foreach ($pidValue in $sitePids) {
  $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
  if ($process -and $process.ProcessName -match "python") {
    Stop-Process -Id $pidValue -Force
  }
}
