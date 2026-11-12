
from standin.model import StandInModel, StandInError, StandInRateLimitError


def main():
    print("TEST 1: Normal request")

    model = StandInModel(latency_ms=100)

    result = model.generate(
        "How does attention work?",
        "Attention uses queries, keys and values."
    )

    print("Latency:", result["latency_ms"], "ms")
    assert result["finish_reason"] == "stop"
    print("PASS")

    print("\nTEST 2: Simulated failure")

    model = StandInModel(latency_ms=0, failure_rate=1.0)

    try:
        model.generate("Test")
        assert False, "Expected failure was not raised."
    except StandInError:
        print("PASS")

    print("\nTEST 3: Simulated rate limit")

    model = StandInModel(latency_ms=0, rate_limit_every=1)

    try:
        model.generate("Test")
        assert False, "Expected rate limit was not raised."
    except StandInRateLimitError:
        print("PASS")

    print("\nTEST 4: Slow response")

    model = StandInModel(latency_ms=500)

    result = model.generate("Test")

    print("Measured latency:", result["latency_ms"], "ms")
    assert result["latency_ms"] >= 500
    print("PASS")

    print("\nTEST 5: Refusal")

    model = StandInModel(latency_ms=0, refusal_rate=1.0)

    result = model.generate("Test")

    print("Answer:", result["answer"])
    assert "cannot answer" in result["answer"].lower()
    print("PASS")


if __name__ == "__main__":
    main()


print("\nTEST 6: Streaming response")

model = StandInModel(latency_ms=0)

received = ""

for chunk in model.generate_stream(
    "How does attention work?"
):
    print(chunk, end="", flush=True)
    received += chunk

print()

assert received.strip()
print("PASS")