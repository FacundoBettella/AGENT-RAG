"""Script 01 — Ingestión de documentos FAQ.

Carga todos los .txt de data/, los chunkea y los guarda en ChromaDB.
Ejecutar una vez antes de hacer consultas.

Uso:
    python scripts/01_ingest.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from factory import build_faq_bundle

DATA_DIR = Path(__file__).parent.parent / "data"


def main() -> None:
    bundle = build_faq_bundle()
    txt_files = list(DATA_DIR.glob("*.txt"))

    if not txt_files:
        print(f"No se encontraron archivos .txt en {DATA_DIR}")
        return

    total_chunks = 0
    for file in txt_files:
        chunks = bundle.indexer.index(str(file))
        print(f"✓ {file.name} → {chunks} chunks indexados")
        total_chunks += chunks

    print(f"\nTotal: {total_chunks} chunks guardados en ChromaDB")
    print(f"Colección tiene {bundle.indexer._store.count()} chunks en total")


if __name__ == "__main__":
    main()
