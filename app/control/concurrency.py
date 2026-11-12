
import threading


class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int):
        if max_concurrent <= 0:
            raise ValueError("max_concurrent must be positive.")

        self.semaphore = threading.BoundedSemaphore(max_concurrent)

    def acquire(self):
        self.semaphore.acquire()

    def release(self):
        self.semaphore.release()

    def execute(self, function, *args, **kwargs):
        with self.semaphore:
            return function(*args, **kwargs)
