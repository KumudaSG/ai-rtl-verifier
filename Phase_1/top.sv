`timescale 1ns/1ps

module top (
    input  logic              clk,
    input  logic              reset,
    input  logic [10:0]       x_count,
    input  logic signed [7:0] in_data,
    input  logic              in_valid,
    output logic signed [31:0] result,
    output logic              overflow,
    output logic              done
);

    // Control-to-datapath signals
    logic init_product;
    logic accept_operand;
    logic set_done;

    // Datapath-to-control status
    logic last_operand_accepted;

    // Top level only integrates the control and datapath modules.
    // All FSM behavior is in control, and all arithmetic/storage is in datapath.

    control u_control (
        .clk(clk),
        .reset(reset),
        .x_count(x_count),
        .in_valid(in_valid),
        .last_operand_accepted(last_operand_accepted),
        .init_product(init_product),
        .accept_operand(accept_operand),
        .set_done(set_done),
        .done(done)
    );

    datapath u_datapath (
        .clk(clk),
        .reset(reset),
        .x_count(x_count),
        .in_data(in_data),
        .in_valid(in_valid),
        .init_product(init_product),
        .accept_operand(accept_operand),
        .result(result),
        .overflow(overflow),
        .last_operand_accepted(last_operand_accepted)
    );

endmodule
