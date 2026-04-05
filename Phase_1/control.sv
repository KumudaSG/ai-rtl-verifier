`timescale 1ns/1ps

module control (
    input  logic        clk,
    input  logic        reset,
    input  logic [10:0] x_count,
    input  logic        in_valid,
    input  logic        last_operand_accepted,
    output logic        init_product,
    output logic        accept_operand,
    output logic        set_done,
    output logic        done
);

    // Simple FSM:
    // IDLE : waiting for the first valid operand of a computation.
    // RUN  : accepting valid operands and tracking completion.
    // DONE : computation complete; hold done high until reset.
    typedef enum logic [1:0] {
        S_IDLE = 2'b00,
        S_RUN  = 2'b01,
        S_DONE = 2'b10
    } state_t;

    state_t state, next_state;

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            state <= S_IDLE;
        end else begin
            state <= next_state;
        end
    end

    always_comb begin
        // Default outputs
        init_product   = 1'b0;
        accept_operand = 1'b0;
        set_done       = 1'b0;
        done           = 1'b0;
        next_state     = state;

        case (state)
            S_IDLE: begin
                // Wait for the first valid operand. The datapath initializes the
                // running product to 1 and multiplies the first accepted operand
                // in the same cycle when in_valid is high.
                if (x_count == 11'd0) begin
                    // Edge case: if zero operands are requested, complete immediately
                    // after leaving reset. Result remains initialized to 1.
                    init_product = 1'b1;
                    set_done     = 1'b1;
                    done         = 1'b1;
                    next_state   = S_DONE;
                end else if (in_valid) begin
                    init_product   = 1'b1;
                    accept_operand = 1'b1;
                    if (last_operand_accepted) begin
                        set_done   = 1'b1;
                        done       = 1'b1;
                        next_state = S_DONE;
                    end else begin
                        next_state = S_RUN;
                    end
                end
            end

            S_RUN: begin
                // Count and process operands only on cycles where in_valid=1.
                // Gap cycles are ignored completely.
                if (in_valid) begin
                    accept_operand = 1'b1;
                    if (last_operand_accepted) begin
                        set_done   = 1'b1;
                        done       = 1'b1;
                        next_state = S_DONE;
                    end
                end
            end

            S_DONE: begin
                // Hold completion high. No more operands are consumed until reset.
                done       = 1'b1;
                next_state = S_DONE;
            end

            default: begin
                next_state = S_IDLE;
            end
        endcase
    end

endmodule
