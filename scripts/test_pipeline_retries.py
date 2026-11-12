
import json

from pathlib import Path

from app.retrieval.bm25_retriever import BM25Retriever
from app.pipeline.research_pipeline import ResearchPipeline
from standin.model import StandInModel, StandInError


class FlakyProvider:
    """Fails once in each stage, then delegates to the stand-in."""

    def __init__(self):
        self.model = StandInModel(latency_ms=0)
        self.evidence_calls = 0
        self.generation_calls = 0

    def check_evidence(self, question, context):
        self.evidence_calls += 1

        if self.evidence_calls == 1:
            raise StandInError("Simulated temporary evidence failure")

        return self.model.check_evidence(question, context)

    def generate(self, question, context=""):
        self.generation_calls += 1

        if self.generation_calls == 1:
            raise StandInError("Simulated temporary generation failure")

        return self.model.generate(question, context)


def main():
    # Load the existing retrieval chunks.
    chunks_path = Path("data/chunks.json")

    with chunks_path.open("r", encoding="utf-8") as file:
        chunks = json.load(file)

    retriever = BM25Retriever(chunks)
    provider = FlakyProvider()

    pipeline = ResearchPipeline(
        retriever=retriever,
        groq_client=provider
    )

    result = pipeline.run(
        "How does scaled dot-product attention work?"
    )

    print("\nSTATUS:", result["status"])
    print("RETRY METRICS:", result.get("retry_metrics"))
    print("EVIDENCE CALLS:", provider.evidence_calls)
    print("GENERATION CALLS:", provider.generation_calls)

    assert result["status"] == "answered"
    assert result["retry_metrics"]["evidence_retries"] == 1
    assert result["retry_metrics"]["generation_retries"] == 1
    assert provider.evidence_calls == 2
    assert provider.generation_calls == 2

    print("\nALL PIPELINE RETRY TESTS PASSED.")


if __name__ == "__main__":
    main()
