
import json
from pathlib import Path

from app.retrieval.chunking import chunk_pages


def main():
    pages_path = Path("data/pages.json")
    output_path = Path("data/chunks.json")

    with pages_path.open("r", encoding="utf-8") as file:
        pages = json.load(file)

    chunks = chunk_pages(
        pages,
        chunk_size=250,
        overlap=50,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(chunks, file, ensure_ascii=False, indent=2)

    print("\nChunking completed!")
    print(f"Input pages: {len(pages)}")
    print(f"Generated chunks: {len(chunks)}")
    print(f"Average words per chunk: "
          f"{sum(c['word_count'] for c in chunks) / len(chunks):.2f}")
    print(f"Saved to: {output_path}")

    print("\nChunks per paper:")
    for paper_id in sorted(set(c["paper_id"] for c in chunks)):
        count = sum(1 for c in chunks if c["paper_id"] == paper_id)
        print(f"{paper_id}: {count}")


if __name__ == "__main__":
    main()
