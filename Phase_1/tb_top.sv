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

    integer wait_cycles;

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

        @(negedge clk);
        reset = 0;
        in_valid = 0;
        in_data = 0;
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

    task send_operand(input integer value);
    begin
        @(negedge clk);
        in_valid = 1;
        in_data = value;
    end
    endtask

    task stop_input;
    begin
        @(negedge clk);
        in_valid = 0;
        in_data = 0;
    end
    endtask

    task wait_for_done(output bit got_done);
    begin
        got_done = 0;
        wait_cycles = 0;

        while (done !== 1 && wait_cycles < 100) begin
            @(posedge clk);
            wait_cycles = wait_cycles + 1;
        end

        if (done === 1)
            got_done = 1;
    end
    endtask

    task check_outputs(
        input string test_name,
        input integer expected_result,
        input bit expected_overflow
    );
        bit got_done;
        bit pass_result;
        bit pass_overflow;
        bit pass_done;
    begin
        wait_for_done(got_done);

        pass_done = got_done;
        pass_result = ($signed(result) === expected_result);
        pass_overflow = (overflow === expected_overflow);

        print_result({test_name, "_done"}, pass_done);
        print_result({test_name, "_result"}, pass_result);
        print_result({test_name, "_overflow"}, pass_overflow);

        if (!pass_result) begin
            $display("DEBUG:%s:expected_result=%0d:actual_result=%0d",
                     test_name, expected_result, $signed(result));
        end

        if (!pass_overflow) begin
            $display("DEBUG:%s:expected_overflow=%0d:actual_overflow=%0d",
                     test_name, expected_overflow, overflow);
        end
    end
    endtask

    initial begin
        clk = 0;
        reset = 0;
        x_count = 0;
        in_data = 0;
        in_valid = 0;

        // Test 1: simplest positive case
        // 5 -> 5
        do_reset();
        x_count = 1;
        send_operand(5);
        stop_input();
        check_outputs("single_positive", 5, 0);

        // Test 2: simplest negative case
        // -7 -> -7
        do_reset();
        x_count = 1;
        send_operand(-7);
        stop_input();
        check_outputs("single_negative", -7, 0);

        // Test 3: two positive operands
        // 3 * 4 = 12
        do_reset();
        x_count = 2;
        send_operand(3);
        send_operand(4);
        stop_input();
        check_outputs("two_positive", 12, 0);

        // Test 4: mixed sign operands
        // 2 * -3 * 4 = -24
        do_reset();
        x_count = 3;
        send_operand(2);
        send_operand(-3);
        send_operand(4);
        stop_input();
        check_outputs("mixed_sign", -24, 0);

        // Test 5: zero should force product to zero
        // 9 * 0 * -5 = 0
        do_reset();
        x_count = 3;
        send_operand(9);
        send_operand(0);
        send_operand(-5);
        stop_input();
        check_outputs("contains_zero", 0, 0);

        // Test 6: edge signed value
        // -128 * 1 = -128
        do_reset();
        x_count = 2;
        send_operand(-128);
        send_operand(1);
        stop_input();
        check_outputs("edge_min_8bit", -128, 0);
        
        // test manual pass
        do_reset();
        x_count = 2;
        send_operand(3);
        send_operand(4);
        stop_input();
        check_outputs("test_manual_pass", 12, 0);
        
        // test manual fail
        // Actual should be 12, but we intentionally expect 99
        // do_reset();
        // x_count = 2;
        // send_operand(3);
        // send_operand(4);
        // stop_input();
        // check_outputs("test_manual_fail", 99, 0);


        $display("CHECK:reached_end_of_testbench:PASS");
        $finish;
    end

endmodule