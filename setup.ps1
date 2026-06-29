$ErrorActionPreference = "Stop"

Write-Host "Setting up Frontend..."
cd AI-Research-Copilot-Frontend
npm install

Write-Host "Setting up Backend..."
cd ..\AI-Research-Copilot-Backend
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
.venv\Scripts\activate
pip install -r requirements.txt

Write-Host "Setup complete. To start the servers:"
Write-Host "Frontend: cd AI-Research-Copilot-Frontend; npm run dev"
Write-Host "Backend: cd AI-Research-Copilot-Backend; .\.venv\Scripts\activate; uvicorn main:app --reload --host 0.0.0.0 --port 8000"
