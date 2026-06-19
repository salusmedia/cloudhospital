# Stop the referral full stack (kill whatever listens on 8080/8101/8019).
foreach ($p in 8080, 8101, 8019) {
  try {
    (Get-NetTCPConnection -LocalPort $p -State Listen -EA SilentlyContinue).OwningProcess |
      ForEach-Object { Stop-Process -Id $_ -Force -EA SilentlyContinue; Write-Host "stopped port $p (PID $_)" }
  } catch {}
}
Write-Host "done."
