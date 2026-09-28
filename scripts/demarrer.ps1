# Lance JISER pour la démo : le backend (port 8000) et l'interface (port 5173), chacun dans sa fenêtre.
# Usage (depuis la racine du dépôt) :  powershell -ExecutionPolicy Bypass -File scripts\demarrer.ps1

$root = Split-Path $PSScriptRoot -Parent

# libère les ports si une ancienne instance tourne encore
foreach ($port in 8000, 5173) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$root'; Write-Host 'JISER · backend (ne pas fermer)' -ForegroundColor Cyan; .venv\Scripts\python -m uvicorn app.main:app --app-dir backend --port 8000"
Start-Sleep -Seconds 3
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$root\frontend'; Write-Host 'JISER · interface (ne pas fermer)' -ForegroundColor Cyan; npm run dev -- --host"
Start-Sleep -Seconds 6

$wifi = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi*" -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress
Write-Host ""
Write-Host "JISER est lancé :" -ForegroundColor Green
Write-Host "  PC          : http://localhost:5173"
Write-Host "  Admin       : http://localhost:5173/plateforme"
if ($wifi) { Write-Host "  Téléphone   : http://$($wifi):5173   (même Wi-Fi que le PC)" }
Start-Process "http://localhost:5173"
