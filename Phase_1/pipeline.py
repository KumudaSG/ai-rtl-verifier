from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
from openai import OpenAI
import instructor

from verifier import verify


load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if OPENROUTER_API_KEY is None:
    raise ValueError("OPENROUTER_API_KEY not found in environment")


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


MODEL_NAME = "openai/gpt-5.4"   # replace with exact model name if needed

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
  2. Datapath module: performs arithmetic operations and stores intermediate and final results
- The top-level module must instantiate both the control module and the datapath module and connect them correctly.
- The top-level module must act only as an integration and wiring module and must not implement the full multiplication behavior by itself.
- The control and datapath modules must have distinct responsibilities.
- Do not leave either submodule empty.
- The control module must generate control signals for the datapath rather than duplicating datapath logic.
- The datapath module must not independently implement the FSM.

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

Input protocol requirements:
- `in_data` carries one signed 8-bit operand at a time.
- `in_valid` indicates whether the value currently present on `in_data` is valid and should be consumed.
- A new operand is presented by the environment on a rising clock edge where `in_valid = 1`.
- The design must only sample and process `in_data` on cycles where `in_valid = 1`.
- When `in_valid = 0`, the value on `in_data` must be ignored and must not affect the result, operand counter, overflow flag, or completion logic.
- One operand arrives per valid cycle. There is never more than one operand per cycle.
- Valid input operands may arrive on consecutive cycles or may be separated by gap cycles where `in_valid = 0`.
- The design must correctly handle both back-to-back valid operands and gaps between valid operands.
- The total number of valid operands to consume is exactly `x_count`.

System behavior requirements:
- A computation begins after reset is deasserted and valid operands start arriving.
- The design shall process exactly `x_count` valid operands.
- The running product must be initialized to 1 at the start of each new computation.
- The datapath must multiply each accepted operand into the running product sequentially.
- The internal operand counter must count only accepted operands, meaning only cycles where `in_valid = 1`.
- The computation is complete only after exactly `x_count` valid operands have been accepted and processed.
- The `done` signal shall assert when the computation is complete.
- `done` should behave as a completion signal and should not assert early before all required operands are consumed.
- The `result` output shall hold the final signed 32-bit result of the completed computation.
- The `overflow` signal shall indicate when the true mathematical product exceeds the signed 32-bit signed range.

Result and overflow requirements:
- Treat `result` as a signed 32-bit two's complement value.
- If the exact mathematical product exceeds the signed 32-bit range, set `overflow = 1`.
- In overflow cases, store the truncated or wrapped 32-bit two's complement result in `result`.
- Document the chosen overflow behavior clearly in comments and make the RTL behavior consistent with those comments.

Reset behavior requirements:
- `reset` is active high.
- When `reset = 1`, all internal FSM state, counters, control outputs, and datapath registers must return to a known idle state.
- On reset, `done` must be cleared.
- On reset, `overflow` must be cleared.
- On reset, any partially completed multiplication must be discarded.
- After reset is deasserted, the design should wait for valid input operands.

Expected FSM behavior:
- The control module should have a clear idle or waiting behavior before operands are processed.
- The control module should track progress until `x_count` valid operands have been consumed.
- Once the required operands are consumed, the control module should drive completion behavior and assert `done`.
- The FSM should be simple, synthesizable, and easy to understand.

Design requirements:
- Use synthesizable SystemVerilog only.
- Do not use vendor IP.
- Do not use dynamic arrays, classes, DPI, or other non-synthesizable constructs.
- Include `timescale directives in the RTL files.
- Include clear comments describing assumptions.
- Include comments explaining:
  - how `in_valid` controls operand acceptance
  - when `in_data` is sampled
  - how operands are counted
  - how the running product is initialized
  - how `done` is asserted
  - how overflow is detected and handled
  - any assumptions about behavior after completion

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
Do not leave the control or datapath module as placeholders.
"""


def generate_solution() -> RTLSolution:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_model=RTLSolution,
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": "You are an expert FPGA and SystemVerilog engineer. Return only a valid structured solution."
            },
            {
                "role": "user",
                "content": PROBLEM_PROMPT
            }
        ],
        max_retries=2,
    )
    return response


def run_pipeline():
    solution = generate_solution()
    verification_result = verify(solution, verbose = False)
    return solution, verification_result


def main():
    solution, verification_result = run_pipeline()

    print("\nStructured solution received.")
    print("Top module:", solution.top_module_name)
    print("Control module:", solution.control_module_name)
    print("Datapath module:", solution.datapath_module_name)

    print("\nVerification result:")
    print(verification_result)


if __name__ == "__main__":
    main()