import os
from pydantic import BaseModel, Field
from openai import OpenAI
import instructor

from dotenv import load_dotenv

from verifier import verify
load_dotenv() 


class RTLFile(BaseModel):
    filename: str = Field(description="Filename including extension, e.g. top.sv")
    content: str = Field(description="Complete SystemVerilog source code for this file")


class RTLSolution(BaseModel):
    top_module_name: str = Field(description="Name of the top module")
    control_module_name: str = Field(description="Name of the control module")
    datapath_module_name: str = Field(description="Name of the datapath module")

    top_file: RTLFile
    control_file: RTLFile
    datapath_file: RTLFile

    assumptions_summary: str = Field(
        description="Short summary of design assumptions about overflow, counting, reset, and done behavior"
    )


OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

MODEL_NAME = "openai/gpt-5.4"  # Replace with the exact model ID you are using

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://github.com/yourusername/ai-rtl-verifier",
        "X-Title": "ai-rtl-verifier",
    },
)

client = instructor.patch(client)


PROBLEM_PROMPT = """
You are generating a complete SystemVerilog RTL solution for an FPGA design task.

Task:
Design and implement a finite state machine-based SystemVerilog design to multiply x_count number of 8-bit signed two's complement numbers. The final result shall be produced as a signed 32-bit output.

The solution must include exactly 3 RTL files:
1. top.sv
2. control.sv
3. datapath.sv

Architecture requirements:
- The implementation must be split into exactly 2 modules excluding the top-level module:
  1. Control module: implements the FSM and control logic
  2. Datapath module: performs arithmetic operations and stores intermediate/final results
- The top-level module must instantiate both the control module and the datapath module and connect them correctly.
- The top-level module must act only as an integration/wiring module and must not implement the full multiplication behavior by itself.
- The control and datapath modules must have distinct responsibilities. Do not leave either submodule empty.

Top-level interface requirements:
The top module must be named `top` and must include exactly these signals:
- input logic clk
- input logic reset
- input logic [10:0] x_count
- input logic signed [7:0] in_data
- input logic in_valid
- output logic signed [31:0] result
- output logic overflow
- output logic done

Functional requirements:
- The design shall multiply exactly x_count valid signed 8-bit operands.
- Operands arrive one at a time on `in_data`.
- An operand shall only be accepted on a cycle where `in_valid = 1`.
- The running product shall be initialized appropriately for multiplication.
- The `done` signal shall assert when the computation is complete.
- The `result` output shall be a signed 32-bit value.
- The `overflow` signal shall indicate when the true mathematical product exceeds the signed 32-bit range.
- If overflow occurs, document the implemented behavior clearly in comments.

Design requirements:
- Use synthesizable SystemVerilog only for RTL modules.
- Do not use vendor IP.
- Do not use dynamic arrays, classes, DPI, or other non-synthesizable constructs.
- Include `timescale directives in the RTL files.
- Include clear comments describing design assumptions, especially for:
  - overflow handling
  - reset behavior
  - operand counting
  - done behavior
  - any sign extension or bit growth decisions

Output requirements:
Return a structured solution matching the schema.
The response must provide:
- top_module_name
- control_module_name
- datapath_module_name
- top_file
- control_file
- datapath_file
- assumptions_summary

Each RTL file must contain complete compilable SystemVerilog code.
Do not return pseudocode.
Do not omit module bodies.
Do not collapse the entire design into the top module.

"""


def generate_solution() -> RTLSolution:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_model=RTLSolution,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are an expert FPGA and SystemVerilog engineer. Return only a valid structured solution.",
            },
            {
                "role": "user",
                "content": PROBLEM_PROMPT,
            },
        ],
        max_retries=2,
    )
    return response


def main():
    solution = generate_solution()

    print("\nStructured solution received.\n")
    print("Top module:", solution.top_module_name)
    print("Control module:", solution.control_module_name)
    print("Datapath module:", solution.datapath_module_name)

    result = verify(solution)

    print("\nVerification result:")
    print(result)


if __name__ == "__main__":
    main()
