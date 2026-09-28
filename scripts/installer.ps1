# Installation de JISER sur un nouveau PC Windows (une seule fois).
# Prérequis : Git, Python 3.11 et Node.js 20 installés.
# Usage (depuis la racine du dépôt) :  powershell -ExecutionPolicy Bypass -File scripts\installer.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Write-Host "1/3 Environnement Python..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) { python -m venv .venv }
.venv\Scripts\python -m pip install --upgrade pip -q
.venv\Scripts\python -m pip install -r backend\requirements.txt -q

Write-Host "2/3 Interface (npm)..." -ForegroundColor Cyan
Set-Location frontend
npm install --silent
Set-Location $root

Write-Host "3/3 Vérifications..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Write-Host "ATTENTION : le fichier .env est absent. Copiez-le depuis le PC d'origine (clé USB ou message privé, jamais via GitHub)." -ForegroundColor Yellow
} else {
    Write-Host ".env présent." -ForegroundColor Green
}
.venv\Scripts\python -m pytest tests -q

Write-Host "Installation terminée. Lancez la démo avec : powershell -ExecutionPolicy Bypass -File scripts\demarrer.ps1" -ForegroundColor Green
