import subprocess
import os
import re


VIVADO_PATH = r"C:\Xilinx\Vivado\2022.2\bin\vivado.bat"


def parse_checks(log_text):
    checks = {}
    pattern = r"CHECK:([A-Za-z0-9_]+):(PASS|FAIL)"

    for match in re.finditer(pattern, log_text):
        check_name = match.group(1)
        check_result = match.group(2)
        checks[check_name] = (check_result == "PASS")

    return checks


def write_solution_files(solution):
    with open("top.sv", "w", encoding="utf-8") as file_object:
        file_object.write(solution.top_file.content)

    with open("control.sv", "w", encoding="utf-8") as file_object:
        file_object.write(solution.control_file.content)

    with open("datapath.sv", "w", encoding="utf-8") as file_object:
        file_object.write(solution.datapath_file.content)


def group_failed_checks(checks):
    grouped = {}

    for check_name, passed in checks.items():
        if passed:
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

        else:
            grouped.setdefault("other", []).append(check_name)

    return grouped


def build_reason(checks):
    if not checks:
        return "No CHECK lines were parsed from simulation output"

    failed_checks = {name: passed for name, passed in checks.items() if not passed}

    if not failed_checks:
        return "All checks passed"

    grouped = group_failed_checks(checks)

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

    if "framework" in grouped:
        reason_parts.append(
            "Framework issue: " + ", ".join(grouped["framework"])
        )

    if "other" in grouped:
        reason_parts.append(
            "Other failed checks: " + ", ".join(grouped["other"])
        )

    return " | ".join(reason_parts)


def verify(solution, verbose= True):
    if not os.path.exists(VIVADO_PATH):
        return {
            "pass": False,
            "details": {},
            "reason": "Vivado path not found"
        }

    try:
        write_solution_files(solution)
    except Exception as error:
        return {
            "pass": False,
            "details": {},
            "reason": f"Failed to write RTL files: {error}"
        }

    print("Running Vivado test...")

    try:
        process = subprocess.Popen(
            [VIVADO_PATH, "-mode", "batch", "-source", "test.tcl"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        full_output = ""

        if process.stdout is not None:
            for line in process.stdout:
                print(line, end="")
                if verbose:
                    print(line, end="") 
                full_output += line

        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            process.kill()
            return {
                "pass": False,
                "details": {},
                "reason": "Simulation timed out"
            }

        checks = parse_checks(full_output)

        if process.returncode != 0:
            return {
                "pass": False,
                "details": checks,
                "reason": f"Vivado returned error code {process.returncode}"
            }

        overall_pass = all(checks.values()) if checks else False
        reason = build_reason(checks)

        return {
            "pass": overall_pass,
            "details": checks,
            "reason": reason
        }

    except Exception as error:
        return {
            "pass": False,
            "details": {},
            "reason": f"Exception occurred: {error}"
        }
