$ErrorActionPreference = "Stop"
if (!(Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$PWD'; .\.venv\Scripts\Activate.ps1; python scripts/run_backend.py"
Set-Location frontend
if (!(Test-Path node_modules)) { npm install }
npm run dev
