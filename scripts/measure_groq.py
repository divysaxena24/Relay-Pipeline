
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from app.providers.groq_client import GroqClient


def main():
    load_dotenv()
    groq = GroqClient()

    output_path = Path("results/results.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "request_id", "scenario", "source", "start_time",
        "first_token_ms", "total_ms", "status", "retries",
        "tokens_in", "tokens_out", "retrieval_setting",
        "answer_grade"
    ]

    context = """
    The Transformer uses scaled dot-product attention.
    It computes attention using queries, keys and values.
    The query-key dot products are scaled and passed
    through softmax to obtain attention weights.
    """

    question = "How does scaled dot-product attention work?"

    file_exists = output_path.exists()

    with output_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)

        if not file_exists:
            writer.writeheader()

        for i in range(1, 6):
            request_id = f"real-baseline-{i:02d}"
            start_time = datetime.now(timezone.utc).isoformat()

            try:
                result = groq.generate(question, context)

                row = {
                    "request_id": request_id,
                    "scenario": "baseline_sequential",
                    "source": "real",
                    "start_time": start_time,
                    "first_token_ms": "",
                    "total_ms": result["latency_ms"],
                    "status": "ok",
                    "retries": 0,
                    "tokens_in": result["tokens_in"],
                    "tokens_out": result["tokens_out"],
                    "retrieval_setting": "manual_context",
                    "answer_grade": ""
                }

                print(
                    f"{request_id}: "
                    f"{result['latency_ms']} ms, "
                    f"{result['total_tokens']} tokens"
                )

            except Exception as error:
                status = (
                    "rate_limited"
                    if getattr(error, "status_code", None) == 429
                    else "error"
                )

                row = {
                    "request_id": request_id,
                    "scenario": "baseline_sequential",
                    "source": "real",
                    "start_time": start_time,
                    "first_token_ms": "",
                    "total_ms": "",
                    "status": status,
                    "retries": 0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "retrieval_setting": "manual_context",
                    "answer_grade": ""
                }

                print(f"{request_id}: {status} - {error}")

            writer.writerow(row)
            file.flush()
            time.sleep(2)

    print(f"\nMeasurements saved to: {output_path}")


if __name__ == "__main__":
    main()
