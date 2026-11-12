
import threading
import time

from app.control.concurrency import ConcurrencyLimiter


def main():
    limiter = ConcurrencyLimiter(max_concurrent=2)

    active = 0
    peak_active = 0
    lock = threading.Lock()

    def task():
        nonlocal active, peak_active

        with lock:
            active += 1
            peak_active = max(peak_active, active)

        time.sleep(0.2)

        with lock:
            active -= 1

    threads = [
        threading.Thread(target=limiter.execute, args=(task,))
        for _ in range(6)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert peak_active <= 2
    assert peak_active == 2
    assert active == 0

    print("Peak concurrent tasks:", peak_active)
    print("TEST: Concurrency limit enforced - PASS")


if __name__ == "__main__":
    main()
