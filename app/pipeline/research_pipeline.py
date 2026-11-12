
from typing import Any
import re
from app.control.request_controller import RequestController
from app.retrieval.bm25_retriever import BM25Retriever
from app.providers.base import ModelProvider
from app.control.retry import call_with_retries


class ResearchPipeline:
    def __init__(
        self,
        retriever: BM25Retriever,
        groq_client: ModelProvider,
        top_k: int = 5
    ):
        self.retriever = retriever
        self.groq = groq_client
        self.top_k = top_k
        self.request_controller = RequestController(
            max_requests=25,
            window_seconds=60,
            max_concurrent=3,
            max_retries=2
        )

    def run(self, question: str) -> dict[str, Any]:
        if not question.strip():
            raise ValueError("Question cannot be empty.")

        # STEP 1: Retrieve relevant passages.
        passages = self.retriever.search(
            question,
            top_k=self.top_k
        )

        if not passages:
            return {
                "status": "refused",
                "reason": "No relevant passages found.",
                "answer": (
                    "I could not find relevant information "
                    "in the available research papers."
                ),
                "citations": [],
                "retrieved_count": 0,
                "retry_metrics": {
                    "evidence_retries": 0,
                    "generation_retries": 0
                }
            }

        # Build context with source identifiers.
        context_parts = []
        citations = []

        for index, passage in enumerate(passages, start=1):
            source_id = f"S{index}"

            citation = {
                "source_id": source_id,
                "title": passage["title"],
                "arxiv_id": passage["arxiv_id"],
                "version": passage["version"],
                "page": passage["page"]
            }

            citations.append(citation)

            context_parts.append(
                f"""
[{source_id}]
Paper: {passage['title']}
arXiv: {passage['arxiv_id']}
Version: {passage['version']}
Page: {passage['page']}

Passage:
{passage['text']}
"""
            )

        context = "\n".join(context_parts)

        # STEP 2: Check evidence with retry support.
        try:
            evidence, evidence_retries = self.request_controller.execute(
                self.groq.check_evidence,
                question,
                context
            )
        except Exception as error:
            return {
                "status": "error",
                "reason": f"Evidence checking failed: {type(error).__name__}",
                "answer": "I could not verify the available evidence. Please try again.",
                "citations": [],
                "retrieved_count": len(passages),
                "retry_metrics": {
                    "evidence_retries": 2,
                    "generation_retries": 0
                }
            }

        # STEP 3: Branch based on evidence.
        if not evidence["sufficient"]:
            return {
                "status": "refused",
                "reason": "Retrieved passages lack sufficient evidence.",
                "answer": (
                    "I cannot answer this reliably using the "
                    "available research papers."
                ),
                "citations": [],
                "retrieved_count": len(passages),
                "evidence_decision": evidence["decision"],
                "retry_metrics": {
                    "evidence_retries": evidence_retries,
                    "generation_retries": 0
                }
            }

        # STEP 4: Generate an answer with retry support.
        try:
            answer, generation_retries = self.request_controller.execute(
                self.groq.generate,
                question=question,
                context=context
            )
        except Exception as error:
            return {
                "status": "error",
                "reason": f"Answer generation failed: {type(error).__name__}",
                "answer": "I could not complete a reliable answer. Please try again.",
                "citations": [],
                "retrieved_count": len(passages),
                "evidence_decision": evidence["decision"],
                "retry_metrics": {
                    "evidence_retries": evidence_retries,
                    "generation_retries": 2
                }
            }

        if (
            not answer["answer"].strip()
            or answer.get("finish_reason") == "length"
        ):
            return {
                "status": "error",
                "reason": "Answer generation was incomplete.",
                "answer": "I could not complete a reliable answer. Please try again.",
                "citations": [],
                "retrieved_count": len(passages),
                "evidence_decision": evidence["decision"],
                "retry_metrics": {
                    "evidence_retries": evidence_retries,
                    "generation_retries": generation_retries
                }
            }

        # STEP 5: Validate source references.
        mentioned_ids = set(
            re.findall(r"\bS\d+\b", answer["answer"])
        )

        valid_ids = {
            citation["source_id"]
            for citation in citations
        }

        invalid_ids = mentioned_ids - valid_ids

        used_citations = [
            citation
            for citation in citations
            if citation["source_id"] in mentioned_ids
        ]

        if invalid_ids:
            citation_status = "invalid"
        elif not mentioned_ids:
            citation_status = "missing"
        else:
            citation_status = "valid"

        return {
            "status": "answered",
            "answer": answer["answer"],
            "citations": used_citations,
            "citation_status": citation_status,
            "invalid_citations": list(invalid_ids),
            "retrieved_count": len(passages),
            "evidence_decision": evidence["decision"],
            "retry_metrics": {
                "evidence_retries": evidence_retries,
                "generation_retries": generation_retries
            },
            "generation_metrics": {
                "latency_ms": answer["latency_ms"],
                "tokens_in": answer["tokens_in"],
                "tokens_out": answer["tokens_out"],
                "request_id": answer["request_id"]
            }
        }
