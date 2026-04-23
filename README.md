# ai-rtl-verifier
This project explores how large language models (LLMs) can be used to generate FPGA designs and how those designs can be evaluated objectively using a reproducible, simulation-driven verification pipeline.

---

## Overview

The system connects three components into a closed loop:

1. **LLM Generation**
   - Generates SystemVerilog modules:
     - `top.sv`
     - `control.sv`
     - `datapath.sv`

2. **Simulation-Based Verification**
   - Runs testbenches in Vivado (2022.2) using batch mode
   - Executed via `test.tcl`

3. **Automated Evaluation**
   - Testbench outputs structured signals:
     ```
     CHECK:<test_name>:PASS
     CHECK:<test_name>:FAIL
     ```
   - Python parses logs and determines correctness

4. **Self-Refinement Loop **
   - LLM receives failure feedback
   - Iteratively improves RTL

---

Setup:
---

Files setup:

Download all the files

Create 4 new files with names: top.sv, tb_top.sv, control.sv, datapath.sv since these are the files that the LLM populates.

Ensure vivado verion 2022.2 is downloaded and check in verifier.py if the path is the same.

pip install the following packages: openai==1.30.0 instructor==1.3.3 pydantic==2.7.1 python-dotenv==1.0.1

Create a .env file in the root directory and add it with OPENROUTER_API_KEY=your_api_key_here

How the System Works:

LLM generates RTL (top.sv, control.sv, datapath.sv) Python writes files to disk Vivado runs simulation via test.tcl

Testbench prints:

CHECK::PASS/FAIL 

Python parses results and evaluates correctness

---

How to run?
---

'''python pipeline.py''' 
- to run a single instance


---
Project timeline:
---

Phase 1:
Building a Simulation-Based Automatic Verifier, LLM API Pipeline with Enforced Structured Output and a self-verification loop where the LLM iteratively refines its own solution based on verifier feedback.

Phase 2:
Expand the scope of the LLM pipeline by integrating various difficulty levels of problems and implementing tool integration. 

We evaluate the system in two modes: a baseline setting that measures raw LLM performance, and a tool-augmented setting that incorporates external verification.
Verilator is used in the augmented setting to provide faster, scriptable simulation, enabling quicker feedback and more efficient refinement of generated RTL.

---

References and inspirations:
1. [Spec2rtl](https://research.nvidia.com/publication/2025-06_spec2rtl-agent-automated-hardware-code-generation-complex-specifications-using)
2. [Evaluation Frameworks](https://www.evidentlyai.com/blog/llm-evaluation-framework)
3. [Verilator](https://github.com/verilator/verilator)
---


*All generated outputs were verified through simulation and not assumed to be correct.*
