`timescale 1ns/1ps

module datapath (
    input  logic              clk,
    input  logic              reset,
    input  logic [10:0]       x_count,
    input  logic signed [7:0] in_data,
    input  logic              in_valid,
    input  logic              init_product,
    input  logic              accept_operand,
    output logic signed [31:0] result,
    output logic              overflow,
    output logic              last_operand_accepted
);

    logic [10:0] accepted_count;
    logic signed [31:0] product_reg;

    logic signed [31:0] operand_ext;
    logic signed [39:0] mult_full;
    logic [10:0] next_count;
    logic signed [31:0] base_product;

    // Sign-extend the 8-bit input operand to 32 bits.
    assign operand_ext = {{24{in_data[7]}}, in_data};

    // If init_product is asserted, the running product starts from 1 for a new
    // computation. This allows the first valid operand to be multiplied into 1.
    assign base_product = init_product ? 32'sd1 : product_reg;

    // Full precision intermediate multiply: 32-bit signed product by 8-bit signed
    // operand (extended to 32 bits), giving up to 40 bits.
    assign mult_full = base_product * operand_ext;

    // Only accepted operands are counted. An operand is accepted only when the
    // control FSM asserts accept_operand, which occurs only on cycles with in_valid=1.
    assign next_count = accepted_count + 11'd1;

    // last_operand_accepted is a combinational status used by the control FSM.
    // It predicts whether the currently accepted operand will complete the required
    // x_count operands. It is only meaningful when accept_operand is high.
    assign last_operand_accepted = accept_operand && (next_count == x_count);

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            product_reg     <= 32'sd1;
            result          <= 32'sd1;
            overflow        <= 1'b0;
            accepted_count  <= 11'd0;
        end else begin
            // Start of a new computation initializes product, counter, and overflow.
            // If a first operand is also accepted in this cycle, logic below updates
            // the registers again with the multiplied value and count=1.
            if (init_product) begin
                product_reg    <= 32'sd1;
                result         <= 32'sd1;
                overflow       <= 1'b0;
                accepted_count <= 11'd0;
            end

            // Sample in_data and update state only when an operand is accepted.
            // Cycles with in_valid=0 are ignored because control will not assert
            // accept_operand in those cycles.
            if (accept_operand && in_valid) begin
                product_reg    <= mult_full[31:0];
                result         <= mult_full[31:0];
                accepted_count <= next_count;

                // Overflow behavior:
                // - overflow is sticky for the duration of the computation.
                // - It asserts if the exact signed product does not fit in 32 bits.
                // - The stored result is the wrapped/truncated low 32 bits of the
                //   two's complement product.
                if (mult_full > 40'sd2147483647 || mult_full < -40'sd2147483648) begin
                    overflow <= 1'b1;
                end
            end
        end
    end

endmodule
