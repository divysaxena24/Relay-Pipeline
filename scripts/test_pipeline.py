
import json
from dotenv import load_dotenv

from app.retrieval.bm25_retriever import BM25Retriever
from app.providers.groq_client import GroqClient
from app.pipeline.research_pipeline import ResearchPipeline


def main():
    load_dotenv()

    with open("data/chunks.json", encoding="utf-8") as file:
        chunks = json.load(file)

    retriever = BM25Retriever(chunks)
    groq = GroqClient()

    pipeline = ResearchPipeline(
        retriever=retriever,
        groq_client=groq,
        top_k=5
    )

    questions = [
        "How does scaled dot-product attention work?",
        "What is the current NVIDIA stock price?"
    ]

    for question in questions:
        print("\n" + "=" * 65)
        print("QUESTION:", question)

        result = pipeline.run(question)

        print("\nSTATUS:", result["status"])
        print("\nANSWER:", result["answer"])
        print("\nEVIDENCE:", result.get("evidence_decision"))
        print("\nCITATIONS:")
        print("\nCITATION STATUS:", result.get("citation_status"))
        print("INVALID CITATIONS:", result.get("invalid_citations", []))

        for citation in result["citations"]:
            print(
                f"[{citation['source_id']}] "
                f"{citation['title']} | "
                f"arXiv:{citation['arxiv_id']} "
                f"v{citation['version']} | "
                f"Page {citation['page']}"
                
            )


if __name__ == "__main__":
    main()
