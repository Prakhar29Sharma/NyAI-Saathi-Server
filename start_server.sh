#!/bin/bash
cd /root/NyAI-Saathi-Server
source .venv/bin/activate
exec uvicorn app.main:app --host 0.0.0.0 --port 8000