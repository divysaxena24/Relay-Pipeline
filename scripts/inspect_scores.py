
import json

from app.retrieval.bm25_retriever import BM25Retriever


def main():
    with open("data/chunks.json", encoding="utf-8") as file:
        chunks = json.load(file)

    retriever = BM25Retriever(chunks)

    questions = [
        ("ANSWERABLE", "How does scaled dot-product attention work?"),
        ("ANSWERABLE", "How does Moshi enable real-time speech dialogue?"),
        ("UNANSWERABLE", "What is the current NVIDIA stock price?"),
        ("UNANSWERABLE", "What is the best Java programming course?"),
    ]

    for category, question in questions:
        results = retriever.search(question, top_k=3)

        print(f"\n[{category}] {question}")

        if not results:
            print("No results found.")
            continue

        for result in results:
            print(
                f"Score: {result['score']:.4f} | "
                f"Paper: {result['paper_id']} | "
                f"Page: {result['page']}"
            )


if __name__ == "__main__":
    main()
