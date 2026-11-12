
from app.control.retry import call_with_retries
from standin.model import StandInError


class TemporaryError(StandInError):
    pass


class PermanentError(Exception):
    pass


class FakeService:
    def __init__(self, failures_before_success=0):
        self.calls = 0
        self.failures_before_success = failures_before_success

    def request(self):
        self.calls += 1

        if self.calls <= self.failures_before_success:
            raise TemporaryError("Temporary service failure")

        return "SUCCESS"


def main():
    delays = []

    # TEST 1: First attempt fails, second succeeds
    service = FakeService(failures_before_success=1)

    result, retries = call_with_retries(
        service.request,
        sleep_fn=delays.append
    )

    assert result == "SUCCESS"
    assert retries == 1
    assert service.calls == 2
    assert delays == [0.25]

    print("TEST 1: Retry after temporary failure - PASS")

    # TEST 2: Two failures, third attempt succeeds
    delays.clear()
    service = FakeService(failures_before_success=2)

    result, retries = call_with_retries(
        service.request,
        sleep_fn=delays.append
    )

    assert result == "SUCCESS"
    assert retries == 2
    assert service.calls == 3
    assert delays == [0.25, 0.5]

    print("TEST 2: Exponential backoff - PASS")

    # TEST 3: All attempts fail
    service = FakeService(failures_before_success=5)

    try:
        call_with_retries(
            service.request,
            sleep_fn=lambda delay: None
        )
        raise AssertionError("Expected an exception")

    except TemporaryError:
        assert service.calls == 3
        print("TEST 3: Maximum retries enforced - PASS")

    # TEST 4: Permanent error should not retry
    class PermanentService:
        def __init__(self):
            self.calls = 0

        def request(self):
            self.calls += 1
            raise PermanentError("Invalid request")

    service = PermanentService()

    try:
        call_with_retries(
            service.request,
            sleep_fn=lambda delay: None
        )
        raise AssertionError("Expected an exception")

    except PermanentError:
        assert service.calls == 1
        print("TEST 4: Non-retryable error - PASS")

    print("\nAll 4 retry tests passed.")


if __name__ == "__main__":
    main()
