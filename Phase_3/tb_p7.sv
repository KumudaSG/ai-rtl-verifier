`timescale 1ns / 1ps

module tb_p7;

    logic clk;
    logic reset;
    logic write_en;
    logic read_en;
    logic [7:0] data_in;
    logic [7:0] data_out;
    logic full;
    logic empty;
    logic done;

    top_p7 dut (
        .clk(clk),
        .reset(reset),
        .write_en(write_en),
        .read_en(read_en),
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
            write_en = 1'b0;
            read_en = 1'b0;
            data_in = 8'd0;

            @(negedge clk);
            reset = 1'b0;
        end
    endtask

    task do_write;
        input [7:0] value;
        input string done_check_name;
        begin
            @(negedge clk);
            data_in = value;
            write_en = 1'b1;
            read_en = 1'b0;

            #1;
            print_check(done_check_name, done == 1'b1);

            @(posedge clk);

            @(negedge clk);
            write_en = 1'b0;
            data_in = 8'd0;
        end
    endtask

    task do_read;
        input string done_check_name;
        begin
            @(negedge clk);
            write_en = 1'b0;
            read_en = 1'b1;

            #1;
            print_check(done_check_name, done == 1'b1);

            @(posedge clk);

            @(negedge clk);
            read_en = 1'b0;
        end
    endtask

    initial begin
        reset = 1'b0;
        write_en = 1'b0;
        read_en = 1'b0;
        data_in = 8'd0;

        apply_reset();

        @(posedge clk);
        print_check("reset_empty", empty == 1'b1);
        print_check("reset_full", full == 1'b0);

        // ------------------------------------------------------------
        // Single write/read
        // ------------------------------------------------------------
        do_write(8'd10, "single_write_done");

        @(posedge clk);
        print_check("single_write_empty", empty == 1'b0);
        print_check("single_write_full", full == 1'b0);

        do_read("single_read_done");

        @(posedge clk);
        print_check("single_read_data", data_out == 8'd10);
        print_check("single_read_empty", empty == 1'b1);

        // ------------------------------------------------------------
        // FIFO ordering test
        // Write 1, 2, 3. Read should return 1, 2, 3.
        // ------------------------------------------------------------
        apply_reset();

        do_write(8'd1, "write_1_done");
        do_write(8'd2, "write_2_done");
        do_write(8'd3, "write_3_done");

        do_read("read_1_done");
        @(posedge clk);
        print_check("fifo_order_1_data", data_out == 8'd1);

        do_read("read_2_done");
        @(posedge clk);
        print_check("fifo_order_2_data", data_out == 8'd2);

        do_read("read_3_done");
        @(posedge clk);
        print_check("fifo_order_3_data", data_out == 8'd3);
        print_check("fifo_empty", empty == 1'b1);

        // ------------------------------------------------------------
        // Full behavior
        // ------------------------------------------------------------
        apply_reset();

        do_write(8'd11, "fill_write_1_done");
        do_write(8'd12, "fill_write_2_done");
        do_write(8'd13, "fill_write_3_done");
        do_write(8'd14, "fill_write_4_done");
        do_write(8'd15, "fill_write_5_done");
        do_write(8'd16, "fill_write_6_done");
        do_write(8'd17, "fill_write_7_done");
        do_write(8'd18, "fill_write_8_done");

        @(posedge clk);
        print_check("full_after_8_writes_full", full == 1'b1);
        print_check("full_after_8_writes_empty", empty == 1'b0);

        // Invalid write when full should be blocked.
        @(negedge clk);
        data_in = 8'd99;
        write_en = 1'b1;
        read_en = 1'b0;

        #1;
        print_check("overflow_blocked_done", done == 1'b0);

        @(posedge clk);

        @(negedge clk);
        write_en = 1'b0;
        data_in = 8'd0;

        // Read should still return the original first value.
        do_read("overflow_safe_read_done");
        @(posedge clk);
        print_check("overflow_safe_data", data_out == 8'd11);

        // ------------------------------------------------------------
        // Underflow behavior
        // ------------------------------------------------------------
        apply_reset();

        @(negedge clk);
        write_en = 1'b0;
        read_en = 1'b1;

        #1;
        print_check("underflow_blocked_done", done == 1'b0);

        @(posedge clk);

        @(negedge clk);
        read_en = 1'b0;

        @(posedge clk);
        print_check("underflow_safe_empty", empty == 1'b1);
        print_check("underflow_safe_full", full == 1'b0);

        // ------------------------------------------------------------
        // Wraparound behavior
        // Fill, read 4, write 4 more, then read remaining in order.
        // Expected order after wraparound:
        // 5, 6, 7, 8, 21, 22, 23, 24
        // ------------------------------------------------------------
        apply_reset();

        do_write(8'd1, "wrap_write_1_done");
        do_write(8'd2, "wrap_write_2_done");
        do_write(8'd3, "wrap_write_3_done");
        do_write(8'd4, "wrap_write_4_done");
        do_write(8'd5, "wrap_write_5_done");
        do_write(8'd6, "wrap_write_6_done");
        do_write(8'd7, "wrap_write_7_done");
        do_write(8'd8, "wrap_write_8_done");

        do_read("wrap_read_old_1_done");
        @(posedge clk);
        print_check("wrap_old_1_data", data_out == 8'd1);

        do_read("wrap_read_old_2_done");
        @(posedge clk);
        print_check("wrap_old_2_data", data_out == 8'd2);

        do_read("wrap_read_old_3_done");
        @(posedge clk);
        print_check("wrap_old_3_data", data_out == 8'd3);

        do_read("wrap_read_old_4_done");
        @(posedge clk);
        print_check("wrap_old_4_data", data_out == 8'd4);

        do_write(8'd21, "wrap_new_write_1_done");
        do_write(8'd22, "wrap_new_write_2_done");
        do_write(8'd23, "wrap_new_write_3_done");
        do_write(8'd24, "wrap_new_write_4_done");

        do_read("wrap_read_1_done");
        @(posedge clk);
        print_check("wraparound_1_data", data_out == 8'd5);

        do_read("wrap_read_2_done");
        @(posedge clk);
        print_check("wraparound_2_data", data_out == 8'd6);

        do_read("wrap_read_3_done");
        @(posedge clk);
        print_check("wraparound_3_data", data_out == 8'd7);

        do_read("wrap_read_4_done");
        @(posedge clk);
        print_check("wraparound_4_data", data_out == 8'd8);

        do_read("wrap_read_5_done");
        @(posedge clk);
        print_check("wraparound_5_data", data_out == 8'd21);

        do_read("wrap_read_6_done");
        @(posedge clk);
        print_check("wraparound_6_data", data_out == 8'd22);

        do_read("wrap_read_7_done");
        @(posedge clk);
        print_check("wraparound_7_data", data_out == 8'd23);

        do_read("wrap_read_8_done");
        @(posedge clk);
        print_check("wraparound_8_data", data_out == 8'd24);

        print_check("wraparound_empty", empty == 1'b1);


        print_check("reached_end_of_testbench", 1'b1);

        #20;
        $finish;
    end

endmodule