import os
import re
import subprocess
from typing import List, Optional, Dict, Any
import time
from pydantic import BaseModel


VIVADO_PATH = r"C:\Xilinx\Vivado\2022.2\bin\vivado.bat"
DEFAULT_TIMEOUT_SECONDS = 60


class RTLFile(BaseModel):
    filename: str
    content: str


class RTLSolution(BaseModel):
    top_file: RTLFile
    control_file: Optional[RTLFile] = None
    datapath_file: Optional[RTLFile] = None
    extra_files: List[RTLFile] = []
    notes: Optional[str] = None


PROBLEM_CONFIGS = {
    "P1": {
        "required_files": ["top_file"],
        "testbench_file": "tb_p1.sv",
        "top_tb_module": "tb_p1",
    },
    "P2": {
        "required_files": ["top_file", "control_file", "datapath_file"],
        "testbench_file": "tb_p2.sv",
        "top_tb_module": "tb_p2",
    },
    "P3": {
        "required_files": ["top_file", "control_file", "datapath_file"],
        "testbench_file": "tb_p3.sv",
        "top_tb_module": "tb_p3",
    },
    "P4": {
        "required_files": ["top_file", "control_file", "datapath_file"],
        "testbench_file": "tb_p4.sv",
        "top_tb_module": "tb_p4",
    },
    "P5": {
        "required_files": ["top_file", "control_file", "datapath_file"],
        "testbench_file": "tb_p5.sv",
        "top_tb_module": "tb_p5",
    },
}


def parse_checks(log_text: str) -> Dict[str, bool]:
    checks = {}
    pattern = r"CHECK:([A-Za-z0-9_]+):(PASS|FAIL)"

    for match_object in re.finditer(pattern, log_text):
        check_name = match_object.group(1)
        check_result = match_object.group(2)
        checks[check_name] = (check_result == "PASS")

    return checks


def should_ignore_check(check_name: str) -> bool:
    return check_name.startswith("manual_fail")


def group_failed_checks(checks: Dict[str, bool]) -> Dict[str, List[str]]:
    grouped = {}

    for check_name, passed in checks.items():
        if passed or should_ignore_check(check_name):
            continue

        if check_name == "reached_end_of_testbench":
            grouped.setdefault("framework", []).append("testbench did not finish cleanly")
            continue

        if check_name.endswith("_done"):
            test_name = check_name[:-5]
            grouped.setdefault("done", []).append(test_name)

        elif check_name.endswith("_result"):
            test_name = check_name[:-7]
            grouped.setdefault("result", []).append(test_name)

        elif check_name.endswith("_overflow"):
            test_name = check_name[:-9]
            grouped.setdefault("overflow", []).append(test_name)

        elif check_name.endswith("_full"):
            test_name = check_name[:-5]
            grouped.setdefault("full", []).append(test_name)

        elif check_name.endswith("_empty"):
            test_name = check_name[:-6]
            grouped.setdefault("empty", []).append(test_name)

        elif check_name.endswith("_data"):
            test_name = check_name[:-5]
            grouped.setdefault("data", []).append(test_name)

        elif check_name.endswith("_valid"):
            test_name = check_name[:-6]
            grouped.setdefault("valid", []).append(test_name)

        elif check_name.endswith("_busy"):
            test_name = check_name[:-5]
            grouped.setdefault("busy", []).append(test_name)

        else:
            grouped.setdefault("other", []).append(check_name)

    return grouped


def build_reason(checks: Dict[str, bool]) -> str:
    filtered_checks = {
        check_name: passed
        for check_name, passed in checks.items()
        if not should_ignore_check(check_name)
    }

    if not filtered_checks:
        return "No non-ignored CHECK lines were parsed from simulation output"

    failed_checks = {
        check_name: passed
        for check_name, passed in filtered_checks.items()
        if not passed
    }

    if not failed_checks:
        return "All checks passed"

    grouped = group_failed_checks(filtered_checks)
    reason_parts = []

    if "done" in grouped:
        reason_parts.append(
            "Computation completion signaling failed for: " + ", ".join(grouped["done"])
        )

    if "result" in grouped:
        reason_parts.append(
            "Arithmetic result incorrect for: " + ", ".join(grouped["result"])
        )

    if "overflow" in grouped:
        reason_parts.append(
            "Overflow handling incorrect for: " + ", ".join(grouped["overflow"])
        )

    if "full" in grouped:
        reason_parts.append(
            "Full flag behavior incorrect for: " + ", ".join(grouped["full"])
        )

    if "empty" in grouped:
        reason_parts.append(
            "Empty flag behavior incorrect for: " + ", ".join(grouped["empty"])
        )

    if "data" in grouped:
        reason_parts.append(
            "Data output incorrect for: " + ", ".join(grouped["data"])
        )

    if "valid" in grouped:
        reason_parts.append(
            "Valid signal timing incorrect for: " + ", ".join(grouped["valid"])
        )

    if "busy" in grouped:
        reason_parts.append(
            "Busy signal behavior incorrect for: " + ", ".join(grouped["busy"])
        )

    if "framework" in grouped:
        reason_parts.append(
            "Framework issue: " + ", ".join(grouped["framework"])
        )

    if "other" in grouped:
        reason_parts.append(
            "Other failed checks: " + ", ".join(grouped["other"])
        )

    return " | ".join(reason_parts)


def validate_solution_for_problem(problem_id: str, solution: RTLSolution) -> Optional[str]:
    if problem_id not in PROBLEM_CONFIGS:
        return f"Unknown problem_id: {problem_id}"

    required_files = PROBLEM_CONFIGS[problem_id]["required_files"]

    for field_name in required_files:
        field_value = getattr(solution, field_name)
        if field_value is None:
            return f"Missing required file for {problem_id}: {field_name}"

    return None


def write_file(filename: str, content: str) -> None:
    with open(filename, "w", encoding="utf-8") as file_object:
        file_object.write(content)


def write_solution_files(problem_id: str, solution: RTLSolution) -> List[str]:
    problem_tag = problem_id.lower()
    written_files = []

    top_name = f"top_{problem_tag}.sv"
    write_file(top_name, solution.top_file.content)
    written_files.append(top_name)

    if solution.control_file is not None:
        control_name = f"control_{problem_tag}.sv"
        write_file(control_name, solution.control_file.content)
        written_files.append(control_name)

    if solution.datapath_file is not None:
        datapath_name = f"datapath_{problem_tag}.sv"
        write_file(datapath_name, solution.datapath_file.content)
        written_files.append(datapath_name)

    for file_index, extra_file in enumerate(solution.extra_files):
        original_name = extra_file.filename.strip() if extra_file.filename else f"extra_{file_index}.sv"
        extra_name = f"{problem_tag}_{original_name}"
        write_file(extra_name, extra_file.content)
        written_files.append(extra_name)

    return written_files



def build_tcl_script(
    problem_id: str,
    rtl_filenames: List[str],
    testbench_file: str,
    top_tb_module: str
) -> str:
    run_id = str(int(time.time()))  # simple unique ID
    project_name = f"{problem_id.lower()}_{run_id}_proj"
    project_dir = f"./runs/{project_name}"

    tcl_lines = []

    tcl_lines.append(f"file mkdir ./runs")
    tcl_lines.append(f"create_project {project_name} {project_dir} -part xc7a35ticsg324-1L")

    for rtl_filename in rtl_filenames:
        tcl_lines.append(f"add_files {rtl_filename}")

    tcl_lines.append(f"add_files -fileset sim_1 {testbench_file}")
    tcl_lines.append(f"set_property top {top_tb_module} [get_filesets sim_1]")
    tcl_lines.append("update_compile_order -fileset sources_1")
    tcl_lines.append("update_compile_order -fileset sim_1")
    tcl_lines.append("launch_simulation")
    tcl_lines.append("close_sim")
    tcl_lines.append("close_project")
    tcl_lines.append("quit")

    return "\n".join(tcl_lines) + "\n"


def write_test_tcl(problem_id: str, rtl_filenames: List[str]) -> str:
    config = PROBLEM_CONFIGS[problem_id]
    tcl_filename = f"test_{problem_id.lower()}.tcl"

    tcl_script = build_tcl_script(
    problem_id=problem_id,
    rtl_filenames=rtl_filenames,
    testbench_file=config["testbench_file"],
    top_tb_module=config["top_tb_module"]
    )

    write_file(tcl_filename, tcl_script)
    return tcl_filename


def run_vivado_batch(
    problem_id: str,
    tcl_filename: str,
    verbose: bool = True,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    if not os.path.exists(VIVADO_PATH):
        return {
            "pass": False,
            "details": {},
            "reason": "Vivado path not found",
            "raw_output": ""
        }

    try:
        process = subprocess.Popen(
            [VIVADO_PATH, "-mode", "batch", "-source", tcl_filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        full_output = ""

        if process.stdout is not None:
            for line in process.stdout:
                if verbose:
                    print(line, end="")
                full_output += line

        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()

            timeout_log_name = f"vivado_{problem_id.lower()}.log"
            write_file(timeout_log_name, full_output)

            return {
                "pass": False,
                "details": {},
                "reason": "Simulation timed out",
                "raw_output": full_output
            }

        log_filename = f"vivado_{problem_id.lower()}.log"
        write_file(log_filename, full_output)

        checks = parse_checks(full_output)

        if process.returncode != 0:
            return {
                "pass": False,
                "details": checks,
                "reason": f"Vivado returned error code {process.returncode}",
                "raw_output": full_output
            }

        filtered_checks = {
            check_name: passed
            for check_name, passed in checks.items()
            if not should_ignore_check(check_name)
        }

        overall_pass = all(filtered_checks.values()) if filtered_checks else False
        reason = build_reason(checks)

        return {
            "pass": overall_pass,
            "details": checks,
            "reason": reason,
            "raw_output": full_output
        }

    except Exception as error:
        return {
            "pass": False,
            "details": {},
            "reason": f"Exception occurred: {error}",
            "raw_output": ""
        }


def verify_p1(
    solution: RTLSolution,
    verbose: bool = True,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    return verify_problem("P1", solution, verbose=verbose, timeout_seconds=timeout_seconds)


def verify_p2(
    solution: RTLSolution,
    verbose: bool = True,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    return verify_problem("P2", solution, verbose=verbose, timeout_seconds=timeout_seconds)


def verify_p3(
    solution: RTLSolution,
    verbose: bool = True,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    return verify_problem("P3", solution, verbose=verbose, timeout_seconds=timeout_seconds)


def verify_p4(
    solution: RTLSolution,
    verbose: bool = True,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    return verify_problem("P4", solution, verbose=verbose, timeout_seconds=timeout_seconds)


def verify_p5(
    solution: RTLSolution,
    verbose: bool = True,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    return verify_problem("P5", solution, verbose=verbose, timeout_seconds=timeout_seconds)


def verify_problem(
    problem_id: str,
    solution: RTLSolution,
    verbose: bool = True,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    validation_error = validate_solution_for_problem(problem_id, solution)
    if validation_error is not None:
        return {
            "pass": False,
            "details": {},
            "reason": validation_error
        }

    try:
        rtl_filenames = write_solution_files(problem_id, solution)
        tcl_filename = write_test_tcl(problem_id, rtl_filenames)
    except Exception as error:
        return {
            "pass": False,
            "details": {},
            "reason": f"Failed to prepare verification files: {error}"
        }

    if verbose:
        print(f"Running Vivado test for {problem_id}...")

    result = run_vivado_batch(
        problem_id=problem_id,
        tcl_filename=tcl_filename,
        verbose=verbose,
        timeout_seconds=timeout_seconds
    )

    return {
        "pass": result["pass"],
        "details": result["details"],
        "reason": result["reason"]
    }


def verify(
    problem_id: str,
    solution: RTLSolution,
    verbose: bool = True,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    if problem_id == "P1":
        return verify_p1(solution, verbose=verbose, timeout_seconds=timeout_seconds)

    if problem_id == "P2":
        return verify_p2(solution, verbose=verbose, timeout_seconds=timeout_seconds)

    if problem_id == "P3":
        return verify_p3(solution, verbose=verbose, timeout_seconds=timeout_seconds)

    if problem_id == "P4":
        return verify_p4(solution, verbose=verbose, timeout_seconds=timeout_seconds)

    if problem_id == "P5":
        return verify_p5(solution, verbose=verbose, timeout_seconds=timeout_seconds)

    return {
        "pass": False,
        "details": {},
        "reason": f"Unknown problem_id: {problem_id}"
    }
