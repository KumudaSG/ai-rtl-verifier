`timescale 1ns / 1ps

module tb_p8;

    logic clk;
    logic reset;
    logic in_valid;
    logic [7:0] data_in;
    logic [10:0] window_sum;
    logic window_valid;
    logic done;

    top_p8 dut (
        .clk(clk),
        .reset(reset),
        .in_valid(in_valid),
        .data_in(data_in),
        .window_sum(window_sum),
        .window_valid(window_valid),
        .done(done)
    );

    initial clk = 1'b0;
    always #5 clk = ~clk;

    task print_check;
        input string check_name;
        input logic passed;
        begin
            if (passed)
                $display("CHECK:%s:PASS", check_name);
            else
                $display("CHECK:%s:FAIL", check_name);
        end
    endtask

    task apply_reset;
        begin
            @(negedge clk);
            reset = 1'b1;
            in_valid = 1'b0;
            data_in = 8'd0;

            @(negedge clk);
            reset = 1'b0;
        end
    endtask

    task send_value;
        input [7:0] value;
        input string done_check_name;
        begin
            @(negedge clk);
            data_in = value;
            in_valid = 1'b1;

            #1;
            print_check(done_check_name, done == 1'b1);

            @(posedge clk);

            @(negedge clk);
            in_valid = 1'b0;
            data_in = 8'd0;
        end
    endtask

    task gap_cycle;
        input string check_name;
        input [10:0] expected_sum;
        input logic expected_valid;
        begin
            @(negedge clk);
            in_valid = 1'b0;
            data_in = 8'd99;

            #1;
            print_check({check_name, "_done"}, done == 1'b0);

            @(posedge clk);

            @(posedge clk);
            print_check({check_name, "_sum"}, window_sum == expected_sum);
            print_check({check_name, "_valid"}, window_valid == expected_valid);
        end
    endtask

    initial begin
        reset = 1'b0;
        in_valid = 1'b0;
        data_in = 8'd0;

        apply_reset();

        @(posedge clk);
        print_check("reset_sum", window_sum == 11'd0);
        print_check("reset_window_valid", window_valid == 1'b0);
        print_check("reset_done", done == 1'b0);

        // ------------------------------------------------------------
        // First 4 samples fill the window.
        // Inputs: 1, 2, 3, 4
        // Expected sum after 4th input = 10
        // ------------------------------------------------------------
        send_value(8'd1, "input_1_done");
        @(posedge clk);
        print_check("after_1_sum", window_sum == 11'd1);
        print_check("after_1_valid", window_valid == 1'b0);

        send_value(8'd2, "input_2_done");
        @(posedge clk);
        print_check("after_2_sum", window_sum == 11'd3);
        print_check("after_2_valid", window_valid == 1'b0);

        send_value(8'd3, "input_3_done");
        @(posedge clk);
        print_check("after_3_sum", window_sum == 11'd6);
        print_check("after_3_valid", window_valid == 1'b0);

        send_value(8'd4, "input_4_done");
        @(posedge clk);
        print_check("after_4_sum", window_sum == 11'd10);
        print_check("after_4_valid", window_valid == 1'b1);

        // ------------------------------------------------------------
        // Sliding behavior.
        // Last 4 values after input 5: 2 + 3 + 4 + 5 = 14
        // Last 4 values after input 6: 3 + 4 + 5 + 6 = 18
        // ------------------------------------------------------------
        send_value(8'd5, "input_5_done");
        @(posedge clk);
        print_check("slide_5_sum", window_sum == 11'd14);
        print_check("slide_5_valid", window_valid == 1'b1);

        send_value(8'd6, "input_6_done");
        @(posedge clk);
        print_check("slide_6_sum", window_sum == 11'd18);
        print_check("slide_6_valid", window_valid == 1'b1);

        // ------------------------------------------------------------
        // Gap cycle should not change state.
        // ------------------------------------------------------------
        gap_cycle("gap_after_6", 11'd18, 1'b1);

        // ------------------------------------------------------------
        // More sliding values.
        // Last 4 after input 7: 4 + 5 + 6 + 7 = 22
        // Last 4 after input 8: 5 + 6 + 7 + 8 = 26
        // Last 4 after input 9: 6 + 7 + 8 + 9 = 30
        // ------------------------------------------------------------
        send_value(8'd7, "input_7_done");
        @(posedge clk);
        print_check("slide_7_sum", window_sum == 11'd22);

        send_value(8'd8, "input_8_done");
        @(posedge clk);
        print_check("slide_8_sum", window_sum == 11'd26);

        send_value(8'd9, "input_9_done");
        @(posedge clk);
        print_check("wraparound_sum", window_sum == 11'd30);
        print_check("wraparound_valid", window_valid == 1'b1);

        // ------------------------------------------------------------
        // Larger values, checks unsigned arithmetic and width.
        // Inputs after reset: 255, 255, 255, 255 => 1020
        // ------------------------------------------------------------
        apply_reset();

        send_value(8'd255, "max_1_done");
        send_value(8'd255, "max_2_done");
        send_value(8'd255, "max_3_done");
        send_value(8'd255, "max_4_done");

        @(posedge clk);
        print_check("max_sum", window_sum == 11'd1020);
        print_check("max_valid", window_valid == 1'b1);

        
        apply_reset();

        send_value(8'd4, "manual_pass_input_1_done");
        send_value(8'd5, "manual_pass_input_2_done");
        send_value(8'd6, "manual_pass_input_3_done");
        send_value(8'd7, "manual_pass_input_4_done");

        @(posedge clk);
        print_check("manual_pass_window_sum", window_sum == 11'd22);

        // Intentionally wrong: 4 + 5 + 6 + 7 = 22, not 23.
        print_check("manual_fail_window_sum", window_sum == 11'd23);

        print_check("reached_end_of_testbench", 1'b1);

        #20;
        $finish;
    end

endmodule