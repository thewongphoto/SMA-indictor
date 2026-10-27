"""Verify active/reference agreement on current data; no configuration changes.

Run: python -m experiments.evaluate_frequency --output artifacts/frequency-evaluation.json
Optional longer histories are isolated test inputs, not a new generator default.
"""
import argparse
import hashlib
import json
from pathlib import Path

from .observable_frequency import best_candidate, optimize_proposed, proposed_cap
from sma_analyzer.engine import optimize_sma
from sma_analyzer.mock_data import generate_mock_data
from sma_analyzer.settings import COUNTERS, SCENARIOS


def _fingerprints(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((root / "sma_analyzer").glob("*.py"))}


def run_evaluation():
    root = Path(__file__).resolve().parents[1]
    before = _fingerprints(root)
    cases = []
    for counter in COUNTERS:
        for scenario in SCENARIOS:
            dataset = generate_mock_data(counter, scenario)
            for target in [12, 6, 1]:
                existing = optimize_sma(dataset.prices, target)
                normalized = best_candidate(dataset.prices, target, range(2, len(dataset.prices)))
                proposed = optimize_proposed(dataset.prices, target)

                if (existing.period, existing.comparisons, existing.frequency, existing.events) != (
                    proposed.period, proposed.comparisons, proposed.frequency, proposed.events
                ):
                    raise RuntimeError("Active optimizer differs from independent reference.")

                def summary(result):
                    return {"period": result.period, "crossings": result.crossing_count,
                            "observable_comparisons": result.comparisons,
                            "annual_frequency": float(result.frequency),
                            "annual_error": float(result.frequency_error)}

                cases.append({
                    "counter": counter, "scenario": scenario, "history_sessions": len(dataset.prices),
                    "target": target, "proposed_cap": proposed_cap(len(dataset.prices)),
                    "current_app": {"period": existing.period, "crossings": existing.crossing_count,
                                    "displayed_annual_frequency": existing.actual_annual_frequency},
                    "normalization_only_uncapped_control": summary(normalized),
                    "complete_proposal": summary(proposed),
                })

    # Exercise the cap's two transition points without changing UI mock history.
    boundaries = []
    for history in [503, 504, 505, 755, 756, 757, 1008, 1260]:
        data = generate_mock_data("DEMO-SGX", "Sideways", sessions=history)
        result = optimize_proposed(data.prices, 12)
        boundaries.append({"history_sessions": history, "cap": proposed_cap(history),
                           "minimum_comparisons": history - proposed_cap(history),
                           "period": result.period, "crossings": result.crossing_count,
                           "observable_comparisons": result.comparisons,
                           "annual_frequency": float(result.frequency)})
    after = _fingerprints(root)
    if before != after:
        raise RuntimeError("Application source changed during evaluation.")
    return {"active_policy_verified": True, "simulated_data_only": True, "application_source_unchanged": True,
            "application_source_sha256": before, "current_mock_history_sessions": 252,
            "cases": cases, "isolated_longer_history_checks": boundaries}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_evaluation()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    for case in report["cases"]:
        new = case["complete_proposal"]
        print(f"{case['counter']} {case['scenario']:<11} target={case['target']:>2}: "
              f"active SMA={new['period']:>3}, crossings={new['crossings']:>2}, "
              f"usable={new['observable_comparisons']:>3}, annual={new['annual_frequency']:.4f}")
    print("Verified: active policy matches reference; evaluation changed no app source; mock history remains 252 sessions.")
