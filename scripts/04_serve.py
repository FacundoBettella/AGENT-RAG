"""Script 04 — Levanta la API REST del FAQ Chatbot.

Uso:
    python scripts/04_serve.py
    python scripts/04_serve.py --port 8080

La API queda disponible en http://localhost:8000
Documentación interactiva: http://localhost:8000/docs
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "m2project.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
