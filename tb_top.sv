`timescale 1ns/1ps

module tb_top;

    logic clk;
    logic reset;
    logic [10:0] x_count;
    logic signed [7:0] in_data;
    logic in_valid;

    logic signed [31:0] result;
    logic overflow;
    logic done;

    integer index;
    integer wait_cycles;

    logic signed [7:0] operand_array [0:19];

    top dut (
        .clk(clk),
        .reset(reset),
        .x_count(x_count),
        .in_data(in_data),
        .in_valid(in_valid),
        .result(result),
        .overflow(overflow),
        .done(done)
    );

    always #5 clk = ~clk;

    task do_reset;
    begin
        reset = 1;
        in_valid = 0;
        in_data = 0;
        x_count = 0;
        repeat (3) @(posedge clk);
        reset = 0;
        @(posedge clk);
    end
    endtask

    task print_result(
        input string test_name,
        input bit passed
    );
    begin
        if (passed)
            $display("CHECK:%s:PASS", test_name);
        else
            $display("CHECK:%s:FAIL", test_name);
    end
    endtask

    task run_test(
        input string test_name,
        input integer count, // how many numbers we are multiplying. 
        input integer expected_result,
        input bit expected_overflow,
        input bit insert_gaps  // helps check if in_valid is being used correctly 
    );
        bit got_done;
        bit pass_result;
        bit pass_overflow;
        bit pass_done;
    begin
        do_reset();

        x_count = count;
        got_done = 0;

        for (index = 0; index < count; index = index + 1) begin
            @(posedge clk);
            in_valid = 1;
            in_data = operand_array[index];

            if (insert_gaps && index < count - 1) begin
                @(posedge clk);
                in_valid = 0;
                in_data = 0;
            end
        end

        @(posedge clk);
        in_valid = 0;
        in_data = 0;

        wait_cycles = 0;
        while (done !== 1 && wait_cycles < 100) begin
            @(posedge clk);
            wait_cycles = wait_cycles + 1;
        end

        if (done === 1)
            got_done = 1;

        pass_result = ($signed(result) === expected_result);
        pass_overflow = (overflow === expected_overflow);
        pass_done = got_done;

        print_result({test_name, "_done"}, pass_done);
        print_result({test_name, "_result"}, pass_result);
        print_result({test_name, "_overflow"}, pass_overflow);
    end
    endtask

    initial begin
        clk = 0;
        reset = 0;
        x_count = 0;
        in_data = 0;
        in_valid = 0;



        // Test 1: single positive
        operand_array[0] = 5;
        run_test("single_positive", 1, 5, 0, 0);

        // Test 2: single negative
        operand_array[0] = -7;
        run_test("single_negative", 1, -7, 0, 0);

        // Test 3: two positives
        operand_array[0] = 3;
        operand_array[1] = 4;
        run_test("two_positive", 2, 12, 0, 0);

        // Test 4: mixed sign
        operand_array[0] = 2;
        operand_array[1] = -3;
        operand_array[2] = 4;
        run_test("mixed_sign", 3, -24, 0, 0);

        // Test 5: negative times negative
        operand_array[0] = -2;
        operand_array[1] = -3;
        run_test("neg_neg", 2, 6, 0, 0);

        // Test 6: includes zero
        operand_array[0] = 9;
        operand_array[1] = 0;
        operand_array[2] = -5;
        run_test("contains_zero", 3, 0, 0, 0);


        // Test 8: all minus ones, even count
        operand_array[0] = -1;
        operand_array[1] = -1;
        operand_array[2] = -1;
        operand_array[3] = -1;
        run_test("minus_ones_even", 4, 1, 0, 0);

        // Test 9: edge value 127
        operand_array[0] = 127;
        operand_array[1] = 1;
        run_test("edge_max_8bit", 2, 127, 0, 0);

        // Test 10: edge value -128
        operand_array[0] = -128;
        operand_array[1] = 1;
        run_test("edge_min_8bit", 2, -128, 0, 0);


        // Test 12: overflow positive
        operand_array[0] = 127;
        operand_array[1] = 127;
        operand_array[2] = 127;
        operand_array[3] = 127;
        operand_array[4] = 127;
        run_test("overflow_positive", 5, 330383694, 1, 0);

        // Test 13: overflow negative
        // operand_array[0] = -128;
        // operand_array[1] = 127;
        // operand_array[2] = 127;
        // operand_array[3] = 127;
        // operand_array[4] = 127;
        // run_test("overflow_negative", 5, -264306688, 1, 0);
        
        // ____________________________________

        // test_manual_pass 
        // we are going to test if 2x10 = 20
        operand_array[0] = 2;
        operand_array[1] = 10;
        run_test("manual_pass", 2,20,0, 1 );

        // test_manual_fail 
        // pass in 3x3 but we say we expect the value 10
        // so it will fail. 
        operand_array[0] = 3;
        operand_array[1] = 3;
        run_test("manual_fail", 2, 10, 0, 1 );
        $display("CHECK:reached_end_of_testbench:PASS");
        
        $finish;
    end

endmodule
