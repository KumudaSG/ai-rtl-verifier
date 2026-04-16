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

The top module must be named top_p1.
The control module must be named control_p1.
The datapath module must be named datapath_p1.
""",
    "P2": """
You are generating a complete SystemVerilog RTL solution for Problem P2.

Task:
Design and implement a finite state machine-based SystemVerilog design that computes the running sum of x_count number of signed 8-bit, two's complement inputs. The final result shall be produced as a signed 16-bit output.

A “running sum” means the design keeps an internal accumulator register. Each time a valid input arrives, that input is added to the accumulator, and the accumulator stores the updated partial sum.

Example:
If x_count = 4 and the valid input sequence is: 3, -2, 7, 1
Then the accumulator evolves as:
- start: 0
- after 3: 3
- after -2: 1
- after 7: 8
- after 1: 9
Final result = 9

The solution must include exactly 3 RTL files:
1. top.sv
2. control.sv
3. datapath.sv

Architecture requirements:
- The implementation must be split into exactly 2 modules excluding the top-level module:
  1. Control module: implements the FSM and control logic
  2. Datapath module: performs arithmetic operations and stores the running sum
- The top-level module must instantiate both the control module and the datapath module and connect them correctly.
- The top-level module must act only as an integration and wiring module.
- The control and datapath modules must have distinct responsibilities.
- Do not leave either submodule empty.
- Control should decide when inputs are accepted, when the datapath adds, and when computation is complete.
- Datapath should store the accumulator and any internal registers.

Top-level interface requirements:
The top module must be named `top_p2` and must include exactly these signals:
- input logic clk
- input logic reset
- input logic [7:0] x_count
- input logic signed [7:0] in_data
- input logic in_valid
- output logic signed [15:0] result
- output logic done

Input protocol requirements:
- in_data carries one signed 8-bit operand at a time.
- in_valid indicates whether the value on in_data is valid.
- Only sample in_data when in_valid = 1.
- Ignore in_data completely when in_valid = 0.
- Count only accepted operands (cycles where in_valid = 1).
- Process exactly x_count valid operands.
- Valid inputs may have gaps between them (cycles where in_valid = 0).

Behavior requirements:
- The running sum must start at 0 after reset.
- The datapath must add each accepted operand to the running sum.
- The accumulator must update ONLY when in_valid = 1.
- The internal operand counter must increment ONLY when in_valid = 1.
- The computation completes only after exactly x_count valid operands are processed.
- done must go high ONLY after exactly x_count valid operands are processed.
- done must NOT go high early.
- result must hold the final 16-bit signed sum after completion.
- After done = 1, the result may remain constant until reset.
- reset is active high and must clear:
  - accumulator
  - operand counter
  - FSM state
  - done signal

Assumptions:
- Assume x_count >= 1
- No separate overflow signal is required
- If the sum exceeds 16-bit range, allow normal 2’s complement wraparound and document it

STRICT RTL RULES (VERY IMPORTANT):
- Each signal must be driven by exactly one process
- Do NOT drive the same signal from multiple always blocks
- next_state must ONLY be assigned in one always_comb block
- state must ONLY be assigned in one always_ff block
- done must be driven from exactly one process
- Do NOT mix blocking and non-blocking assignments for the same signal
- Control module structure MUST be:
  - one always_ff for state register
  - one always_comb for next_state and control signals
- Use synthesizable SystemVerilog only
- Do NOT use vendor IP, DPI, classes, or non-synthesizable constructs

Output requirements:
Return a structured solution matching the schema.
- top_module_name, control_module_name, datapath_module_name must be provided
- top_file, control_file, datapath_file must all be provided
- assumptions_summary must be provided

The top module must be named `top_p2`
The control module must be named `control_p2`
The datapath module must be named `datapath_p2`

Do not return pseudocode.
Do not omit module bodies.
Do not collapse everything into the top module.
Do not leave control or datapath empty.

Accumulator semantics (VERY IMPORTANT):
- The datapath must contain a register that stores the running sum.
- That running sum register must be initialized to 0 on reset.
- On each cycle where an input is accepted (in_valid = 1 and computation is not yet complete), the datapath must update:
    running_sum <= running_sum + sign_extended(in_data)
- The running sum must NOT be cleared between accepted inputs.
- The running sum must preserve its value across gap cycles where in_valid = 0.
- The final result output must reflect the running sum register after all x_count valid inputs have been accepted.

Signed arithmetic requirements (VERY IMPORTANT):
- in_data is a signed 8-bit two's complement value.
- Before addition, in_data must be treated as a signed value and sign-extended to the accumulator width.
- The running sum register and result must be signed 16-bit values.
- Do NOT treat in_data as unsigned during addition.

Control/datapath interaction requirements:
- The control module must generate an explicit add_enable signal.
- add_enable must go high only when a valid input is being accepted.
- The datapath must update the accumulator only when add_enable = 1.
- The datapath must not independently decide when to count or add.
- The control module must generate or coordinate the operand counter.
- The operand counter must increment exactly when add_enable = 1.


""",

    "P3": """
You are generating a complete SystemVerilog RTL solution for Problem P3.

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

The top module must be named `top_p3`
The control module must be named `control_p3`
The datapath module must be named `datapath_p3`
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

STRICT RTL RULES (VERY IMPORTANT):
- Each signal must be driven by exactly one process.
- Do NOT drive the same signal from multiple always blocks.
- next_state must ONLY be assigned in a single always_comb block.
- state must ONLY be updated in a single always_ff block.
- done must be driven from exactly one process.
- Do NOT mix blocking and non-blocking assignments for the same signal.
- Control module must follow this structure:
    - always_ff for state register
    - always_comb for next_state logic


The top module must be named top_p3.
The control module must be named control_p3.
The datapath module must be named datapath_p3.
""",

    "P4": """
You are generating a complete SystemVerilog RTL solution for Problem P4.

Task:
Design and implement a finite state machine-based SystemVerilog design that counts how many times an input pulse is received. The design should increment its count only on cycles where in_valid is high and pulse_in is 1. Once the count reaches a target value, the module should assert a done signal.

The solution must include exactly 3 RTL files:
1. top.sv
2. control.sv
3. datapath.sv

Architecture requirements:
- Split the implementation into exactly 2 modules excluding the top-level module:
  1. Control: implements the FSM and control logic
  2. Datapath: stores the running count and performs comparisons
- The top-level module must instantiate both modules and only connect them.
- The control and datapath responsibilities must be separate.

Top-level interface requirements:
The top module must be named `top` and must include exactly these signals:
- input logic clk
- input logic reset
- input logic [7:0] target_count
- input logic pulse_in
- input logic in_valid
- output logic [7:0] count
- output logic done

Behavior requirements:
- Count only cycles where in_valid = 1 and pulse_in = 1.
- Ignore pulse_in completely when in_valid = 0.
- count must increment by exactly 1 per valid pulse.
- done must assert when count reaches target_count.
- reset is active high and must clear the count and state.
- Include comments explaining how valid gating works, when count increments, and how done behaves after completion.

Output requirements:
Return a structured solution matching the schema.
- top_module_name, control_module_name, datapath_module_name must be provided
- top_file, control_file, datapath_file must all be provided
- assumptions_summary must be provided

STRICT RTL RULES (VERY IMPORTANT):

- Each signal must be driven by exactly one process.
- Do NOT drive the same signal from multiple always blocks.
- next_state must ONLY be assigned in a single always_comb block.
- state must ONLY be updated in a single always_ff block.
- done must be driven from exactly one always block (not both combinational and sequential).
- Do NOT mix blocking and non-blocking assignments for the same signal.
- Control module must follow this structure:
    - always_ff for state register
    - always_comb for next_state logic

The top module must be named top_p4.
The control module must be named control_p4.
The datapath module must be named datapath_p4.

Before finalizing the solution, verify the following:
- There is no combinational path control_output -> datapath_status -> same control_output.
- Every datapath status signal is a pure function of registered datapath state and legal datapath inputs.
- Every control output is a pure function of FSM state, external inputs, and stable datapath status.

""",

    "P5": """
You are generating a complete SystemVerilog RTL solution for Problem P5.

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

The top module must be named top_p5.
The control module must be named control_p5.
The datapath module must be named datapath_p5.
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
