# TestCraft Goo Watchdog
# Ensures the Streamlit app and Cloudflare Tunnel are always running.
# Run this repeatedly via Task Scheduler (e.g. every 5 minutes + at startup).

$ErrorActionPreference = "SilentlyContinue"

$AppDir       = "C:\AI-Test"
$PythonExe    = "C:\AI-Test\venv\Scripts\python.exe"
$CloudflaredExe = "C:\AI-Test\tools\cloudflared.exe"
$AppLog       = "C:\AI-Test\logs\webapp.log"
$TunnelLog    = "C:\AI-Test\logs\tunnel.log"
$UrlFile      = "C:\AI-Test\current_url.txt"

New-Item -ItemType Directory -Force -Path "C:\AI-Test\logs" | Out-Null

# ---- Ensure Streamlit web app is running ----
$appListening = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue
if (-not $appListening) {
    Start-Process -FilePath $PythonExe `
        -ArgumentList "-m", "streamlit", "run", "app.py" `
        -WorkingDirectory $AppDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $AppLog `
        -RedirectStandardError "$AppLog.err"
    Start-Sleep -Seconds 8
}

# ---- Ensure Cloudflare Tunnel is running ----
$tunnelRunning = Get-Process cloudflared -ErrorAction SilentlyContinue
if (-not $tunnelRunning) {
    Start-Process -FilePath $CloudflaredExe `
        -ArgumentList "tunnel", "--url", "http://localhost:8501" `
        -WorkingDirectory $AppDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $TunnelLog `
        -RedirectStandardError "$TunnelLog.err"
    Start-Sleep -Seconds 10

    # Extract the freshly generated public URL and save it for reference
    $urlLine = Select-String -Path "$TunnelLog.err" -Pattern "https://.*trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($urlLine) {
        $url = ($urlLine.Matches[0].Value)
        Set-Content -Path $UrlFile -Value $url
    }
}
