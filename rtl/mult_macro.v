// SPDX-License-Identifier: LGPL-3.0-or-later
// The B210 legacy DDC and DUC use the signed, one-cycle MULT_MACRO mode.
module MULT_MACRO #(
    parameter DEVICE = "7SERIES",
    parameter LATENCY = 1,
    parameter WIDTH_A = 18,
    parameter WIDTH_B = 18
) (
    input wire CLK,
    input wire CE,
    input wire RST,
    input wire signed [WIDTH_A-1:0] A,
    input wire signed [WIDTH_B-1:0] B,
    output reg signed [WIDTH_A+WIDTH_B-1:0] P
);
    if (LATENCY != 1) begin : unsupported_mode
        B210_MULT_MACRO_REQUIRES_LATENCY_1 invalid();
    end

    always @(posedge CLK) begin
        if (RST)
            P <= 0;
        else if (CE)
            P <= A * B;
    end
endmodule
