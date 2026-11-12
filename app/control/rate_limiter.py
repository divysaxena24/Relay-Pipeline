
import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float = 60):
        if max_requests <= 0:
            raise ValueError("max_requests must be positive.")

        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive.")

        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_times = deque()
        self.lock = threading.Lock()

    def acquire(self):
        while True:
            with self.lock:
                now = time.monotonic()

                # Remove requests outside the time window.
                while (
                    self.request_times
                    and now - self.request_times[0] >= self.window_seconds
                ):
                    self.request_times.popleft()

                if len(self.request_times) < self.max_requests:
                    self.request_times.append(now)
                    return

                wait_time = (
                    self.window_seconds
                    - (now - self.request_times[0])
                )

            time.sleep(max(wait_time, 0))
