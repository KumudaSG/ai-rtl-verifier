from dotenv import load_dotenv
import argparse
import os
import subprocess
from typing import Dict, Any, List, Optional

from verifier import verify, RTLSolution

# Change this import if your current no-tool pipeline file has a different name.
from baseline import (
    client,
    MODEL_NAME,
    SYSTEM_PROMPT,
    PROBLEM_PROMPTS,
    GeneratedSolution,
    normalize_problem_id,
    prompt_for_problem_id,
    convert_to_verifier_solution,
    print_solution_summary,
)

load_dotenv()

IVERILOG_PATH = os.getenv("IVERILOG_PATH", r"C:\iverilog\bin\iverilog.exe")
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_TOOL_RETRIES = 2

TOOL_CONFIGS = {
    "P1": {"testbench_file": "tb_p1.sv"},
    "P2": {"testbench_file": "tb_p2.sv"},
    "P3": {"testbench_file": "tb_p3.sv"},
    "P4": {"testbench_file": "tb_p4.sv"},
    "P5": {"testbench_file": "tb_p5.sv"},
}


def build_messages(problem_id: str, extra_feedback: Optional[str] = None) -> List[Dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": PROBLEM_PROMPTS[problem_id]
        }
    ]

    if extra_feedback is not None:
        messages.append(
            {
                "role": "user",
                "content": extra_feedback
            }
        )

    return messages


def generate_solution(problem_id: str, extra_feedback: Optional[str] = None) -> GeneratedSolution:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_model=GeneratedSolution,
        temperature=0.3,
        messages=build_messages(problem_id, extra_feedback=extra_feedback),
        max_retries=2,
    )
    return response


def write_file(filename: str, content: str) -> None:
    with open(filename, "w", encoding="utf-8") as file_object:
        file_object.write(content)


def write_solution_files(problem_id: str, generated_solution: GeneratedSolution) -> List[str]:
    problem_tag = problem_id.lower()
    written_files = []

    top_filename = f"top_{problem_tag}.sv"
    write_file(top_filename, generated_solution.top_file.content)
    written_files.append(top_filename)

    if generated_solution.control_file is not None:
        control_filename = f"control_{problem_tag}.sv"
        write_file(control_filename, generated_solution.control_file.content)
        written_files.append(control_filename)

    if generated_solution.datapath_file is not None:
        datapath_filename = f"datapath_{problem_tag}.sv"
        write_file(datapath_filename, generated_solution.datapath_file.content)
        written_files.append(datapath_filename)

    for file_index, extra_file in enumerate(generated_solution.extra_files):
        original_name = extra_file.filename.strip() if extra_file.filename else f"extra_{file_index}.sv"
        extra_filename = f"{problem_tag}_{original_name}"
        write_file(extra_filename, extra_file.content)
        written_files.append(extra_filename)

    return written_files


def expected_module_names(problem_id: str) -> Dict[str, Optional[str]]:
    problem_tag = problem_id.lower()

    if problem_id == "P1":
        return {
            "top": f"top_{problem_tag}",
            "control": None,
            "datapath": None,
        }

    return {
        "top": f"top_{problem_tag}",
        "control": f"control_{problem_tag}",
        "datapath": f"datapath_{problem_tag}",
    }


def enforce_expected_names(problem_id: str, generated_solution: GeneratedSolution) -> Optional[str]:
    expected = expected_module_names(problem_id)

    if generated_solution.top_module_name != expected["top"]:
        return f"Top module must be named {expected['top']}, but got {generated_solution.top_module_name}"

    if expected["control"] is not None:
        if generated_solution.control_module_name != expected["control"]:
            return f"Control module must be named {expected['control']}, but got {generated_solution.control_module_name}"

    if expected["datapath"] is not None:
        if generated_solution.datapath_module_name != expected["datapath"]:
            return f"Datapath module must be named {expected['datapath']}, but got {generated_solution.datapath_module_name}"

    return None


def run_iverilog_check(problem_id: str, rtl_filenames: List[str], verbose: bool = False) -> Dict[str, Any]:
    if not os.path.exists(IVERILOG_PATH):
        return {
            "pass": False,
            "reason": f"Icarus executable not found at: {IVERILOG_PATH}",
            "raw_output": "",
            "returncode": None
        }

    testbench_file = TOOL_CONFIGS[problem_id]["testbench_file"]
    output_file = f"tool_{problem_id.lower()}.out"
    log_file = f"iverilog_{problem_id.lower()}.log"

    command = [
        IVERILOG_PATH,
        "-g2012",
        "-o",
        output_file,
    ] + rtl_filenames + [testbench_file]

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True
        )
    except Exception as error:
        return {
            "pass": False,
            "reason": f"Failed to run Icarus: {error}",
            "raw_output": "",
            "returncode": None
        }

    full_output = (process.stdout or "") + (process.stderr or "")
    write_file(log_file, full_output)

    if verbose and full_output.strip():
        print("\nIcarus output:")
        print(full_output)

    if process.returncode == 0:
        return {
            "pass": True,
            "reason": "Icarus compile passed",
            "raw_output": full_output,
            "returncode": process.returncode
        }

    return {
        "pass": False,
        "reason": "Icarus compile failed",
        "raw_output": full_output,
        "returncode": process.returncode
    }


def build_tool_feedback(problem_id: str, tool_result: Dict[str, Any]) -> str:
    return f"""
Your previous SystemVerilog solution for {problem_id} failed the tool check.

Regenerate the full structured RTL solution and fix the issues below.

Requirements for this revision:
- Keep the same problem requirements and interface.
- Keep the required module split.
- Keep the exact required module names.
- Fix all syntax, elaboration, compile, and wiring problems.
- Each signal must have exactly one procedural driver.
- Do not leave placeholder modules.

Tool output:
{tool_result["raw_output"]}
""".strip()


def run_tool_pipeline(
    problem_id: str,
    verbose: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_tool_retries: int = DEFAULT_TOOL_RETRIES
):
    feedback = None
    tool_history = []
    last_generated_solution = None

    for attempt_index in range(max_tool_retries + 1):
        if verbose:
            print(f"\nGenerating RTL for {problem_id} (attempt {attempt_index + 1})...")

        generated_solution = generate_solution(problem_id, extra_feedback=feedback)
        last_generated_solution = generated_solution

        naming_error = enforce_expected_names(problem_id, generated_solution)
        if naming_error is not None:
            tool_result = {
                "pass": False,
                "reason": naming_error,
                "raw_output": naming_error,
                "returncode": None
            }
            tool_history.append(tool_result)

            if attempt_index == max_tool_retries:
                return generated_solution, {
                    "pass": False,
                    "details": {},
                    "reason": naming_error
                }, tool_history

            feedback = build_tool_feedback(problem_id, tool_result)
            continue

        rtl_filenames = write_solution_files(problem_id, generated_solution)
        tool_result = run_iverilog_check(problem_id, rtl_filenames, verbose=verbose)
        tool_history.append(tool_result)

        if tool_result["pass"]:
            verifier_solution: RTLSolution = convert_to_verifier_solution(generated_solution)
            verification_result = verify(
                problem_id=problem_id,
                solution=verifier_solution,
                verbose=verbose,
                timeout_seconds=timeout_seconds
            )
            return generated_solution, verification_result, tool_history

        if attempt_index == max_tool_retries:
            return generated_solution, {
                "pass": False,
                "details": {},
                "reason": f"Tool stage failed after {max_tool_retries + 1} attempts: {tool_result['reason']}"
            }, tool_history

        feedback = build_tool_feedback(problem_id, tool_result)

    return last_generated_solution, {
        "pass": False,
        "details": {},
        "reason": "Unexpected tool pipeline failure"
    }, tool_history


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate RTL, run Icarus as a tool, then verify with Vivado."
    )
    parser.add_argument(
        "--problem",
        type=str,
        help="Problem ID to solve: P1, P2, P3, P4, or P5"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print tool and Vivado output"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Vivado simulation timeout in seconds"
    )
    parser.add_argument(
        "--tool-retries",
        type=int,
        default=DEFAULT_TOOL_RETRIES,
        help="Maximum number of tool-fix retries"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.problem is not None:
        problem_id = normalize_problem_id(args.problem)
    else:
        problem_id = prompt_for_problem_id()

    generated_solution, verification_result, tool_history = run_tool_pipeline(
        problem_id=problem_id,
        verbose=args.verbose,
        timeout_seconds=args.timeout,
        max_tool_retries=args.tool_retries
    )

    if generated_solution is not None:
        print_solution_summary(problem_id, generated_solution)

    print("\nTool history:")
    for tool_index, tool_result in enumerate(tool_history, start=1):
        print(f"Attempt {tool_index}: {tool_result['reason']}")

    print("\nVerification result:")
    print(verification_result)


if __name__ == "__main__":
    main()
