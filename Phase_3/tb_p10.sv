`timescale 1ns / 1ps

module tb_p10;

    logic clk;
    logic reset;
    logic insert_en;
    logic remove_en;
    logic [7:0] data_in;
    logic [7:0] data_out;
    logic full;
    logic empty;
    logic done;

    top_p10 dut (
        .clk(clk),
        .reset(reset),
        .insert_en(insert_en),
        .remove_en(remove_en),
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
            insert_en = 1'b0;
            remove_en = 1'b0;
            data_in = 8'd0;

            @(negedge clk);
            reset = 1'b0;
        end
    endtask

    task do_insert;
        input [7:0] value;
        input string done_check_name;
        begin
            @(negedge clk);
            data_in = value;
            insert_en = 1'b1;
            remove_en = 1'b0;

            #1;
            print_check(done_check_name, done == 1'b1);

            @(posedge clk);

            @(negedge clk);
            insert_en = 1'b0;
            data_in = 8'd0;
        end
    endtask

    task do_remove;
        input string done_check_name;
        begin
            @(negedge clk);
            insert_en = 1'b0;
            remove_en = 1'b1;

            #1;
            print_check(done_check_name, done == 1'b1);

            @(posedge clk);

            @(negedge clk);
            remove_en = 1'b0;
        end
    endtask

    initial begin
        reset = 1'b0;
        insert_en = 1'b0;
        remove_en = 1'b0;
        data_in = 8'd0;

        apply_reset();

        // ------------------------------------------------------------
        // Reset behavior
        // ------------------------------------------------------------
        @(posedge clk);
        print_check("reset_empty", empty == 1'b1);
        print_check("reset_full", full == 1'b0);
        print_check("reset_data", data_out == 8'd0);

        // ------------------------------------------------------------
        // Single insert and remove
        // ------------------------------------------------------------
        do_insert(8'd10, "single_insert_done");

        @(posedge clk);
        print_check("single_insert_empty", empty == 1'b0);
        print_check("single_insert_full", full == 1'b0);
        print_check("single_insert_data", data_out == 8'd10);

        do_remove("single_remove_done");

        @(posedge clk);
        print_check("single_remove_empty", empty == 1'b1);
        print_check("single_remove_full", full == 1'b0);
        print_check("single_remove_data", data_out == 8'd0);

        // ------------------------------------------------------------
        // Priority behavior
        // Insert 10, 50, 30. Highest should be 50.
        // ------------------------------------------------------------
        apply_reset();

        do_insert(8'd10, "insert_10_done");
        @(posedge clk);
        print_check("priority_after_10_data", data_out == 8'd10);

        do_insert(8'd50, "insert_50_done");
        @(posedge clk);
        print_check("priority_after_50_data", data_out == 8'd50);

        do_insert(8'd30, "insert_30_done");
        @(posedge clk);
        print_check("priority_after_30_data", data_out == 8'd50);

        // Remove highest 50. Next highest should be 30.
        do_remove("remove_highest_50_done");
        @(posedge clk);
        print_check("priority_after_remove_50_data", data_out == 8'd30);

        // Remove highest 30. Next highest should be 10.
        do_remove("remove_highest_30_done");
        @(posedge clk);
        print_check("priority_after_remove_30_data", data_out == 8'd10);

        // Remove final value. Buffer should be empty.
        do_remove("remove_highest_10_done");
        @(posedge clk);
        print_check("priority_after_remove_10_empty", empty == 1'b1);
        print_check("priority_after_remove_10_data", data_out == 8'd0);

        // ------------------------------------------------------------
        // Full behavior and invalid insert
        // ------------------------------------------------------------
        apply_reset();

        do_insert(8'd5, "fill_insert_1_done");
        do_insert(8'd15, "fill_insert_2_done");
        do_insert(8'd25, "fill_insert_3_done");
        do_insert(8'd35, "fill_insert_4_done");

        @(posedge clk);
        print_check("full_after_4_inserts_full", full == 1'b1);
        print_check("full_after_4_inserts_empty", empty == 1'b0);
        print_check("full_after_4_inserts_data", data_out == 8'd35);

        // Invalid insert while full should not assert done or change highest.
        @(negedge clk);
        data_in = 8'd99;
        insert_en = 1'b1;
        remove_en = 1'b0;

        #1;
        print_check("overflow_blocked_done", done == 1'b0);
        print_check("overflow_blocked_data", data_out == 8'd35);

        @(posedge clk);

        @(negedge clk);
        insert_en = 1'b0;
        data_in = 8'd0;

        @(posedge clk);
        print_check("overflow_safe_data", data_out == 8'd35);
        print_check("overflow_safe_full", full == 1'b1);

        // ------------------------------------------------------------
        // Remove from full buffer in priority order.
        // Expected: 35, 25, 15, 5
        // ------------------------------------------------------------
        do_remove("remove_35_done");
        @(posedge clk);
        print_check("remove_35_next_data", data_out == 8'd25);

        do_remove("remove_25_done");
        @(posedge clk);
        print_check("remove_25_next_data", data_out == 8'd15);

        do_remove("remove_15_done");
        @(posedge clk);
        print_check("remove_15_next_data", data_out == 8'd5);

        do_remove("remove_5_done");
        @(posedge clk);
        print_check("remove_5_empty", empty == 1'b1);
        print_check("remove_5_data", data_out == 8'd0);

        // ------------------------------------------------------------
        // Underflow behavior
        // ------------------------------------------------------------
        apply_reset();

        @(negedge clk);
        insert_en = 1'b0;
        remove_en = 1'b1;

        #1;
        print_check("underflow_blocked_done", done == 1'b0);

        @(posedge clk);

        @(negedge clk);
        remove_en = 1'b0;

        @(posedge clk);
        print_check("underflow_safe_empty", empty == 1'b1);
        print_check("underflow_safe_full", full == 1'b0);
        print_check("underflow_safe_data", data_out == 8'd0);

        // ------------------------------------------------------------
        // Tie behavior
        // With equal highest values, removing one should leave the other.
        // We cannot observe internal index directly, but we can check that
        // duplicate highest values are handled correctly.
        // ------------------------------------------------------------
        apply_reset();

        do_insert(8'd40, "tie_insert_1_done");
        do_insert(8'd40, "tie_insert_2_done");
        do_insert(8'd20, "tie_insert_3_done");

        @(posedge clk);
        print_check("tie_initial_highest", data_out == 8'd40);

        do_remove("tie_remove_first_40_done");
        @(posedge clk);
        print_check("tie_second_40_still_highest", data_out == 8'd40);

        do_remove("tie_remove_second_40_done");
        @(posedge clk);
        print_check("tie_after_two_40s_removed", data_out == 8'd20);

        apply_reset();

        do_insert(8'd12, "manual_pass_insert_1_done");
        do_insert(8'd55, "manual_pass_insert_2_done");
        do_insert(8'd33, "manual_pass_insert_3_done");

        @(posedge clk);
        print_check("manual_pass_priority_buffer", data_out == 8'd55);

        // Intentionally wrong: highest is 55, not 33
        print_check("manual_fail_priority_buffer", data_out == 8'd33);

        print_check("reached_end_of_testbench", 1'b1);

        #20;
        $finish;
    end

endmodule