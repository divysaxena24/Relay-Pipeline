
from dotenv import load_dotenv

from app.providers.groq_client import GroqClient


def main():
    load_dotenv()

    groq = GroqClient()

    context = """
    The Transformer uses scaled dot-product attention.
    It computes attention using queries, keys and values.
    The query-key dot products are scaled and passed
    through softmax to obtain attention weights.
    """

    question = "How does scaled dot-product attention work?"

    result = groq.generate(
        question=question,
        context=context
    )

    print("\n========== GROQ RESPONSE ==========")
    print(result["answer"])

    print("\n========== METRICS ==========")
    print("Model:", result["model"])
    print("Latency:", result["latency_ms"], "ms")
    print("Input tokens:", result["tokens_in"])
    print("Output tokens:", result["tokens_out"])
    print("Total tokens:", result["total_tokens"])
    print("Request ID:", result["request_id"])


if __name__ == "__main__":
    main()
