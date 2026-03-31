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


def verify():
    if not os.path.exists(VIVADO_PATH):
        return {
            "pass": False,
            "details": {},
            "reason": "Vivado path not found"
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

        if overall_pass:
            reason = "All checks passed"
        else:
            failed_checks = [name for name, passed in checks.items() if not passed]
            reason = "Failed checks: " + ", ".join(failed_checks)

        return {
            "overall pass": overall_pass,
            "details": checks,
            "reason": reason
        }

    except Exception as error:
        return {
            "pass": False,
            "details": {},
            "reason": f"Exception occurred: {error}"
        }


result = verify()
print("\nFinal verifier result:")
print(result)
