`timescale 1ns / 1ps

module tb_p2;

    logic clk;
    logic reset;
    logic [7:0] x_count;
    logic signed [7:0] in_data;
    logic in_valid;
    logic signed [15:0] result;
    logic done;

    top_p2 dut (
        .clk(clk),
        .reset(reset),
        .x_count(x_count),
        .in_data(in_data),
        .in_valid(in_valid),
        .result(result),
        .done(done)
    );

    initial clk = 1'b0;
    always #5 clk = ~clk;

    task apply_reset;
    begin
        reset = 1'b1;
        x_count = 8'd0;
        in_data = 8'sd0;
        in_valid = 1'b0;

        @(negedge clk);
        @(negedge clk);
        reset = 1'b0;
    end
    endtask

    task drive_idle_cycle;
    begin
        @(negedge clk);
        in_valid = 1'b0;
        in_data = 8'sd0;
    end
    endtask

    task send_value(input logic signed [7:0] value);
    begin
        @(negedge clk);
        in_data = value;
        in_valid = 1'b1;

        @(posedge clk);

        @(negedge clk);
        in_valid = 1'b0;
        in_data = 8'sd0;
    end
    endtask

    task wait_for_done;
        integer cycle_count;
    begin
        cycle_count = 0;
        while (done !== 1'b1) begin
            @(posedge clk);
            cycle_count = cycle_count + 1;

            if (cycle_count > 40) begin
                $display("CHECK:wait_done_done:FAIL");
                disable wait_for_done;
            end
        end
    end
    endtask

    task check_result_and_done(
        input string test_name,
        input logic signed [15:0] expected_result
    );
    begin
        @(negedge clk);

        if (result === expected_result) begin
            $display("CHECK:%s_result:PASS", test_name);
        end
        else begin
            $display("CHECK:%s_result:FAIL", test_name);
            $display("  Expected result = %0d, Got result = %0d", expected_result, result);
        end

        if (done === 1'b1) begin
            $display("CHECK:%s_done:PASS", test_name);
        end
        else begin
            $display("CHECK:%s_done:FAIL", test_name);
        end

        repeat (2) drive_idle_cycle();
    end
    endtask

    initial begin
        $display("Starting tb_p2...");

        // basic_sum
        apply_reset();
        @(negedge clk);
        x_count = 8'd3;
        send_value(8'sd10);
        send_value(8'sd20);
        send_value(8'sd30);
        wait_for_done();
        check_result_and_done("basic_sum", 16'sd60);

        // mixed_sign
        apply_reset();
        @(negedge clk);
        x_count = 8'd3;
        send_value(-8'sd5);
        send_value(8'sd12);
        send_value(-8'sd3);
        wait_for_done();
        check_result_and_done("mixed_sign", 16'sd4);

        // single_value
        apply_reset();
        @(negedge clk);
        x_count = 8'd1;
        send_value(-8'sd25);
        wait_for_done();
        check_result_and_done("single_value", -16'sd25);

        // zeros
        apply_reset();
        @(negedge clk);
        x_count = 8'd3;
        send_value(8'sd0);
        send_value(8'sd0);
        send_value(8'sd0);
        wait_for_done();
        check_result_and_done("zeros", 16'sd0);

        // manual fail 
        apply_reset();
        @(negedge clk);
        x_count = 8'd2;

        send_value(8'sd3);
        send_value(8'sd4);

        wait_for_done();

        // wrong expected result on purpose (should be 7)
        check_result_and_done("manual_fail", 16'sd10);
        ////////////////////////////////////////////////////////////
        // manual_pass: test ignoring invalid cycles
        apply_reset();
        @(negedge clk);
        x_count = 8'd2;

        // valid input
        send_value(8'sd5);

        // invalid cycle (should be ignored)
        @(negedge clk);
        in_valid = 1'b0;
        in_data = 8'sd100;

        // valid input
        send_value(8'sd7);

        wait_for_done();
        check_result_and_done("manual_pass", 16'sd12);


        $display("CHECK:reached_end_of_testbench:PASS");
        $finish;
    end

    initial begin
        #5000;
        $display("CHECK:reached_end_of_testbench:FAIL");
        $display("CHECK:watchdog_done:FAIL");
        $finish;
    end

endmodule