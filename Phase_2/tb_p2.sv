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
        // Drive inputs BEFORE the next rising edge so the DUT samples them correctly
        @(negedge clk);
        in_data = value;
        in_valid = 1'b1;

        // Hold through the sampling edge
        @(posedge clk);

        // Deassert after the edge
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

    task run_test(
        input string test_name,
        input logic [7:0] count_value,
        input logic signed [7:0] values [0:7],
        input integer num_values,
        input logic signed [15:0] expected_result
    );
        integer value_index;
    begin
        apply_reset();

        @(negedge clk);
        x_count = count_value;

        for (value_index = 0; value_index < num_values; value_index = value_index + 1) begin
            send_value(values[value_index]);
        end

        wait_for_done();

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

    logic signed [7:0] vals1 [0:7];
    logic signed [7:0] vals2 [0:7];
    logic signed [7:0] vals3 [0:7];
    logic signed [7:0] vals4 [0:7];

    initial begin
        $display("Starting tb_p2...");

        vals1[0] = 8'sd10;
        vals1[1] = 8'sd20;
        vals1[2] = 8'sd30;
        run_test("basic_sum", 8'd3, vals1, 3, 16'sd60);

        vals2[0] = -8'sd5;
        vals2[1] = 8'sd12;
        vals2[2] = -8'sd3;
        run_test("mixed_sign", 8'd3, vals2, 3, 16'sd4);

        vals3[0] = -8'sd25;
        run_test("single_value", 8'd1, vals3, 1, -16'sd25);

        vals4[0] = 8'sd0;
        vals4[1] = 8'sd0;
        vals4[2] = 8'sd0;
        run_test("zeros", 8'd3, vals4, 3, 16'sd0);

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
