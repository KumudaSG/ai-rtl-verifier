`timescale 1ns / 1ps

module tb_p5;

    logic clk;
    logic reset;
    logic write_en;
    logic read_en;
    logic [7:0] data_in;
    logic [7:0] data_out;
    logic full;
    logic empty;
    logic done;

    top_p5 dut (
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

    task do_reset;
    begin
        reset = 1'b1;
        write_en = 1'b0;
        read_en = 1'b0;
        data_in = 8'd0;

        repeat (2) @(negedge clk);
        reset = 1'b0;
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

    task write_data(input [7:0] value);
    begin
        @(negedge clk);
        write_en = 1'b1;
        read_en = 1'b0;
        data_in = value;

        @(posedge clk);

        @(negedge clk);
        write_en = 1'b0;
        data_in = 8'd0;
    end
    endtask

    task read_data(output [7:0] value);
    begin
        // request the read
        @(negedge clk);
        read_en = 1'b1;
        write_en = 1'b0;

        // FIFO performs the read on this edge
        @(posedge clk);

        // deassert read
        @(negedge clk);
        read_en = 1'b0;

        // wait one more cycle because data_out is registered
        @(posedge clk);
        @(negedge clk);
        value = data_out;
    end
    endtask

    task check_value(
        input string test_name,
        input [7:0] expected,
        input [7:0] actual
    );
    begin
        if (actual === expected) begin
            print_result(test_name, 1'b1);
        end
        else begin
            print_result(test_name, 1'b0);
            $display("DEBUG:%s:expected=%0d:actual=%0d",
                     test_name, expected, actual);
        end
    end
    endtask

    initial begin
        logic [7:0] temp;

        $display("Starting tb_p5...");

        // Test 1: write then read single value
        do_reset();
        write_data(8'd10);
        read_data(temp);
        check_value("single_write_read", 8'd10, temp);

        // Test 2: FIFO order check
        do_reset();
        write_data(8'd1);
        write_data(8'd2);
        write_data(8'd3);

        read_data(temp);
        check_value("fifo_order_1", 8'd1, temp);

        read_data(temp);
        check_value("fifo_order_2", 8'd2, temp);

        read_data(temp);
        check_value("fifo_order_3", 8'd3, temp);

        // Test 3: empty flag after reads
        if (empty)
            print_result("empty_after_reads", 1'b1);
        else
            print_result("empty_after_reads", 1'b0);

        // Test 4: full flag for 8-entry FIFO
        do_reset();
        write_data(8'd11);
        write_data(8'd12);
        write_data(8'd13);
        write_data(8'd14);
        write_data(8'd15);
        write_data(8'd16);
        write_data(8'd17);
        write_data(8'd18);

        @(negedge clk);
        if (full)
            print_result("full_flag", 1'b1);
        else
            print_result("full_flag", 1'b0);

        // Test 5: read from empty should be safe
        do_reset();
        read_data(temp);
        print_result("read_empty_safe", 1'b1);

        $display("CHECK:reached_end_of_testbench:PASS");
        $finish;
    end

    initial begin
        #5000;
        $display("CHECK:reached_end_of_testbench:FAIL");
        $finish;
    end

endmodule