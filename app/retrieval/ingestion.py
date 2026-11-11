
import fitz
from pathlib import Path
from typing import Any

PAPER_METADATA = {
    "attention_v7.pdf": {
        "paper_id": "attention",
        "title": "Attention Is All You Need",
        "version": 7,
        "arxiv_id": "1706.03762",
    },
    "moshi_v1.pdf": {
        "paper_id": "moshi",
        "title": "Moshi: a speech-text foundation model for real-time dialogue",
        "version": 1,
        "arxiv_id": "2410.00037",
    },
    "dynamic_chunking_v2.pdf": {
        "paper_id": "dynamic_chunking",
        "title": "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling",
        "version": 2,
        "arxiv_id": "2507.07955",
    },
}


def extract_pdf(pdf_path: Path) -> list[dict[str, Any]]:
    metadata = PAPER_METADATA.get(pdf_path.name)

    if metadata is None:
        raise ValueError(f"Unknown paper: {pdf_path.name}")

    pages = []

    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            if not text:
                continue

            pages.append({
                **metadata,
                "page": page_number,
                "text": text,
            })

    return pages


def ingest_all(papers_dir: str = "papers") -> list[dict]:
    papers_path = Path(papers_dir)
    all_pages = []

    for filename in PAPER_METADATA:
        pdf_path = papers_path / filename

        if not pdf_path.exists():
            raise FileNotFoundError(f"Paper not found: {pdf_path}")

        pages = extract_pdf(pdf_path)
        all_pages.extend(pages)

        print(f"Extracted {len(pages)} pages from {filename}")

    return all_pages
