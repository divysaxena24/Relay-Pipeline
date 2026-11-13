
import time


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

RETRYABLE_ERROR_NAMES = {
    "StandInError",
    "StandInRateLimitError",
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
    "TimeoutError",
    "ConnectionError",
}


def is_retryable_error(error: Exception) -> bool:
    # Check the exception class and all its parent classes.
    error_names = {
        cls.__name__
        for cls in type(error).__mro__
    }

    if error_names & RETRYABLE_ERROR_NAMES:
        return True

    status_code = getattr(error, "status_code", None)

    return status_code in RETRYABLE_STATUS_CODES



def call_with_retries(
    function,
    *args,
    max_retries: int = 2,
    base_delay: float = 0.25,
    max_delay: float = 2.0,
    sleep_fn=time.sleep,
    before_attempt=None,
    **kwargs
):
    retries = 0

    while True:
        if before_attempt is not None:
            before_attempt()

        try:
            result = function(*args, **kwargs)
            return result, retries

        except Exception as error:
            if not is_retryable_error(error):
                error.retries = retries
                raise

            if retries >= max_retries:
                error.retries = retries
                raise

            delay = min(
                base_delay * (2 ** retries),
                max_delay
            )

            sleep_fn(delay)
            retries += 1
