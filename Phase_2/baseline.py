from dotenv import load_dotenv
import argparse
import os
from typing import Optional, List, Dict

from pydantic import BaseModel, Field
from openai import OpenAI
import instructor

from verifier import verify, RTLSolution, RTLFile


load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if OPENROUTER_API_KEY is None:
    raise ValueError("OPENROUTER_API_KEY not found in environment")


MODEL_NAME = "openai/gpt-5.4"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://github.com/yourusername/ai-rtl-verifier",
        "X-Title": "ai-rtl-verifier",
    },
)

client = instructor.patch(client)


class GeneratedSolution(BaseModel):
    top_module_name: str = Field(description="Name of the top module")
    control_module_name: Optional[str] = Field(
        default=None,
        description="Name of the control module if the problem requires one"
    )
    datapath_module_name: Optional[str] = Field(
        default=None,
        description="Name of the datapath module if the problem requires one"
    )

    top_file: RTLFile
    control_file: Optional[RTLFile] = None
    datapath_file: Optional[RTLFile] = None
    extra_files: List[RTLFile] = []

    assumptions_summary: str = Field(
        description="Short summary of design assumptions and edge-case handling"
    )


SYSTEM_PROMPT = (
    "You are an expert FPGA and SystemVerilog engineer. "
    "Return only a valid structured solution that matches the schema exactly. "
    "All returned RTL must be complete, synthesizable SystemVerilog. "
    "Do not return pseudocode. Do not leave placeholder modules."
)


PROBLEM_PROMPTS: Dict[str, str] = {
    "P1": """
You are generating a complete SystemVerilog RTL solution for Problem P1.

Task:
Design and implement a combinational SystemVerilog module that adds two signed 8-bit, 2's complement numbers and produces an 8-bit signed result. The module must also detect signed overflow.

Architecture requirements:
- This problem should be implemented as a single top-level module.
- Do not create control or datapath submodules unless absolutely necessary.
- The design must be purely combinational.
- No clock, FSM, always_ff, or sequential state.

Top-level interface requirements:
The top module must be named `top` and must include exactly these signals:
- input logic signed [7:0] A
- input logic signed [7:0] B
- output logic signed [7:0] Sum
- output logic Overflow

Behavior requirements:
- Perform signed 8-bit two's complement addition.
- Overflow must assert only when both inputs have the same sign and the result has a different sign.
- The result should reflect normal 8-bit two's complement truncation behavior.
- Include comments explaining overflow detection.

Output requirements:
Return a structured solution matching the schema.
For this problem:
- top_file is required
- control_file should be null
- datapath_file should be null
- top_module_name must be provided
- assumptions_summary must be provided
""",

    "P2": """
You are generating a complete SystemVerilog RTL solution for Problem P2.

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
- The top-level module must act only as an integration and wiring module.
- The control and datapath modules must have distinct responsibilities.
- Do not leave either submodule empty.

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
- in_data carries one signed 8-bit operand at a time.
- in_valid indicates whether the value currently present on in_data is valid and should be consumed.
- Only sample in_data when in_valid = 1.
- Ignore in_data completely when in_valid = 0.
- Process exactly x_count valid operands.

Behavior requirements:
- Initialize the running product to 1 at the start of computation.
- Multiply each accepted operand into the running product sequentially.
- done asserts only after exactly x_count valid operands have been processed.
- overflow indicates when the true mathematical product exceeds signed 32-bit range.
- On overflow, keep a consistent wrapped/truncated 32-bit result and document that behavior in comments.
- reset is active high and must clear all state.

Output requirements:
Return a structured solution matching the schema.
- top_module_name, control_module_name, datapath_module_name must be provided
- top_file, control_file, datapath_file must all be provided
- assumptions_summary must be provided
""",

    "P3": """
You are generating a complete SystemVerilog RTL solution for Problem P3.

Task:
Design and implement a finite state machine-based sequential multiplier that multiplies two signed 8-bit, 2's complement numbers using a shift-and-add algorithm over multiple clock cycles.

The solution must include exactly 3 RTL files:
1. top.sv
2. control.sv
3. datapath.sv

Architecture requirements:
- Split the implementation into exactly 2 modules excluding the top-level module:
  1. Control: FSM and sequencing
  2. Datapath: shifting, addition, sign handling, and storage
- Do not use the built-in multiplication operator * for the main multiply behavior.
- The top-level module must instantiate both modules and only wire them together.

Top-level interface requirements:
The top module must be named `top` and must include exactly these signals:
- input logic clk
- input logic reset
- input logic start
- input logic signed [7:0] A
- input logic signed [7:0] B
- output logic signed [15:0] result
- output logic done
- output logic busy
- output logic overflow

Behavior requirements:
- Computation begins when start is asserted while idle.
- busy must remain high while computation is in progress.
- done must assert when the result is ready.
- The multiplication must be performed iteratively using shift-and-add style logic.
- Correctly handle signed operands.
- Include comments describing sign extension, shift direction, cycle behavior, and overflow handling.

Output requirements:
Return a structured solution matching the schema.
- top_module_name, control_module_name, datapath_module_name must be provided
- top_file, control_file, datapath_file must all be provided
- assumptions_summary must be provided
""",

    "P4": """
You are generating a complete SystemVerilog RTL solution for Problem P4.

Task:
Design and implement an 8-entry FIFO buffer with 8-bit data width using SystemVerilog.

The solution must include exactly 3 RTL files:
1. top.sv
2. control.sv
3. datapath.sv

Architecture requirements:
- Split into exactly 2 modules excluding the top-level module:
  1. Control: pointer logic, state updates, and status flag generation
  2. Datapath: FIFO storage and data movement
- The top-level module must instantiate both modules and only connect them.
- The control and datapath responsibilities must be separate.

Top-level interface requirements:
The top module must be named `top` and must include exactly these signals:
- input logic clk
- input logic reset
- input logic write_en
- input logic read_en
- input logic [7:0] data_in
- output logic [7:0] data_out
- output logic full
- output logic empty
- output logic done

Behavior requirements:
- FIFO depth must be exactly 8.
- Writes occur only when not full.
- Reads occur only when not empty.
- full and empty must always reflect the correct state.
- Pointer wraparound must work correctly.
- Define a consistent behavior for simultaneous read_en and write_en in the same cycle.
- done should indicate that a requested valid operation completed successfully.
- Include comments explaining simultaneous read/write behavior and wraparound assumptions.

Output requirements:
Return a structured solution matching the schema.
- top_module_name, control_module_name, datapath_module_name must be provided
- top_file, control_file, datapath_file must all be provided
- assumptions_summary must be provided
""",

    "P5": """
You are generating a complete SystemVerilog RTL solution for Problem P5.

Task:
Design and implement a 2-stage pipelined ALU that performs arithmetic and logic operations on signed 8-bit inputs. The output must appear exactly 2 clock cycles after a valid input is accepted.

The solution must include exactly 3 RTL files:
1. top.sv
2. control.sv
3. datapath.sv

Architecture requirements:
- Split into exactly 2 modules excluding the top-level module:
  1. Control: pipeline control and valid propagation
  2. Datapath: operations and pipeline stage storage
- The top-level module must instantiate both modules and only connect them.

Supported operations:
- 2'b00: add
- 2'b01: subtract
- 2'b10: bitwise AND
- 2'b11: bitwise OR

Top-level interface requirements:
The top module must be named `top` and must include exactly these signals:
- input logic clk
- input logic reset
- input logic in_valid
- input logic signed [7:0] A
- input logic signed [7:0] B
- input logic [1:0] Op
- output logic signed [7:0] result
- output logic overflow
- output logic out_valid

Behavior requirements:
- Implement a true 2-stage pipeline.
- An input is accepted only when in_valid is high.
- out_valid must assert exactly 2 cycles after an accepted input.
- result must correspond to the correct operation.
- overflow must be correct for add and subtract.
- overflow must remain 0 for AND and OR.
- The design must support back-to-back valid inputs on consecutive cycles.
- Include comments explaining pipeline stage partitioning and valid timing.

Output requirements:
Return a structured solution matching the schema.
- top_module_name, control_module_name, datapath_module_name must be provided
- top_file, control_file, datapath_file must all be provided
- assumptions_summary must be provided
"""
}


def normalize_problem_id(problem_id: str) -> str:
    cleaned = problem_id.strip().upper()
    if cleaned in PROBLEM_PROMPTS:
        return cleaned
    raise ValueError(f"Unsupported problem_id: {problem_id}")


def prompt_for_problem_id() -> str:
    print("Available problems: P1, P2, P3, P4, P5")
    user_choice = input("Which problem would you like to solve? ").strip()
    return normalize_problem_id(user_choice)


def build_messages(problem_id: str) -> List[Dict[str, str]]:
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": PROBLEM_PROMPTS[problem_id]
        }
    ]


def generate_solution(problem_id: str) -> GeneratedSolution:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_model=GeneratedSolution,
        temperature=0.3,
        messages=build_messages(problem_id),
        max_retries=2,
    )
    return response


def convert_to_verifier_solution(generated_solution: GeneratedSolution) -> RTLSolution:
    return RTLSolution(
        top_file=generated_solution.top_file,
        control_file=generated_solution.control_file,
        datapath_file=generated_solution.datapath_file,
        extra_files=generated_solution.extra_files,
        notes=generated_solution.assumptions_summary,
    )


def run_pipeline(
    problem_id: str,
    verbose: bool = False,
    timeout_seconds: int = 60
):
    generated_solution = generate_solution(problem_id)
    verifier_solution = convert_to_verifier_solution(generated_solution)

    verification_result = verify(
        problem_id=problem_id,
        solution=verifier_solution,
        verbose=verbose,
        timeout_seconds=timeout_seconds
    )

    return generated_solution, verification_result


def print_solution_summary(problem_id: str, generated_solution: GeneratedSolution) -> None:
    print("\nStructured solution received.")
    print("Problem:", problem_id)
    print("Top module:", generated_solution.top_module_name)

    if generated_solution.control_module_name is not None:
        print("Control module:", generated_solution.control_module_name)

    if generated_solution.datapath_module_name is not None:
        print("Datapath module:", generated_solution.datapath_module_name)

    print("\nAssumptions summary:")
    print(generated_solution.assumptions_summary)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate and verify RTL for one of the five HW3 problems.")
    parser.add_argument(
        "--problem",
        type=str,
        help="Problem ID to solve: P1, P2, P3, P4, or P5"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print Vivado output while verifying"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Vivado simulation timeout in seconds"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.problem is not None:
        problem_id = normalize_problem_id(args.problem)
    else:
        problem_id = prompt_for_problem_id()

    generated_solution, verification_result = run_pipeline(
        problem_id=problem_id,
        verbose=args.verbose,
        timeout_seconds=args.timeout
    )

    print_solution_summary(problem_id, generated_solution)

    print("\nVerification result:")
    print(verification_result)


if __name__ == "__main__":
    main()
