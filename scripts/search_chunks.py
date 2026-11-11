
import json
from pathlib import Path

from app.retrieval.bm25_retriever import BM25Retriever


def load_chunks():
    path = Path("data/chunks.json")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main():
    chunks = load_chunks()

    retriever = BM25Retriever(chunks)

    while True:
        query = input("\nEnter your question (or 'exit'): ").strip()

        if query.lower() == "exit":
            break

        try:
            results = retriever.search(query, top_k=5)

            if not results:
                print("\nNo relevant passages found.")
                continue

            print(f"\nTop {len(results)} results:")

            for rank, result in enumerate(results, start=1):
                print("\n" + "=" * 70)
                print(f"Rank: {rank}")
                print(f"Score: {result['score']}")
                print(f"Paper: {result['title']}")
                print(f"arXiv: {result['arxiv_id']}")
                print(f"Version: {result['version']}")
                print(f"Page: {result['page']}")
                print(f"Chunk: {result['chunk_id']}")
                print("\nPassage:")
                print(result["text"][:1000])

            print("\n" + "=" * 70)

        except ValueError as error:
            print(f"Invalid query: {error}")


if __name__ == "__main__":
    main()
