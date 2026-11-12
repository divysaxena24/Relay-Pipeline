
from collections import deque

from app.control.rate_limiter import RateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def main():
    clock = FakeClock()

    limiter = RateLimiter(
        max_requests=3,
        window_seconds=10
    )

    # Replace real time functions with our fake clock.
    import app.control.rate_limiter as module

    module.time.monotonic = clock.monotonic
    module.time.sleep = clock.sleep

    # First three requests should pass immediately.
    for _ in range(3):
        limiter.acquire()

    assert len(limiter.request_times) == 3
    assert clock.now == 0

    print("TEST 1: Three requests allowed - PASS")

    # Fourth request should wait until the first expires.
    limiter.acquire()

    assert clock.now >= 10
    assert len(limiter.request_times) == 1

    print("TEST 2: Excess request waits - PASS")

    # A new request should now be allowed immediately.
    previous_time = clock.now
    limiter.acquire()

    assert clock.now == previous_time

    print("TEST 3: Request allowed after window refresh - PASS")

    print("\nAll rate limiter tests passed.")


if __name__ == "__main__":
    main()
