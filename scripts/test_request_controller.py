
from app.control.request_controller import RequestController
from standin.model import StandInError


class FlakyService:
    def __init__(self):
        self.calls = 0

    def request(self):
        self.calls += 1

        if self.calls == 1:
            raise StandInError("Temporary failure")

        return "SUCCESS"


def main():
    controller = RequestController(
        max_requests=10,
        window_seconds=60,
        max_concurrent=2,
        max_retries=2
    )

    service = FlakyService()

    # Disable actual waiting for this unit test.
    controller.rate_limiter.acquire = lambda: None

    result, retries = controller.execute(service.request)

    assert result == "SUCCESS"
    assert retries == 1
    assert service.calls == 2

    print("TEST 1: Request controller retries - PASS")

    # Test a successful request without retry.
    result, retries = controller.execute(lambda: "OK")

    assert result == "OK"
    assert retries == 0

    print("TEST 2: Successful request - PASS")

    print("\nAll request controller tests passed.")


if __name__ == "__main__":
    main()
