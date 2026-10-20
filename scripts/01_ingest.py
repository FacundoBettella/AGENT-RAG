"""Script 01 — Ingestión de las 3 bases de conocimiento (HR, Tech, Finance).

Fuerza la construcción de cada agente de dominio, lo que dispara la
ingesta perezosa de su carpeta data/<domain>_docs/ hacia su propia
colección de Chroma si todavía está vacía (ver DomainAgent en
src/agents/base.py).

Uso:
    python scripts/01_ingest.py
"""

import io
import sys
from pathlib import Path

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents import finance_agent, hr_agent, tech_agent

AGENTS = {
    "HR": hr_agent.agent,
    "Tech": tech_agent.agent,
    "Finance": finance_agent.agent,
}


def main() -> None:
    for name, agent in AGENTS.items():
        count = agent.count()
        print(f"✓ {name} ({agent.config.collection_name}) → {count} chunks en Chroma")


if __name__ == "__main__":
    main()
