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
    memory_file: Optional[RTLFile] = None
    pointer_file: Optional[RTLFile] = None
    selector_file: Optional[RTLFile] = None
    decoder_file: Optional[RTLFile] = None
    accumulator_file: Optional[RTLFile] = None
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
""",
# =========================
# FAMILY B — Memory-Centric RTL Systems
# =========================

"P6": """
You are generating a complete SystemVerilog RTL solution for Problem P6.

Task:
Design and implement an 8-entry stack (LIFO) with 8-bit data width.

The solution must include exactly 5 RTL files:
1. top.sv
2. control.sv
3. datapath.sv
4. memory.sv
5. pointer.sv

Required schema mapping:
- top.sv -> top_file
- control.sv -> control_file
- datapath.sv -> datapath_file
- memory.sv -> memory_file
- pointer.sv -> pointer_file

Architecture requirements:
- top_p6 must only instantiate and connect submodules.
- control_p6 must generate push/pop control decisions and status behavior.
- datapath_p6 must coordinate memory and pointer modules.
- memory_p6 must store the 8 stack entries.
- pointer_p6 must maintain the stack pointer / count.
- Do not collapse memory or pointer logic into top.
- Do not leave any required module empty.

Top-level interface:
The top module must be named top_p6 and must include exactly:
- input logic clk
- input logic reset
- input logic push_en
- input logic pop_en
- input logic [7:0] data_in
- output logic [7:0] data_out
- output logic full
- output logic empty
- output logic done

Behavior requirements:
- reset is active high and clears stack state.
- push_en pushes data_in only when stack is not full.
- pop_en pops the most recently pushed value only when stack is not empty.
- LIFO order must be preserved.
- full is 1 when the stack contains 8 entries.
- empty is 1 when the stack contains 0 entries.
- done must assert combinationally during the same cycle as a valid push/pop request.
- Invalid push when full must not change state.
- Invalid pop when empty must not change state.
- If push_en and pop_en are both high in the same cycle, define and document a simple behavior. Prefer pop first, then push, or ignore simultaneous operations.
- All state updates must happen on the rising edge of clk.
- data_out should hold the popped value after a valid pop.

Strict RTL rules:
- Use synthesizable SystemVerilog only.
- No classes, dynamic arrays, DPI, vendor IP, or unsynthesizable constructs.
- Each signal must be driven by exactly one process.
- Do not mix blocking and nonblocking assignments for the same signal.
- Use clear comments explaining stack pointer behavior, full/empty detection, and invalid operation handling.

Required module names:
- top_p6
- control_p6
- datapath_p6
- memory_p6
- pointer_p6

Return a structured solution matching the schema exactly.
Do not return pseudocode.
Do not omit module bodies.

Icarus compatibility requirements:
- Use simple SystemVerilog syntax compatible with Icarus Verilog.
- Do not use type casts like logic'(expr), packed type casts, comma expressions, streaming operators, or inside expressions.
- Use simple always_comb, always_ff, assign statements, and case statements only.
- Do not use clever compact expressions.
- Do not assign the same output in both always_comb and always_ff.
""",

"P7": """
You are generating a complete SystemVerilog RTL solution for Problem P7.

Task:
Design and implement an 8-entry FIFO queue with 8-bit data width.

The solution must include exactly 5 RTL files:
1. top.sv
2. control.sv
3. datapath.sv
4. memory.sv
5. pointer.sv

Required schema mapping:
- top.sv -> top_file
- control.sv -> control_file
- datapath.sv -> datapath_file
- memory.sv -> memory_file
- pointer.sv -> pointer_file

Architecture requirements:
- top_p7 must only instantiate and wire submodules.
- control_p7 must decide when reads and writes are allowed.
- datapath_p7 must coordinate memory access and pointer updates.
- memory_p7 must implement the FIFO storage.
- pointer_p7 must maintain read pointer, write pointer, and count.
- Do not collapse all FIFO logic into one module.
- Do not leave any required module empty.
Important wiring rule:
- top_p7 must instantiate only control_p7 and datapath_p7.
- top_p7 must not instantiate memory_p7 or pointer_p7 directly.
- memory_p7 and pointer_p7 must be instantiated only inside datapath_p7.
- The top-level outputs data_out, full, and empty must be driven only by datapath_p7.
- No top-level output may be connected to outputs of more than one submodule.

Top-level interface:
The top module must be named top_p7 and must include exactly:
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
- reset is active high and clears all FIFO state.
- A write occurs only when write_en = 1 and full = 0.
- A read occurs only when read_en = 1 and empty = 0.
- Reads must return data in first-in-first-out order.
- read pointer and write pointer must wrap around correctly after index 7.
- full is 1 when the FIFO contains 8 entries.
- empty is 1 when the FIFO contains 0 entries.
- done must assert combinationally during the same cycle as a valid read/write request.
- Invalid write when full must not modify stored data or pointer state.
- Invalid read when empty must not modify pointer state.
- For simultaneous valid read and write, both operations may complete in the same cycle if the FIFO is neither empty nor full. Document the chosen behavior.
- data_out should update after a valid read and may hold its previous value otherwise.


Strict RTL rules:
- Use synthesizable SystemVerilog only.
- No vendor IP, classes, dynamic arrays, or DPI.
- Each signal must be driven by exactly one process.
- Do not assign the same register in multiple always blocks.
- Use comments explaining full/empty logic, pointer wraparound, and simultaneous read/write behavior.
- Module hierarchy requirement:
- top_p7 -> control_p7 + datapath_p7
- datapath_p7 -> memory_p7 + pointer_p7
- control_p7 must not instantiate memory_p7 or pointer_p7.

Required module names:
- top_p7
- control_p7
- datapath_p7
- memory_p7
- pointer_p7

Return a structured solution matching the schema exactly.
Do not return pseudocode.
Do not omit module bodies.

Icarus compatibility requirements:
- Use simple SystemVerilog syntax compatible with Icarus Verilog.
- Do not use type casts like logic'(expr), packed type casts, comma expressions, streaming operators, or inside expressions.
- Use simple always_comb, always_ff, assign statements, and case statements only.
- Do not use clever compact expressions.
- Do not assign the same output in both always_comb and always_ff.
""",

"P8": """
You are generating a complete SystemVerilog RTL solution for Problem P8.

Task:
Design and implement an 8-entry circular buffer that computes the sliding window sum of the most recent 4 valid 8-bit unsigned inputs.

The solution must include exactly 6 RTL files:
1. top.sv
2. control.sv
3. datapath.sv
4. memory.sv
5. pointer.sv
6. accumulator.sv

Required schema mapping:
- top.sv -> top_file
- control.sv -> control_file
- datapath.sv -> datapath_file
- memory.sv -> memory_file
- pointer.sv -> pointer_file
- accumulator.sv -> accumulator_file

Architecture requirements:
- top_p8 must only instantiate and connect submodules.
- control_p8 must generate update enables and done behavior.
- datapath_p8 must coordinate buffer memory, pointer update, and accumulator update.
- memory_p8 must store circular buffer entries.
- pointer_p8 must maintain the circular write index and valid sample count.
- accumulator_p8 must maintain the running window sum.
- Do not collapse memory, pointer, or accumulator logic into top.
- Do not leave any required module empty.

Top-level interface:
The top module must be named top_p8 and must include exactly:
- input logic clk
- input logic reset
- input logic in_valid
- input logic [7:0] data_in
- output logic [10:0] window_sum
- output logic window_valid
- output logic done

Behavior requirements:
- reset is active high and clears buffer, pointer, count, sum, window_valid, and done.
- data_in is accepted only when in_valid = 1.
- The design stores each accepted input into the circular buffer.
- The circular write pointer must wrap around correctly after index 7.
- window_sum must equal the sum of the most recent 4 accepted values.
- Before 4 valid samples have arrived, window_valid must be 0.
- Once at least 4 valid samples have arrived, window_valid must be 1.
- After the first 4 valid samples, every new accepted sample must add the new value and subtract the value leaving the 4-sample window.
- Gap cycles where in_valid = 0 must not change buffer contents, pointer, count, sum, or window_valid.
- done must be combinational, not registered.
- done must assert during the same cycle that in_valid = 1 and the input is accepted.
- done must be 0 whenever in_valid = 0.
- Do not update done inside an always_ff block.
- Prefer generating done in control_p8 using combinational logic.
- Use unsigned arithmetic for data_in and window_sum.
- Maximum sum is 4 * 255 = 1020, so window_sum must be at least 10 bits. Use 11 bits for safety.

Strict RTL rules:
- Use synthesizable SystemVerilog only.
- No dynamic arrays, classes, DPI, vendor IP, or unsynthesizable constructs.
- Each signal must be driven by exactly one process.
- Do not mix blocking and nonblocking assignments for the same signal.
- Use comments explaining window filling, wraparound, and subtract-old/add-new behavior.

Required module names:
- top_p8
- control_p8
- datapath_p8
- memory_p8
- pointer_p8
- accumulator_p8

Return a structured solution matching the schema exactly.
Do not return pseudocode.
Do not omit module bodies.

Icarus compatibility requirements:
- Use simple SystemVerilog syntax compatible with Icarus Verilog.
- Do not use type casts like logic'(expr), packed type casts, comma expressions, streaming operators, or inside expressions.
- Use simple always_comb, always_ff, assign statements, and case statements only.
- Do not use clever compact expressions.
- Do not assign the same output in both always_comb and always_ff.
""",

"P9": """
You are generating a complete SystemVerilog RTL solution for Problem P9.

Task:
Design and implement a 4-entry register file with 8-bit registers, one synchronous write port, and one combinational read port.

The solution must include exactly 5 RTL files:
1. top.sv
2. control.sv
3. datapath.sv
4. memory.sv
5. decoder.sv

Required schema mapping:
- top.sv -> top_file
- control.sv -> control_file
- datapath.sv -> datapath_file
- memory.sv -> memory_file
- decoder.sv -> decoder_file

Module hierarchy requirement:
- top_p9 must instantiate only control_p9 and datapath_p9.
- datapath_p9 must instantiate memory_p9 and decoder_p9.
- top_p9 must not instantiate memory_p9 or decoder_p9 directly.
- control_p9 must not instantiate memory_p9 or decoder_p9.
- read_data must be driven only by datapath_p9.
- done must be driven only by control_p9 or by a single combinational assignment in top_p9, not by multiple modules.

Top-level interface:
The top module must be named top_p9 and must include exactly:
- input logic clk
- input logic reset
- input logic write_en
- input logic [1:0] write_addr
- input logic [7:0] write_data
- input logic [1:0] read_addr
- output logic [7:0] read_data
- output logic done

Behavior requirements:
- reset is active high and clears all 4 registers to 0.
- When write_en = 1, write_data is written into the register selected by write_addr on the rising clock edge.
- When write_en = 0, no register may change.
- read_data must reflect the current value stored at read_addr.
- The read port must be combinational, not registered.
- If reading and writing the same address in the same cycle, read_data should show the old value before the clock edge and the new value after the clock edge.
- done must be combinational, not registered.
- done must assert during the same cycle that write_en = 1.
- done must be 0 whenever write_en = 0.
- Do not update done inside an always_ff block.
- No unintended register should be overwritten during a write.
- decoder_p9 must generate exactly one active write enable when write_en = 1.
- decoder_p9 must generate all-zero write enables when write_en = 0.

Strict RTL rules:
- Use synthesizable SystemVerilog only.
- No vendor IP, classes, dynamic arrays, or DPI.
- Each signal must be driven by exactly one process.
- Do not assign the register array from multiple always blocks.
- Use comments explaining address decoding, write behavior, and read-during-write behavior.

Required module names:
- top_p9
- control_p9
- datapath_p9
- memory_p9
- decoder_p9

Return a structured solution matching the schema exactly.
Do not return pseudocode.
Do not omit module bodies.

Icarus compatibility requirements:
- Use simple SystemVerilog syntax compatible with Icarus Verilog.
- Do not use type casts like logic'(expr), packed type casts, comma expressions, streaming operators, or inside expressions.
- Use simple always_comb, always_ff, assign statements, and case statements only.
- Do not use clever compact expressions.
- Do not assign the same output in both always_comb and always_ff.
""",

"P10": """
You are generating a complete SystemVerilog RTL solution for Problem P10.

Task:
Design and implement a 4-entry priority buffer that stores 8-bit values and outputs the highest stored valid value.

The solution must include exactly 5 RTL files:
1. top.sv
2. control.sv
3. datapath.sv
4. memory.sv
5. selector.sv

Required schema mapping:
- top.sv -> top_file
- control.sv -> control_file
- datapath.sv -> datapath_file
- memory.sv -> memory_file
- selector.sv -> selector_file

Architecture requirements:
- top_p10 must instantiate only control_p10 and datapath_p10.
- datapath_p10 must instantiate memory_p10 and selector_p10.
- top_p10 must not instantiate memory_p10 or selector_p10 directly.
- control_p10 must not instantiate memory_p10 or selector_p10.
- control_p10 must generate operation enables and done behavior.
- datapath_p10 must own and update the stored entries and valid bits through memory_p10.
- memory_p10 must store the 4 values and 4 valid bits.
- selector_p10 must choose the highest valid value from memory_p10 outputs.
- data_out, full, and empty must be driven only by datapath_p10.
- done must be driven only by control_p10 or by one combinational assignment in top_p10.
- Do not collapse priority selection into top or control.
- Do not leave any required module empty.

Top-level interface:
The top module must be named top_p10 and must include exactly:
- input logic clk
- input logic reset
- input logic insert_en
- input logic remove_en
- input logic [7:0] data_in
- output logic [7:0] data_out
- output logic full
- output logic empty
- output logic done

Behavior requirements:
- reset is active high and clears all entries and valid bits.
- insert_en inserts data_in into the first available empty slot when the buffer is not full.
- remove_en removes the current highest valid value when the buffer is not empty.
- data_out must show the highest valid stored value.
- If multiple entries have the same highest value, choose the lowest index entry as the tie-breaker.
- full is 1 when all 4 entries are valid.
- empty is 1 when no entries are valid.
- Invalid insert when full must not modify state.
- Invalid remove when empty must not modify state.
- If insert_en and remove_en are both high in the same cycle, define and document a simple deterministic behavior. Prefer remove first, then insert if space is available.
- selector_p10 must ignore invalid entries.
- data_out may be 0 when empty.
- done must be combinational, not registered.
- done must assert during the same cycle that a valid insert or valid remove request is accepted.
- done must be 0 when insert_en/remove_en are low, or when the requested operation is invalid.
- Do not update done inside an always_ff block.

Strict RTL rules:
- Use synthesizable SystemVerilog only.
- No dynamic arrays, classes, DPI, vendor IP, or unsynthesizable constructs.
- Each signal must be driven by exactly one process.
- Do not mix blocking and nonblocking assignments for the same signal.
- Use comments explaining valid-bit tracking, priority selection, tie-breaking, and invalid operation handling.
Signal ownership rules:
- valid bits must be assigned in only one always_ff block, preferably inside memory_p10.
- stored values must be assigned in only one always_ff block, preferably inside memory_p10.
- data_out must not be assigned in multiple modules.
- full and empty must not be assigned in multiple modules.
- done must not be assigned in datapath_p10 if control_p10 already drives it.

Required module names:
- top_p10
- control_p10
- datapath_p10
- memory_p10
- selector_p10

Return a structured solution matching the schema exactly.
Do not return pseudocode.
Do not omit module bodies.

Icarus compatibility requirements:
- Use simple SystemVerilog syntax compatible with Icarus Verilog.
- Do not use type casts like logic'(expr), packed type casts, comma expressions, streaming operators, or inside expressions.
- Use simple always_comb, always_ff, assign statements, and case statements only.
- Do not use clever compact expressions.
- Do not assign the same output in both always_comb and always_ff.

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


def convert_to_verifier_solution(generated_solution):
    return RTLSolution(
        top_file=generated_solution.top_file,
        control_file=generated_solution.control_file,
        datapath_file=generated_solution.datapath_file,
        memory_file=generated_solution.memory_file,
        pointer_file=generated_solution.pointer_file,
        selector_file=generated_solution.selector_file,
        decoder_file=generated_solution.decoder_file,
        accumulator_file=generated_solution.accumulator_file,
        extra_files=generated_solution.extra_files,
        notes=generated_solution.assumptions_summary,
    )


def run_pipeline(
    problem_id: str,
    verbose: bool = False,
    timeout_seconds: int = 60
):
    generated_solution, verification_result, tool_history = run_tool_pipeline(
        problem_id=problem_id,
        verbose=verbose,
        timeout_seconds=timeout_seconds,
        max_tool_retries=0   # IMPORTANT: disables refinement
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
