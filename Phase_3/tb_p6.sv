`timescale 1ns / 1ps

module tb_p6;

    logic clk;
    logic reset;
    logic push_en;
    logic pop_en;
    logic [7:0] data_in;
    logic [7:0] data_out;
    logic full;
    logic empty;
    logic done;

    top_p6 dut (
        .clk(clk),
        .reset(reset),
        .push_en(push_en),
        .pop_en(pop_en),
        .data_in(data_in),
        .data_out(data_out),
        .full(full),
        .empty(empty),
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
            push_en = 1'b0;
            pop_en = 1'b0;
            data_in = 8'd0;

            @(negedge clk);
            reset = 1'b0;
        end
    endtask

    task do_push;
        input [7:0] value;
        input string done_check_name;
        begin
            @(negedge clk);
            data_in = value;
            push_en = 1'b1;
            pop_en = 1'b0;

            #1;
            print_check(done_check_name, done == 1'b1);

            @(posedge clk);

            @(negedge clk);
            push_en = 1'b0;
            data_in = 8'd0;
        end
    endtask

    task do_pop;
        input string done_check_name;
        begin
            @(negedge clk);
            push_en = 1'b0;
            pop_en = 1'b1;

            #1;
            print_check(done_check_name, done == 1'b1);

            @(posedge clk);

            @(negedge clk);
            pop_en = 1'b0;
        end
    endtask

    initial begin
        reset = 1'b0;
        push_en = 1'b0;
        pop_en = 1'b0;
        data_in = 8'd0;

        apply_reset();

        @(posedge clk);
        print_check("reset_empty", empty == 1'b1);
        print_check("reset_full", full == 1'b0);

        do_push(8'd10, "single_push_done");
        @(posedge clk);
        print_check("single_push_empty", empty == 1'b0);
        print_check("single_push_full", full == 1'b0);

        do_pop("single_pop_done");
        @(posedge clk);
        print_check("single_pop_data", data_out == 8'd10);
        print_check("single_pop_empty", empty == 1'b1);

        apply_reset();

        do_push(8'd1, "push_1_done");
        do_push(8'd2, "push_2_done");
        do_push(8'd3, "push_3_done");

        do_pop("pop_1_done");
        @(posedge clk);
        print_check("lifo_order_1_data", data_out == 8'd3);

        do_pop("pop_2_done");
        @(posedge clk);
        print_check("lifo_order_2_data", data_out == 8'd2);

        do_pop("pop_3_done");
        @(posedge clk);
        print_check("lifo_order_3_data", data_out == 8'd1);
        print_check("lifo_empty", empty == 1'b1);

        apply_reset();

        do_push(8'd11, "fill_push_1_done");
        do_push(8'd12, "fill_push_2_done");
        do_push(8'd13, "fill_push_3_done");
        do_push(8'd14, "fill_push_4_done");
        do_push(8'd15, "fill_push_5_done");
        do_push(8'd16, "fill_push_6_done");
        do_push(8'd17, "fill_push_7_done");
        do_push(8'd18, "fill_push_8_done");

        @(posedge clk);
        print_check("full_after_8_pushes_full", full == 1'b1);
        print_check("full_after_8_pushes_empty", empty == 1'b0);

        @(negedge clk);
        data_in = 8'd99;
        push_en = 1'b1;
        pop_en = 1'b0;

        #1;
        print_check("overflow_blocked_done", done == 1'b0);

        @(posedge clk);

        @(negedge clk);
        push_en = 1'b0;
        data_in = 8'd0;

        do_pop("overflow_safe_pop_done");
        @(posedge clk);
        print_check("overflow_safe_data", data_out == 8'd18);

        apply_reset();

        @(negedge clk);
        push_en = 1'b0;
        pop_en = 1'b1;

        #1;
        print_check("underflow_blocked_done", done == 1'b0);

        @(posedge clk);

        @(negedge clk);
        pop_en = 1'b0;

        @(posedge clk);
        print_check("underflow_safe_empty", empty == 1'b1);
        print_check("underflow_safe_full", full == 1'b0);

        apply_reset();

        do_push(8'd42, "manual_pass_push_done");
        do_pop("manual_pass_pop_done");
        @(posedge clk);
        print_check("manual_pass_stack_lifo", data_out == 8'd42);

        // The correct popped value was 42, so this should fail.
        print_check("manual_fail_stack_lifo", data_out == 8'd99);

        print_check("reached_end_of_testbench", 1'b1);

        #20;
        $finish;
    end

endmodule