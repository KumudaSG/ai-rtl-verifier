`timescale 1ns / 1ps

module tb_p1;

    logic signed [7:0] A;
    logic signed [7:0] B;
    logic signed [7:0] Sum;
    logic Overflow;

    top_p1 dut (
        .A(A),
        .B(B),
        .Sum(Sum),
        .Overflow(Overflow)
    );

    task run_test(
        input string test_name,
        input logic signed [7:0] test_a,
        input logic signed [7:0] test_b,
        input logic signed [7:0] expected_sum,
        input logic expected_overflow
    );
    begin
        A = test_a;
        B = test_b;

        #1;

        if (Sum === expected_sum) begin
            $display("CHECK:%s_result:PASS", test_name);
        end
        else begin
            $display("CHECK:%s_result:FAIL", test_name);
            $display("  Expected Sum = %0d, Got Sum = %0d", expected_sum, Sum);
        end

        if (Overflow === expected_overflow) begin
            $display("CHECK:%s_overflow:PASS", test_name);
        end
        else begin
            $display("CHECK:%s_overflow:FAIL", test_name);
            $display("  Expected Overflow = %0d, Got Overflow = %0d", expected_overflow, Overflow);
        end
    end
    endtask

    initial begin
        $display("Starting tb_p1...");

        // basic positive addition
        run_test("basic_add", 8'sd10, 8'sd20, 8'sd30, 1'b0);

        // adding 1+1, set expected = 2  
        run_test("manual_pass", 8'sd1, 8'sd1, 8'sd2, 1'b0);  

        // adding 1+1, set expected = 5 so it will fail.
        run_test("manual_fail", 8'sd1, 8'sd1, 8'sd5, 1'b0);

        // mixed signs, no overflow
        run_test("mixed_sign", 8'sd20, -8'sd5, 8'sd15, 1'b0);

        // zero case
        run_test("zero_case", 8'sd0, 8'sd0, 8'sd0, 1'b0);

        // positive overflow: 127 + 1 = -128 in 8-bit signed
        run_test("positive_overflow", 8'sd127, 8'sd1, -8'sd128, 1'b1);

        // negative overflow: -128 + (-1) = 127 in 8-bit signed wraparound
        run_test("negative_overflow", -8'sd128, -8'sd1, 8'sd127, 1'b1);

        // boundary without overflow
        run_test("boundary_no_overflow", 8'sd60, 8'sd40, 8'sd100, 1'b0);

        $display("CHECK:reached_end_of_testbench:PASS");
        $finish;
    end

endmodule