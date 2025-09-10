# Windows Packaging Guide (Option B)

This document describes how to build the Windows distributable with embedded Python (`python_dist/`) and Electron.

Important: Perform Windows-specific steps on a Windows machine after cloning the repository.

## Overview
- Python backend is spawned by Electron Main.
- Ports are configurable via `.env`: `CHAINLIT_PORT` (default 8000) and `ELECTRON_API_PORT` (default 8001).
- Logs are written under `<UserData>/logs` and exposed in the UI.

## Prerequisites (Windows)
- Node.js 18+ (x64)
- Python 3.10+ (for development); for distribution use the embeddable package
- Git, 7-Zip or PowerShell (for extracting archives)

## Steps
1. Clone the repository
   - `git clone <your repo>`
   - `cd chainlit_pj`
2. Install dependencies (dev)
   - `npm i`
   - `uv pip install -r requirements.in` (or `pip install -r requirements.in`)
3. Prepare `.env`
   - Copy `.env.example` to `.env`
   - Set `OPENAI_API_KEY`, `CHAINLIT_AUTH_SECRET`, `DEFAULT_MODEL`, and optionally the ports `CHAINLIT_PORT`, `ELECTRON_API_PORT`.
4. Create `python_dist/` (embedded Python)
   - See `scripts/build_python_dist.ps1` and run it in PowerShell.
   - It creates `python_dist/` with `python.exe` and required site-packages.
5. Package
   - `npm run build:win` (electron-builder)
   - Output artifacts in `dist/`

## Verification
- Run the packaged app and confirm:
  - First launch generates `<UserData>/.env` if absent
  - Settings tab loads; “Open Chat” navigates to Chainlit (top-level)
  - Logs available via “Open Log Folder” and “System Logs”
  - Health check shows both servers healthy

## Troubleshooting
- Port conflicts → adjust ports in `.env` and retry
- Missing packages → run `uv pip install -r requirements.in` and repackage
- OpenAI errors → verify API key and default model
