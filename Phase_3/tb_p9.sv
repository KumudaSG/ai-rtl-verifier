`timescale 1ns / 1ps

module tb_p9;

    logic clk;
    logic reset;
    logic write_en;
    logic [1:0] write_addr;
    logic [7:0] write_data;
    logic [1:0] read_addr;
    logic [7:0] read_data;
    logic done;

    top_p9 dut (
        .clk(clk),
        .reset(reset),
        .write_en(write_en),
        .write_addr(write_addr),
        .write_data(write_data),
        .read_addr(read_addr),
        .read_data(read_data),
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
            write_addr = 2'd0;
            write_data = 8'd0;
            read_addr = 2'd0;

            @(negedge clk);
            reset = 1'b0;
        end
    endtask

    task do_write;
        input [1:0] addr;
        input [7:0] value;
        input string done_check_name;
        begin
            @(negedge clk);
            write_en = 1'b1;
            write_addr = addr;
            write_data = value;

            #1;
            print_check(done_check_name, done == 1'b1);

            @(posedge clk);

            @(negedge clk);
            write_en = 1'b0;
            write_addr = 2'd0;
            write_data = 8'd0;
        end
    endtask

    task do_read_check;
        input [1:0] addr;
        input [7:0] expected_value;
        input string check_name;
        begin
            @(negedge clk);
            read_addr = addr;
            write_en = 1'b0;

            #1;
            print_check(check_name, read_data == expected_value);
        end
    endtask

    initial begin
        reset = 1'b0;
        write_en = 1'b0;
        write_addr = 2'd0;
        write_data = 8'd0;
        read_addr = 2'd0;

        apply_reset();

        // ------------------------------------------------------------
        // Reset behavior: all registers should read as 0.
        // ------------------------------------------------------------
        do_read_check(2'd0, 8'd0, "reset_read_addr0");
        do_read_check(2'd1, 8'd0, "reset_read_addr1");
        do_read_check(2'd2, 8'd0, "reset_read_addr2");
        do_read_check(2'd3, 8'd0, "reset_read_addr3");

        @(negedge clk);
        write_en = 1'b0;
        #1;
        print_check("idle_done", done == 1'b0);

        // ------------------------------------------------------------
        // Single write/read.
        // ------------------------------------------------------------
        do_write(2'd2, 8'd55, "single_write_done");
        do_read_check(2'd2, 8'd55, "single_write_read_data");

        // ------------------------------------------------------------
        // Write all registers and verify independent storage.
        // ------------------------------------------------------------
        do_write(2'd0, 8'd10, "write_addr0_done");
        do_write(2'd1, 8'd20, "write_addr1_done");
        do_write(2'd2, 8'd30, "write_addr2_done");
        do_write(2'd3, 8'd40, "write_addr3_done");

        do_read_check(2'd0, 8'd10, "read_addr0_data");
        do_read_check(2'd1, 8'd20, "read_addr1_data");
        do_read_check(2'd2, 8'd30, "read_addr2_data");
        do_read_check(2'd3, 8'd40, "read_addr3_data");

        // ------------------------------------------------------------
        // No-write behavior.
        // Try changing write_data with write_en = 0.
        // Register contents should not change.
        // ------------------------------------------------------------
        @(negedge clk);
        write_en = 1'b0;
        write_addr = 2'd1;
        write_data = 8'd99;
        read_addr = 2'd1;

        #1;
        print_check("no_write_done", done == 1'b0);

        @(posedge clk);

        do_read_check(2'd1, 8'd20, "no_write_preserve_data");

        // ------------------------------------------------------------
        // Overwrite one register only.
        // Other registers should stay unchanged.
        // ------------------------------------------------------------
        do_write(2'd1, 8'd77, "overwrite_addr1_done");

        do_read_check(2'd0, 8'd10, "overwrite_keep_addr0");
        do_read_check(2'd1, 8'd77, "overwrite_change_addr1");
        do_read_check(2'd2, 8'd30, "overwrite_keep_addr2");
        do_read_check(2'd3, 8'd40, "overwrite_keep_addr3");

        // ------------------------------------------------------------
        // Read-during-write same address.
        // Expected behavior from prompt:
        // read_data shows old value before the clock edge,
        // then new value after the clock edge.
        // ------------------------------------------------------------
        @(negedge clk);
        write_en = 1'b1;
        write_addr = 2'd3;
        write_data = 8'd88;
        read_addr = 2'd3;

        #1;
        print_check("read_during_write_old_data", read_data == 8'd40);
        print_check("read_during_write_done", done == 1'b1);

        @(posedge clk);

        @(negedge clk);
        write_en = 1'b0;
        write_addr = 2'd0;
        write_data = 8'd0;

        #1;
        print_check("read_during_write_new_data", read_data == 8'd88);
        
        apply_reset();

        do_write(2'd1, 8'd44, "manual_pass_write_done");
        do_read_check(2'd1, 8'd44, "manual_pass_register_file");

        // Intentionally wrong: register 1 contains 44, not 45.
        do_read_check(2'd1, 8'd45, "manual_fail_register_file");
        
        print_check("reached_end_of_testbench", 1'b1);

        #20;
        $finish;
    end

endmodule