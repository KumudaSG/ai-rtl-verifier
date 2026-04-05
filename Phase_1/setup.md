Files setup:
1. Download all the files 
2. Create 4 new files with names: top.sv, tb_top.sv, control.sv, datapath.sv since these are the files that the LLM populates. 
3. Ensure vivado verion 2022.2 is downloaded and check in verifier.py if the path is the same. 
4. pip install the following packages:
openai==1.30.0
instructor==1.3.3
pydantic==2.7.1
python-dotenv==1.0.1

5. Create a .env file in the root directory and add it with OPENROUTER_API_KEY=your_api_key_here


How the System Works:


LLM generates RTL (top.sv, control.sv, datapath.sv)
Python writes files to disk
Vivado runs simulation via test.tcl

Testbench prints:

CHECK:<name>:PASS/FAIL
Python parses results and evaluates correctness

