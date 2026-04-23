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

4. **Self-Refinement Loop**
   - LLM receives failure feedback
   - Iteratively improves RTL

---

Setup:
---

Ensure vivado verion 2022.2 is downloaded and check in verifier.py if the path is the same.

pip install the following packages: openai==1.30.0 instructor==1.3.3 pydantic==2.7.1 python-dotenv==1.0.1

Create a .env file in the root directory and add it with OPENROUTER_API_KEY=your_api_key_here

---

## How to run?
This repository is organized by phase, with each stage kept in its own folder.
The setup and execution flow are slightly different in each phase.

**Phase 1**
In Phase 1, the LLM generates and populates the RTL design files, but the required file structure must already exist.

#### What you need before running
- Python installed
- Vivado 2022.2 installed
- Required Python packages installed
- A valid `.env` file with your OpenRouter API key
- The following empty files created in the Phase 1 folder:
  - `top.sv`
  - `control.sv`
  - `datapath.sv`
- A valid testbench file: you as the user must add tests in this file for the vivado simulation to run. 
- A valid TCL script for simulation.

**Phase 2**
In Phase 2, the pipeline is more automated. You only need to provide a testbench file for each problem with the format eg: tb_p1.sv

If you want to make changes to the problems, the prompts are in pipeline.py. 

The system automatically generates:

top.sv
control.sv
datapath.sv
the TCL simulation script


---
## How the system works?

---
Project timeline:
---

Phase 1:
Building a Simulation-Based Automatic Verifier, LLM API Pipeline with Enforced Structured Output and a self-refinement loop where the LLM iteratively refines its own solution based on verifier feedback.

Phase 2 (Tool augmentation)
Expand the scope of the LLM pipeline by integrating various difficulty levels of problems and implementing tool integration. 

We evaluate the system in two modes: a baseline setting that measures raw LLM performance, and a tool-augmented setting that incorporates external verification.
Verilator is used in the augmented setting to provide faster, scriptable simulation, enabling quicker feedback and more efficient refinement of generated RTL.

Phase 3 (Concept level memory):

Using the ideas expressed in ArcMemo, we try to implement Concept level memory in our pipeline. 

---

References and inspirations:
1. [Spec2rtl](https://research.nvidia.com/publication/2025-06_spec2rtl-agent-automated-hardware-code-generation-complex-specifications-using)
2. [Evaluation Frameworks](https://www.evidentlyai.com/blog/llm-evaluation-framework)
3. [Verilator](https://github.com/verilator/verilator)
4. [ArcMemo](https://arxiv.org/abs/2509.04439)
---


*All generated outputs were verified through simulation and not assumed to be correct.*
