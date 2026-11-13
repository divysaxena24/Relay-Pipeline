
import csv
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import numpy as np

from app.control.request_controller import RequestController
from standin.model import (
    StandInModel,
    StandInError,
    StandInRateLimitError,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_FILE = PROJECT_ROOT / "results" / "results.csv"

CSV_FIELDS = [
    "request_id",
    "scenario",
    "source",
    "start_time",
    "first_token_ms",
    "total_ms",
    "status",
    "retries",
    "tokens_in",
    "tokens_out",
    "retrieval_setting",
    "answer_grade",
]


class DailyBudgetStandIn:
    """Wrap a stand-in model with a simulated daily request budget."""

    def __init__(self, model, daily_budget=5):
        self.model = model
        self.daily_budget = daily_budget
        self.successful_calls = 0
        self.rejected_calls = 0
        self.lock = threading.Lock()

    def generate(self, question, context=""):
        with self.lock:
            if self.successful_calls >= self.daily_budget:
                self.rejected_calls += 1
                raise StandInRateLimitError(
                    "Simulated daily budget exhausted."
                )

            self.successful_calls += 1

        return self.model.generate(question, context)

    def check_evidence(self, question, context):
        with self.lock:
            if self.successful_calls >= self.daily_budget:
                self.rejected_calls += 1
                raise StandInRateLimitError(
                    "Simulated daily budget exhausted."
                )

            self.successful_calls += 1

        return self.model.check_evidence(question, context)



def execute_request(
    model,
    controller,
    request_id,
    scenario,
    offered_at,
    offered_perf,
):
    question = "How does scaled dot-product attention work?"
    context = (
        "Scaled dot-product attention computes attention scores "
        "using queries, keys and values. The scores are scaled "
        "before applying softmax."
    )

    row = {
        "request_id": request_id,
        "scenario": scenario,
        "source": "stand-in",
        "start_time": offered_at.isoformat(),
        "first_token_ms": "",
        "total_ms": "",
        "status": "error",
        "retries": 0,
        "tokens_in": "",
        "tokens_out": "",
        "retrieval_setting": "direct_model_call",
        "answer_grade": "",
    }

    try:
        response, retries = controller.execute(
            model.generate,
            question=question,
            context=context,
        )

        row["status"] = "ok"
        row["retries"] = retries
        row["tokens_in"] = response.get("tokens_in", "")
        row["tokens_out"] = response.get("tokens_out", "")

    except StandInRateLimitError as error:
        row["status"] = "rate_limited"
        row["retries"] = getattr(error, "retries", 0)

    except TimeoutError as error:
        row["status"] = "timeout"
        row["retries"] = getattr(error, "retries", 0)

    except StandInError as error:
        row["status"] = "error"
        row["retries"] = getattr(error, "retries", 0)
        print(f"Request {request_id} failed: {error}")

    except Exception as error:
        row["status"] = "error"
        row["retries"] = getattr(error, "retries", 0)
        print(f"Request {request_id} failed: {error}")

    # Includes executor queue wait + controller wait + model latency.
    row["total_ms"] = round(
        (time.perf_counter() - offered_perf) * 1000,
        2,
    )

    return row


def append_results(rows):
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_exists = (
        RESULTS_FILE.exists()
        and RESULTS_FILE.stat().st_size > 0
    )

    if file_exists:
        with RESULTS_FILE.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            existing_fields = next(csv.reader(file), [])

        if existing_fields != CSV_FIELDS:
            raise ValueError(
                "Existing results.csv has a different schema. "
                "Inspect its header before proceeding."
            )

    with RESULTS_FILE.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)

        if not file_exists:
            writer.writeheader()

        writer.writerows(rows)


def run_scenario(
    name,
    request_count,
    arrival_interval,
    max_requests=1000,
    window_seconds=60,
    model=None,
):
    print(f"\n{'=' * 60}")
    print(f"SCENARIO: {name}")
    print(f"Requests: {request_count}")
    print(f"Arrival interval: {arrival_interval} seconds")
    print("=" * 60)

    if model is None:
        model = StandInModel(
            latency_ms=573,
            failure_rate=0.0,
            refusal_rate=0.0,
            rate_limit_every=0,
        )

    controller = RequestController(
        max_requests=max_requests,
        window_seconds=window_seconds,
        max_concurrent=3,
        max_retries=2,
    )

    rows = []
    futures = []
    peak_queue_length = 0

    first_submission = None
    last_submission = None

    with ThreadPoolExecutor(max_workers=3) as executor:

        # Submit requests according to the scenario's arrival pattern.
        for _ in range(request_count):
            offered_at = datetime.now(timezone.utc)
            offered_perf = time.perf_counter()

            if first_submission is None:
                first_submission = offered_perf

            last_submission = offered_perf

            request_id = str(uuid.uuid4())

            future = executor.submit(
                execute_request,
                model,
                controller,
                request_id,
                name,
                offered_at,
                offered_perf,
            )

            futures.append(future)

            queued = sum(
                1
                for item in futures
                if not item.running() and not item.done()
            )

            peak_queue_length = max(
                peak_queue_length,
                queued,
            )

            if arrival_interval > 0:
                time.sleep(arrival_interval)

        # Collect all completed requests.
        for future in as_completed(futures):
            rows.append(future.result())

    append_results(rows)

    total_latencies = [
        float(row["total_ms"])
        for row in rows
        if row["total_ms"] != ""
    ]

    successful = sum(
        row["status"] == "ok"
        for row in rows
    )

    failed = len(rows) - successful

    offered_duration = (
        last_submission - first_submission
        if request_count > 1
        else 0
    )

    offered_rate = (
        request_count / offered_duration
        if offered_duration > 0
        else 0
    )

    print(f"Completed requests: {len(rows)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Offered rate: {offered_rate:.2f} requests/sec")
    print(f"Peak queued requests (sampled): {peak_queue_length}")

    if total_latencies:
        print(
            f"Total latency p50: "
            f"{np.percentile(total_latencies, 50):.2f} ms"
        )
        print(
            f"Total latency p95: "
            f"{np.percentile(total_latencies, 95):.2f} ms"
        )
        print(
            f"Total latency p99: "
            f"{np.percentile(total_latencies, 99):.2f} ms"
        )

    print(f"Raw results appended to: {RESULTS_FILE}")
    print(f"Rate limit: {max_requests} requests / {window_seconds} seconds")
    print(f"Concurrency limit: 3")

    return rows


def main():
    scenarios = [
        ("hour9_steady_v2", 20, 0.30),
        ("hour9_burst", 30, 0),
        ("hour9_sustained_overload", 40, 0.05),
    ]

    for name, count, interval in scenarios:
        run_scenario(name, count, interval)
    
        # Simulate halving Groq's observed project limit:
    # 30 RPM becomes 15 RPM.
    run_scenario(
        name="hour9_reduced_limit_v1",
        request_count=20,
        arrival_interval=0,
        max_requests=15,
        window_seconds=60,
    )

    daily_model = DailyBudgetStandIn(
        model=StandInModel(
            latency_ms=573,
            failure_rate=0.0,
            refusal_rate=0.0,
            rate_limit_every=0,
        ),
        daily_budget=5,
    )

    daily_rows = run_scenario(
        name="hour9_daily_budget_v1",
        request_count=20,
        arrival_interval=0,
        max_requests=1000,
        window_seconds=60,
        model=daily_model,
    )

    print("\nDAILY BUDGET RESULTS")
    print(f"Successful model calls: {daily_model.successful_calls}")
    print(f"Rejected model attempts: {daily_model.rejected_calls}")
    print(
        "Requests marked rate-limited:",
        sum(row["status"] == "rate_limited" for row in daily_rows),
    )

    print("\nALL THREE TRAFFIC SCENARIOS FINISHED.")
    print(f"Check raw data: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
