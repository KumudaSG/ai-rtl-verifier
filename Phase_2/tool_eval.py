import argparse
import csv
import json
from datetime import datetime
from typing import Dict, Any, List

from tool_pipeline import run_tool_pipeline
from baseline import normalize_problem_id


DEFAULT_NUM_RUNS = 5
VALID_PROBLEMS = ["P1", "P2", "P3", "P4", "P5"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate the tool pipeline over multiple runs and summarize results."
    )
    parser.add_argument(
        "--problems",
        nargs="+",
        default=VALID_PROBLEMS,
        help="Problem IDs to evaluate, such as P1 P2 P3"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_NUM_RUNS,
        help="Number of runs per problem"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Vivado verification timeout in seconds"
    )
    parser.add_argument(
        "--tool-retries",
        type=int,
        default=2,
        help="Maximum number of tool-fix retries"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed logs during evaluation"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="tool_eval_results.csv",
        help="CSV file to save per-run results"
    )
    parser.add_argument(
        "--json",
        type=str,
        default="tool_eval_summary.json",
        help="JSON file to save aggregate summary"
    )
    return parser.parse_args()


def safe_check_count(details: Dict[str, Any]) -> Dict[str, int]:
    pass_count = 0
    fail_count = 0

    for check_name, check_value in details.items():
        if check_value:
            pass_count += 1
        else:
            fail_count += 1

    return {
        "pass_count": pass_count,
        "fail_count": fail_count
    }


def summarize_tool_history(tool_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_attempts = len(tool_history)
    compile_passes = 0
    compile_failures = 0
    final_tool_pass = False
    last_tool_reason = "No tool history"

    for tool_result in tool_history:
        if tool_result.get("pass"):
            compile_passes += 1
        else:
            compile_failures += 1

    if total_attempts > 0:
        final_tool_pass = tool_history[-1].get("pass", False)
        last_tool_reason = tool_history[-1].get("reason", "Unknown")

    return {
        "tool_attempts": total_attempts,
        "tool_compile_passes": compile_passes,
        "tool_compile_failures": compile_failures,
        "final_tool_pass": final_tool_pass,
        "last_tool_reason": last_tool_reason
    }


def run_one_evaluation(
    problem_id: str,
    run_index: int,
    timeout_seconds: int,
    max_tool_retries: int,
    verbose: bool
) -> Dict[str, Any]:
    generated_solution, verification_result, tool_history = run_tool_pipeline(
        problem_id=problem_id,
        verbose=verbose,
        timeout_seconds=timeout_seconds,
        max_tool_retries=max_tool_retries
    )

    detail_counts = safe_check_count(verification_result.get("details", {}))
    tool_summary = summarize_tool_history(tool_history)

    row = {
        "problem_id": problem_id,
        "run_index": run_index,
        "final_pass": verification_result.get("pass", False),
        "verification_reason": verification_result.get("reason", ""),
        "num_checks_passed": detail_counts["pass_count"],
        "num_checks_failed": detail_counts["fail_count"],
        "tool_attempts": tool_summary["tool_attempts"],
        "tool_compile_passes": tool_summary["tool_compile_passes"],
        "tool_compile_failures": tool_summary["tool_compile_failures"],
        "final_tool_pass": tool_summary["final_tool_pass"],
        "last_tool_reason": tool_summary["last_tool_reason"],
        "top_module_name": getattr(generated_solution, "top_module_name", ""),
        "control_module_name": getattr(generated_solution, "control_module_name", ""),
        "datapath_module_name": getattr(generated_solution, "datapath_module_name", "")
    }

    return row


def write_csv(filename: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with open(filename, "w", newline="", encoding="utf-8") as file_object:
        writer = csv.DictWriter(file_object, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_runs": len(rows),
        "overall_final_passes": 0,
        "overall_final_failures": 0,
        "overall_pass_rate": 0.0,
        "by_problem": {}
    }

    if not rows:
        return summary

    overall_passes = 0

    for row in rows:
        if row["final_pass"]:
            overall_passes += 1

        problem_id = row["problem_id"]

        if problem_id not in summary["by_problem"]:
            summary["by_problem"][problem_id] = {
                "runs": 0,
                "final_passes": 0,
                "final_failures": 0,
                "pass_rate": 0.0,
                "avg_tool_attempts": 0.0,
                "avg_checks_passed": 0.0,
                "avg_checks_failed": 0.0,
                "tool_compile_fail_runs": 0
            }

        problem_summary = summary["by_problem"][problem_id]
        problem_summary["runs"] += 1
        problem_summary["avg_tool_attempts"] += row["tool_attempts"]
        problem_summary["avg_checks_passed"] += row["num_checks_passed"]
        problem_summary["avg_checks_failed"] += row["num_checks_failed"]

        if row["final_pass"]:
            problem_summary["final_passes"] += 1
        else:
            problem_summary["final_failures"] += 1

        if row["tool_compile_failures"] > 0:
            problem_summary["tool_compile_fail_runs"] += 1

    summary["overall_final_passes"] = overall_passes
    summary["overall_final_failures"] = len(rows) - overall_passes
    summary["overall_pass_rate"] = overall_passes / len(rows)

    for problem_id, problem_summary in summary["by_problem"].items():
        run_count = problem_summary["runs"]
        if run_count > 0:
            problem_summary["pass_rate"] = problem_summary["final_passes"] / run_count
            problem_summary["avg_tool_attempts"] /= run_count
            problem_summary["avg_checks_passed"] /= run_count
            problem_summary["avg_checks_failed"] /= run_count

    return summary


def write_json(filename: str, data: Dict[str, Any]) -> None:
    with open(filename, "w", encoding="utf-8") as file_object:
        json.dump(data, file_object, indent=2)


def print_summary(summary: Dict[str, Any]) -> None:
    print("\n=== Tool Pipeline Evaluation Summary ===")
    print(f"Total runs: {summary['total_runs']}")
    print(f"Overall passes: {summary['overall_final_passes']}")
    print(f"Overall failures: {summary['overall_final_failures']}")
    print(f"Overall pass rate: {summary['overall_pass_rate']:.2%}")

    print("\nPer-problem results:")
    for problem_id, problem_summary in summary["by_problem"].items():
        print(f"\n{problem_id}")
        print(f"  Runs: {problem_summary['runs']}")
        print(f"  Final passes: {problem_summary['final_passes']}")
        print(f"  Final failures: {problem_summary['final_failures']}")
        print(f"  Pass rate: {problem_summary['pass_rate']:.2%}")
        print(f"  Avg tool attempts: {problem_summary['avg_tool_attempts']:.2f}")
        print(f"  Avg checks passed: {problem_summary['avg_checks_passed']:.2f}")
        print(f"  Avg checks failed: {problem_summary['avg_checks_failed']:.2f}")
        print(f"  Runs with tool compile failure: {problem_summary['tool_compile_fail_runs']}")


def main():
    args = parse_args()

    normalized_problem_ids = []
    for raw_problem in args.problems:
        normalized_problem_ids.append(normalize_problem_id(raw_problem))

    rows = []

    for problem_id in normalized_problem_ids:
        for run_index in range(1, args.runs + 1):
            print(f"\nRunning {problem_id} | trial {run_index}/{args.runs}")

            row = run_one_evaluation(
                problem_id=problem_id,
                run_index=run_index,
                timeout_seconds=args.timeout,
                max_tool_retries=args.tool_retries,
                verbose=args.verbose
            )

            rows.append(row)

            print(
                f"Result: final_pass={row['final_pass']} | "
                f"tool_attempts={row['tool_attempts']} | "
                f"checks_passed={row['num_checks_passed']} | "
                f"checks_failed={row['num_checks_failed']}"
            )

    summary = build_summary(rows)

    write_csv(args.csv, rows)
    write_json(args.json, summary)
    print_summary(summary)

    print(f"\nSaved per-run results to: {args.csv}")
    print(f"Saved summary to: {args.json}")


if __name__ == "__main__":
    main()
