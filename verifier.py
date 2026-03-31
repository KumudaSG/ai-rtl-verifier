import subprocess
import os

VIVADO_PATH = r"C:\Xilinx\Vivado\2022.2\bin\vivado.bat"

if not os.path.exists(VIVADO_PATH):
    print("ERROR: Vivado path not found")
    raise SystemExit(1)

print("Running Vivado test...")

try:
    process = subprocess.Popen(
        [VIVADO_PATH, "-mode", "batch", "-source", "test.tcl"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    if process.stdout is not None:
        for line in process.stdout:
            print(line, end="")

    process.wait()

    print("\nReturn code:", process.returncode)

    if process.returncode == 0:
        print("\nSUCCESS: Vivado connection works")
    else:
        print("\nFAIL: Vivado ran but returned error")

except Exception as error:
    print("Exception occurred:", error)
