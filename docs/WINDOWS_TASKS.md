# Windows-Only Task List and Steps

This file lists tasks that must be performed on Windows, with step-by-step instructions.

## 1) Build `python_dist/` (Windows)
- Run PowerShell as user (no admin required) and execute:
  - `./scripts/build_python_dist.ps1`
- The script will:
  - Download Python embeddable ZIP (3.10+)
  - Expand to `python_dist/`
  - Create `pythonXX._pth` and add site-packages path
  - Install minimal wheels into `python_dist/Lib/site-packages` (chainlit, fastapi, uvicorn, openai, python-dotenv, etc.)

## 2) Package with electron-builder (Windows)
- `npm run build:win`
- Verify artifacts under `dist/`

## 3) Smoke test packaged app
- Launch the app
- Confirm ports per `.env` (`CHAINLIT_PORT`, `ELECTRON_API_PORT`)
- Confirm logs in `<UserData>/logs` and UI → Settings → System Logs

## 4) Optional: Code Signing
- Configure electron-builder signing (not required for internal testing)
- Add certs/secrets via GitHub Actions or local environment if needed
