#!/bin/sh
# Linux/macOS launcher. Windows: run `python run_all.py` (PowerShell: Start-Process python run_all.py -WindowStyle Hidden).
cd "$(dirname "$0")" && exec python3 run_all.py
