`timescale 1ns / 1ps

module tb_p4;

    logic clk;
    logic reset;
    logic [7:0] target_count;
    logic pulse_in;
    logic in_valid;
    logic [7:0] count;
    logic done;

    integer wait_cycles;
    integer observed_count;

    top_p4 dut (
        .clk(clk),
        .reset(reset),
        .target_count(target_count),
        .pulse_in(pulse_in),
        .in_valid(in_valid),
        .count(count),
        .done(done)
    );

    initial clk = 1'b0;
    always #5 clk = ~clk;

    task do_reset;
    begin
        reset = 1'b1;
        target_count = 8'd0;
        pulse_in = 1'b0;
        in_valid = 1'b0;

        @(negedge clk);
        @(negedge clk);
        reset = 1'b0;

        // give one full cycle after reset release
        @(posedge clk);
        @(negedge clk);
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

    task send_cycle(
        input bit pulse_value,
        input bit valid_value,
        output bit sampled_done,
        output logic [7:0] sampled_count
    );
    begin
        // drive before active edge
        @(negedge clk);
        pulse_in = pulse_value;
        in_valid = valid_value;

        // DUT samples here
        @(posedge clk);
        #1;
        sampled_done = done;
        sampled_count = count;

        // clear after sampling edge
        @(negedge clk);
        pulse_in = 1'b0;
        in_valid = 1'b0;
    end
    endtask

    task wait_for_done_and_capture(
        output bit got_done,
        output logic [7:0] count_when_done
    );
        logic [7:0] sampled_count;
    begin
        got_done = 0;
        count_when_done = count;
        wait_cycles = 0;

        while (done !== 1'b1 && wait_cycles < 100) begin
            @(posedge clk);
            #1;
            sampled_count = count;
            wait_cycles = wait_cycles + 1;

            if (done === 1'b1) begin
                got_done = 1;
                count_when_done = sampled_count;
            end
        end
    end
    endtask

    task check_final(
        input string test_name,
        input integer expected_count,
        input bit expected_done,
        input bit got_done,
        input logic [7:0] sampled_count
    );
        bit pass_count;
        bit pass_done;
    begin
        pass_count = (sampled_count === expected_count);

        if (expected_done)
            pass_done = (got_done === 1'b1);
        else
            pass_done = (done === 1'b0);

        print_result({test_name, "_result"}, pass_count);
        print_result({test_name, "_done"}, pass_done);

        if (!pass_count) begin
            $display("DEBUG:%s:expected_count=%0d:sampled_count=%0d:live_count=%0d",
                     test_name, expected_count, sampled_count, count);
        end

        if (!pass_done) begin
            if (expected_done)
                $display("DEBUG:%s:expected_done_seen=1:actual_done_seen=%0d",
                         test_name, got_done);
            else
                $display("DEBUG:%s:expected_done=0:actual_done=%0d",
                         test_name, done);
        end
    end
    endtask

    initial begin
        bit sampled_done;
        bit got_done;
        logic [7:0] sampled_count;

        reset = 1'b0;
        target_count = 8'd0;
        pulse_in = 1'b0;
        in_valid = 1'b0;

        $display("Starting tb_p4...");

        // Test 1: three valid pulses reach target
        do_reset();
        target_count = 8'd3;
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);
        wait_for_done_and_capture(got_done, sampled_count);
        check_final("basic_count", 3, 1'b1, got_done, sampled_count);

        // Test 2: invalid cycle with pulse high should be ignored
        do_reset();
        target_count = 8'd2;
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);
        send_cycle(1'b1, 1'b0, sampled_done, sampled_count);
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);
        wait_for_done_and_capture(got_done, sampled_count);
        check_final("ignore_invalid", 2, 1'b1, got_done, sampled_count);

        // Test 3: valid cycles with pulse low should not count
        do_reset();
        target_count = 8'd2;
        send_cycle(1'b0, 1'b1, sampled_done, sampled_count);
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);
        send_cycle(1'b0, 1'b1, sampled_done, sampled_count);
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);
        wait_for_done_and_capture(got_done, sampled_count);
        check_final("ignore_zero_pulse", 2, 1'b1, got_done, sampled_count);

        // Test 4: not enough pulses yet
        do_reset();
        target_count = 8'd3;
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);
        send_cycle(1'b0, 1'b1, sampled_done, sampled_count);
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);

        // sample immediately after the last meaningful cycle
        @(posedge clk);
        #1;
        sampled_count = count;
        got_done = (done === 1'b1);

        check_final("not_done_yet", 2, 1'b0, got_done, sampled_count);

        // Test 5: target_count = 1
        do_reset();
        target_count = 8'd1;
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);
        wait_for_done_and_capture(got_done, sampled_count);
        check_final("target_one", 1, 1'b1, got_done, sampled_count);

        // manual_pass: invalid pulse should be ignored, valid pulses should count
        do_reset();
        target_count = 8'd2;
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);  // count = 1
        send_cycle(1'b1, 1'b0, sampled_done, sampled_count);  // ignored
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);  // count = 2
        wait_for_done_and_capture(got_done, sampled_count);
        check_final("manual_pass", 2, 1'b1, got_done, sampled_count);

        // manual_fail: intentionally wrong expected count
        do_reset();
        target_count = 8'd2;
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);  // count = 1
        send_cycle(1'b1, 1'b1, sampled_done, sampled_count);  // count = 2
        wait_for_done_and_capture(got_done, sampled_count);
        check_final("manual_fail", 3, 1'b1, got_done, sampled_count);

        $display("CHECK:reached_end_of_testbench:PASS");
        $display("CHECK:watchdog_done:PASS");
        $finish;
    end

    initial begin
        #5000;
        $display("CHECK:reached_end_of_testbench:FAIL");
        $display("CHECK:watchdog_done:FAIL");
        $finish;
    end

endmodule