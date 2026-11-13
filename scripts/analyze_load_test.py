
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "results" / "results.csv"
OUTPUT_FILE = ROOT / "results" / "scenario_summary.csv"

df = pd.read_csv(INPUT_FILE)

# Exclude the first steady run from the corrected steady-load comparison.
# Keep it in the raw CSV as an earlier overloaded-arrival experiment.
comparison_scenarios = [
    "baseline_sequential",
    "hour9_steady_v2",
    "hour9_burst",
    "hour9_sustained_overload",
    "hour9_reduced_limit_v1",
    "hour9_daily_budget_v1",
]

df = df[df["scenario"].isin(comparison_scenarios)].copy()

summary = []

for (scenario, source), group in df.groupby(
    ["scenario", "source"]
):
    latencies = pd.to_numeric(
        group["total_ms"],
        errors="coerce"
    ).dropna()

    total = len(group)
    successful = (group["status"] == "ok").sum()

    summary.append({
        "scenario": scenario,
        "source": source,
        "requests": total,
        "success_pct": round(successful / total * 100, 2),
        "rate_limited_pct": round(
            (group["status"] == "rate_limited").mean() * 100, 2
        ),
        "timeout_pct": round(
            (group["status"] == "timeout").mean() * 100, 2
        ),
        "error_pct": round(
            (group["status"] == "error").mean() * 100, 2
        ),
        "avg_retries_per_request": round(
            pd.to_numeric(group["retries"], errors="coerce").fillna(0).mean(),
            2
        ),
        "p50_total_ms": round(latencies.quantile(0.50), 2)
            if not latencies.empty else None,
        "p95_total_ms": round(latencies.quantile(0.95), 2)
            if not latencies.empty else None,
        "p99_total_ms": round(latencies.quantile(0.99), 2)
            if not latencies.empty else None,
        "avg_tokens_in": round(
            pd.to_numeric(group["tokens_in"], errors="coerce").mean(), 2
        ),
        "avg_tokens_out": round(
            pd.to_numeric(group["tokens_out"], errors="coerce").mean(), 2
        ),
        "first_token_measurements": group["first_token_ms"].count(),
    })

result = pd.DataFrame(summary)
result.to_csv(OUTPUT_FILE, index=False)

print("\nSCENARIO SUMMARY")
print(result.to_string(index=False))
print(f"\nSaved summary to: {OUTPUT_FILE}")
