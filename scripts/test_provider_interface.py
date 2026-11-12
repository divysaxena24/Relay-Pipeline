
from app.providers.base import ModelProvider
from app.providers.groq_client import GroqClient
from standin.model import StandInModel


def main():
    print("TEST 1: Groq provider interface")
    assert issubclass(GroqClient, ModelProvider)
    print("PASS")

    print("\nTEST 2: Stand-in provider interface")
    standin = StandInModel(latency_ms=0)
    assert isinstance(standin, ModelProvider)
    print("PASS")

    print("\nTEST 3: Stand-in generate response")
    generated = standin.generate(
        "How does attention work?",
        "Attention uses queries, keys and values."
    )

    required_generate = {
        "answer",
        "model",
        "latency_ms",
        "tokens_in",
        "tokens_out",
        "total_tokens",
        "finish_reason",
        "request_id"
    }

    assert required_generate.issubset(generated.keys())
    print("PASS")

    print("\nTEST 4: Stand-in evidence response")
    evidence = standin.check_evidence(
        "How does attention work?",
        "Attention uses queries, keys and values."
    )

    required_evidence = {
        "sufficient",
        "decision",
        "request_id",
        "tokens_in",
        "tokens_out"
    }

    assert required_evidence.issubset(evidence.keys())
    print("PASS")

    print("\nAll 4 compatibility tests passed.")


if __name__ == "__main__":
    main()
