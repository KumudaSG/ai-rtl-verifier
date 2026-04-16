import argparse
import csv
import json
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

from verifier import verify, RTLSolution
from tool_pipeline import (
    generate_solution,
    enforce_expected_names,
    build_tool_feedback,
    run_iverilog_check,
    write_solution_files,
)
from baseline import (
    convert_to_verifier_solution,
    print_solution_summary,
)

load_dotenv()

PROBLEM_ID = "P5"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_TOOL_RETRIES = 2
DEFAULT_REFINEMENT_TURNS = 2
DEFAULT_NUM_RUNS = 5


def build_refinement_feedback(
    verifier_result: Dict[str, Any]
) -> str:
    reason = verifier_result.get("reason", "Unknown verifier failure")

    return f"""
Your previous SystemVerilog solution for {PROBLEM_ID} failed verification.

Regenerate the full structured RTL solution and fix the functional issues.

Requirements for this revision:
- Keep the same problem requirements and interface.
- Keep the required module split.
- Keep the exact required module names.
- Fix the behavioral logic, not just syntax.
- Each signal must have exactly one procedural driver.
- Do not leave placeholder modules.

Verifier reason:
{reason}
""".strip()


def run_tool_stage_once(
    problem_id: str,
    extra_feedback: Optional[str],
    verbose: bool
):
    generated_solution = generate_solution(problem_id, extra_feedback=extra_feedback)

    naming_error = enforce_expected_names(problem_id, generated_solution)
    if naming_error is not None:
        tool_result = {
            "pass": False,
            "reason": naming_error,
            "raw_output": naming_error,
            "returncode": None
        }
        return generated_solution, tool_result

    rtl_filenames = write_solution_files(problem_id, generated_solution)
    tool_result = run_iverilog_check(problem_id, rtl_filenames, verbose=verbose)
    return generated_solution, tool_result


def run_tool_augmented_refinement(
    problem_id: str,
    verbose: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_tool_retries: int = DEFAULT_TOOL_RETRIES,
    max_refinement_turns: int = DEFAULT_REFINEMENT_TURNS
):
    conversation_feedback = None
    refinement_history = []
    last_generated_solution = None

    for refinement_turn in range(max_refinement_turns + 1):
        if verbose:
            print(f"\nRefinement turn {refinement_turn + 1}/{max_refinement_turns + 1}")

        tool_feedback = conversation_feedback
        tool_history = []
        generated_solution = None

        for tool_attempt in range(max_tool_retries + 1):
            if verbose:
                print(f"Generating RTL for {problem_id} (tool attempt {tool_attempt + 1})...")

            generated_solution, tool_result = run_tool_stage_once(
                problem_id=problem_id,
                extra_feedback=tool_feedback,
                verbose=verbose
            )
            last_generated_solution = generated_solution
            tool_history.append(tool_result)

            if tool_result["pass"]:
                break

            if tool_attempt == max_tool_retries:
                verification_result = {
                    "pass": False,
                    "details": {},
                    "reason": f"Tool stage failed after {max_tool_retries + 1} attempts: {tool_result['reason']}"
                }

                refinement_history.append(
                    {
                        "refinement_turn": refinement_turn + 1,
                        "tool_attempts": len(tool_history),
                        "tool_pass": False,
                        "verifier_pass": False,
                        "reason": verification_result["reason"]
                    }
                )

                if refinement_turn == max_refinement_turns:
                    return last_generated_solution, verification_result, refinement_history

                conversation_feedback = build_refinement_feedback(verification_result)
                generated_solution = None
                break

            tool_feedback = build_tool_feedback(problem_id, tool_result)

        if generated_solution is None:
            continue

        verifier_solution: RTLSolution = convert_to_verifier_solution(generated_solution)
        verification_result = verify(
            problem_id=problem_id,
            solution=verifier_solution,
            verbose=verbose,
            timeout_seconds=timeout_seconds
        )

        refinement_history.append(
            {
                "refinement_turn": refinement_turn + 1,
                "tool_attempts": len(tool_history),
                "tool_pass": True,
                "verifier_pass": verification_result.get("pass", False),
                "reason": verification_result.get("reason", "Unknown verifier result")
            }
        )

        if verification_result.get("pass", False):
            return generated_solution, verification_result, refinement_history

        if refinement_turn == max_refinement_turns:
            return generated_solution, verification_result, refinement_history

        conversation_feedback = build_refinement_feedback(verification_result)

    return last_generated_solution, {
        "pass": False,
        "details": {},
        "reason": "Unexpected refinement failure"
    }, refinement_history


def run_experiment(
    num_runs: int,
    verbose: bool,
    timeout_seconds: int,
    max_tool_retries: int,
    max_refinement_turns: int
) -> List[Dict[str, Any]]:
    rows = []

    for run_index in range(1, num_runs + 1):
        print(f"\nRunning {PROBLEM_ID} | trial {run_index}/{num_runs}")

        generated_solution, verification_result, refinement_history = run_tool_augmented_refinement(
            problem_id=PROBLEM_ID,
            verbose=verbose,
            timeout_seconds=timeout_seconds,
            max_tool_retries=max_tool_retries,
            max_refinement_turns=max_refinement_turns
        )

        if generated_solution is not None:
            print_solution_summary(PROBLEM_ID, generated_solution)

        final_pass = verification_result.get("pass", False)
        final_reason = verification_result.get("reason", "Unknown")
        turns_used = len(refinement_history)

        if len(refinement_history) > 0:
            final_tool_attempts = refinement_history[-1]["tool_attempts"]
        else:
            final_tool_attempts = 0

        print("\nRefinement history:")
        for item in refinement_history:
            print(
                f"Turn {item['refinement_turn']}: "
                f"tool_pass={item['tool_pass']} | "
                f"verifier_pass={item['verifier_pass']} | "
                f"tool_attempts={item['tool_attempts']} | "
                f"reason={item['reason']}"
            )

        print("\nFinal verification result:")
        print(verification_result)

        rows.append(
            {
                "problem_id": PROBLEM_ID,
                "run_index": run_index,
                "final_pass": final_pass,
                "final_reason": final_reason,
                "refinement_turns_used": turns_used,
                "final_tool_attempts": final_tool_attempts
            }
        )

    return rows


def write_csv(filename: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with open(filename, "w", newline="", encoding="utf-8") as file_object:
        writer = csv.DictWriter(file_object, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_runs = len(rows)
    total_passes = 0

    for row in rows:
        if row["final_pass"]:
            total_passes += 1

    summary = {
        "problem_id": PROBLEM_ID,
        "total_runs": total_runs,
        "total_passes": total_passes,
        "total_failures": total_runs - total_passes,
        "pass_rate": (total_passes / total_runs) if total_runs > 0 else 0.0,
        "runs": rows
    }

    return summary


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run tool-augmented self-refinement on P5 for five trials."
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_NUM_RUNS,
        help="Number of trials to run"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Vivado verification timeout in seconds"
    )
    parser.add_argument(
        "--tool-retries",
        type=int,
        default=DEFAULT_TOOL_RETRIES,
        help="Maximum number of tool-stage retries per refinement turn"
    )
    parser.add_argument(
        "--refinement-turns",
        type=int,
        default=DEFAULT_REFINEMENT_TURNS,
        help="Maximum number of refinement turns after the initial attempt"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="refinement_results.csv",
        help="CSV file for per-run results"
    )
    parser.add_argument(
        "--json",
        type=str,
        default="refinement_summary.json",
        help="JSON file for summary results"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print tool and verifier logs"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    rows = run_experiment(
        num_runs=args.runs,
        verbose=args.verbose,
        timeout_seconds=args.timeout,
        max_tool_retries=args.tool_retries,
        max_refinement_turns=args.refinement_turns
    )

    summary = build_summary(rows)

    write_csv(args.csv, rows)

    with open(args.json, "w", encoding="utf-8") as file_object:
        json.dump(summary, file_object, indent=2)

    print("\n=== Final Summary ===")
    print(f"Problem: {summary['problem_id']}")
    print(f"Total runs: {summary['total_runs']}")
    print(f"Passes: {summary['total_passes']}")
    print(f"Failures: {summary['total_failures']}")
    print(f"Pass rate: {summary['pass_rate']:.2%}")
    print(f"Saved CSV: {args.csv}")
    print(f"Saved JSON: {args.json}")


if __name__ == "__main__":
    main()
