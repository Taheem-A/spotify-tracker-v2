$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

function Get-SupportedPython {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($version in @("3.13", "3.12", "3.11")) {
            & py "-$version" -c "import sys; print(sys.executable)" *> $null
            if ($LASTEXITCODE -eq 0) {
                return @("py", "-$version")
            }
        }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        $version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($version -in @("3.11", "3.12", "3.13")) {
            return @("python")
        }
    }

    throw "Tracker V2 requires Python 3.11, 3.12, or 3.13. Install a supported Python version and try again."
}

$pythonCommand = Get-SupportedPython

if (!(Test-Path .venv)) {
    if ($pythonCommand.Count -eq 2) {
        & $pythonCommand[0] $pythonCommand[1] -m venv .venv
    } else {
        & $pythonCommand[0] -m venv .venv
    }
}

& .\.venv\Scripts\Activate.ps1

$venvVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($venvVersion -notin @("3.11", "3.12", "3.13")) {
    throw ".venv uses Python $venvVersion. Delete .venv and run start.ps1 again so Tracker can create a supported environment."
}

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if (!(Test-Path .env) -and (Test-Path .env.example)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example. Add SPOTIFY_CLIENT_ID to .env for live Spotify integration." -ForegroundColor Yellow
}

if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js 20+ / npm is required for the frontend. Install Node.js and try again."
}

Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$PSScriptRoot'; .\.venv\Scripts\Activate.ps1; python scripts/run_backend.py"

Set-Location frontend
if (!(Test-Path node_modules)) { npm install }
npm run dev
