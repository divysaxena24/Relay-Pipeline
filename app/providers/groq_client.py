
import os
import time

from groq import Groq


class GroqClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-20b"
        )

        if not api_key:
            raise ValueError("GROQ_API_KEY is missing.")

        self.client = Groq(api_key=api_key)

    def generate(self, question: str, context: str = ""):
        start_time = time.perf_counter()

        prompt = f"""
Answer the question using ONLY the supplied research passages.

STRICT RULES:
1. Every factual claim must have a citation.
2. Cite sources using their IDs, for example [S1] or [S2].
3. Use ONLY source IDs provided in the passages.
4. Put citations immediately after the claims they support.
5. Never invent citations, page numbers, or paper details.
6. If the evidence is insufficient, say so.
7. Keep the answer clear and concise.

Example:
Scaled dot-product attention computes query-key compatibility
using dot products [S1]. The scores are scaled by the square
root of the key dimension before softmax [S1].

Research passages:
{context}

Question:
{question}
"""

        response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {
                "role": "system",
                "content": "You are a careful research assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_completion_tokens=2048,
        reasoning_effort="low",
        include_reasoning=False
    )

        choice = response.choices[0]
                
        print("Generation finish reason:", choice.finish_reason        )
        print("Generation completion tokens:      ",
            response.usage.completion_tokens if response.usage else 0)

        end_time = time.perf_counter()

        answer = response.choices[0].message.content or ""

        usage = response.usage

        return {
            "answer": answer,
            "model": response.model,
            "latency_ms": round(
                (end_time - start_time) * 1000, 2
            ),
            "tokens_in": usage.prompt_tokens if usage else 0,
            "tokens_out": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
            "request_id": response.id
        }


    def check_evidence(self, question: str, context: str):
        prompt = f"""
Determine whether the research passages contain enough
information to answer the question.

Reply with exactly one word:
SUFFICIENT
or
INSUFFICIENT

Do not use outside knowledge.

Passages:
{context}

Question:
{question}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_completion_tokens=1024,
            reasoning_effort="low",
            include_reasoning=False
        )

        choice = response.choices[0]

        print("Evidence raw output:", repr(choice.message.content))
        print("Finish reason:", choice.finish_reason)
        print("Completion tokens:", response.usage.completion_tokens)

        message = response.choices[0].message

        decision = (message.content or "").strip().upper()

        print("Evidence checker raw output:", repr(message.content))
        print("Evidence checker finish reason:",
            response.choices[0].finish_reason)

        sufficient = decision.startswith("SUFFICIENT") and not (
            decision.startswith("INSUFFICIENT")
        )

        return {
            "sufficient": sufficient,
            "decision": decision,
            "request_id": response.id,
            "tokens_in": response.usage.prompt_tokens if response.usage else 0,
            "tokens_out": response.usage.completion_tokens if response.usage else 0
        }

