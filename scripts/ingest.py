
import json
from pathlib import Path

from app.retrieval.ingestion import ingest_all


def main():
    pages = ingest_all()

    output_path = Path("data/pages.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(pages, file, ensure_ascii=False, indent=2)

    print("\nIngestion completed!")
    print(f"Total extracted pages: {len(pages)}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
