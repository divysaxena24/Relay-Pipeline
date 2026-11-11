
import re
from typing import Any


def split_into_chunks(
    text: str,
    chunk_size: int = 250,
    overlap: int = 50,
) -> list[str]:
    """
    Split text into overlapping word-based chunks.

    chunk_size: maximum words per chunk
    overlap: words repeated between consecutive chunks
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    words = re.findall(r"\S+", text)

    if not words:
        return []

    chunks = []
    step = chunk_size - overlap

    for start in range(0, len(words), step):
        chunk_words = words[start:start + chunk_size]

        if not chunk_words:
            break

        chunks.append(" ".join(chunk_words))

        if start + chunk_size >= len(words):
            break

    return chunks


def chunk_pages(
    pages: list[dict[str, Any]],
    chunk_size: int = 250,
    overlap: int = 50,
) -> list[dict[str, Any]]:
    all_chunks = []

    for page_data in pages:
        text = page_data["text"]

        page_chunks = split_into_chunks(
            text,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk_index, chunk_text in enumerate(page_chunks):
            all_chunks.append({
                "chunk_id": (
                    f"{page_data['paper_id']}"
                    f"_p{page_data['page']}"
                    f"_c{chunk_index}"
                ),
                "paper_id": page_data["paper_id"],
                "title": page_data["title"],
                "arxiv_id": page_data["arxiv_id"],
                "version": page_data["version"],
                "page": page_data["page"],
                "chunk_index": chunk_index,
                "word_count": len(chunk_text.split()),
                "text": chunk_text,
            })

    return all_chunks
