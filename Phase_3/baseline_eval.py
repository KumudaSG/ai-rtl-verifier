import json
import time
from datetime import datetime

from tool_pipeline import run_tool_pipeline, MODEL_NAME


PROBLEMS = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"]
TRIALS_PER_PROBLEM = 5

TEMPERATURE = 0.3
PIPELINE_CHOICE = "HW3 tool-augmented pipeline with tool retries disabled"


def run_baseline_eval():
    baseline_log = {
        "run_configuration": {
            "pipeline_choice": PIPELINE_CHOICE,
            "model": MODEL_NAME,
            "temperature": TEMPERATURE,
            "trials_per_problem": TRIALS_PER_PROBLEM,
            "timestamp": datetime.now().isoformat(),
            "tool_retries": 0,
            "memory": "off",
            "self_refinement": "off",
        },
        "results": []
    }

    for problem_id in PROBLEMS:
        print(f"\n========== Running {problem_id} ==========")

        for trial_number in range(1, TRIALS_PER_PROBLEM + 1):
            print(f"\n--- {problem_id} Trial {trial_number} ---")

            start_time = time.time()

            try:
                generated_solution, verification_result, tool_history = run_tool_pipeline(
                    problem_id=problem_id,
                    verbose=False,
                    timeout_seconds=60,
                    max_tool_retries=0
                )

                elapsed_seconds = time.time() - start_time

                trial_record = {
                    "problem_id": problem_id,
                    "trial": trial_number,
                    "pass": verification_result["pass"],
                    "details": verification_result["details"],
                    "reason": verification_result["reason"],
                    "tool_history": tool_history,
                    "elapsed_seconds": elapsed_seconds,
                }

                print("PASS" if verification_result["pass"] else "FAIL")
                print("Reason:", verification_result["reason"])

            except Exception as error:
                elapsed_seconds = time.time() - start_time

                trial_record = {
                    "problem_id": problem_id,
                    "trial": trial_number,
                    "pass": False,
                    "details": {},
                    "reason": f"Baseline evaluation exception: {error}",
                    "tool_history": [],
                    "elapsed_seconds": elapsed_seconds,
                }

                print("FAIL")
                print("Reason:", trial_record["reason"])

            baseline_log["results"].append(trial_record)

            with open("baseline_log.json", "w", encoding="utf-8") as file_object:
                json.dump(baseline_log, file_object, indent=2)

    print("\nBaseline evaluation complete.")
    print("Saved results to baseline_log.json")


if __name__ == "__main__":
    run_baseline_eval()