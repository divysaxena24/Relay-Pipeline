
from app.control.retry import call_with_retries
from app.control.rate_limiter import RateLimiter
from app.control.concurrency import ConcurrencyLimiter


class RequestController:
    def __init__(
        self,
        max_requests: int = 25,
        window_seconds: float = 60,
        max_concurrent: int = 3,
        max_retries: int = 2
    ):
        self.rate_limiter = RateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds
        )

        self.concurrency_limiter = ConcurrencyLimiter(
            max_concurrent=max_concurrent
        )

        self.max_retries = max_retries

    def execute(self, function, *args, **kwargs):
        return self.concurrency_limiter.execute(
            call_with_retries,
            function,
            *args,
            max_retries=self.max_retries,
            before_attempt=self.rate_limiter.acquire,
            **kwargs
        )
