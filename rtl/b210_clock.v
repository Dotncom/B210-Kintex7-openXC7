// SPDX-License-Identifier: LGPL-3.0-or-later
// The board supplies a 40 MHz differential reference. GPIF and the bus
// share the 100 MHz output. Keep feedback on a global clock buffer.
module b210_clock (
    input wire ref_p,
    input wire ref_n,
    input wire reset,
    output wire clk100,
    output wire locked
);
    wire ref_clock;
    wire feedback;
    wire feedback_global;
    wire gpif_clock;

    IBUFDS ref_buffer (.I(ref_p), .IB(ref_n), .O(ref_clock));
    BUFG feedback_buffer (.I(feedback), .O(feedback_global));
    BUFG gpif_buffer (.I(gpif_clock), .O(clk100));

    // 40 MHz × 25 = 1 GHz VCO. Output 1 divides by 10.
    // Keep the unused divider settings for the board's MMCM readback check.
    MMCME2_ADV #(
        .BANDWIDTH("OPTIMIZED"),
        .COMPENSATION("ZHOLD"),
        .CLKIN1_PERIOD(25.0),
        .DIVCLK_DIVIDE(1),
        .CLKFBOUT_MULT_F(25.0),
        .CLKOUT0_DIVIDE_F(25.0),
        .CLKOUT1_DIVIDE(10),
        .CLKOUT2_DIVIDE(10)
    ) mmcm (
        .CLKIN1(ref_clock), .CLKIN2(1'b0), .CLKINSEL(1'b1),
        .CLKFBIN(feedback_global), .CLKFBOUT(feedback),
        .CLKOUT1(gpif_clock), .LOCKED(locked), .RST(reset), .PWRDWN(1'b0),
        .DADDR(7'b0), .DI(16'b0), .DCLK(1'b0), .DEN(1'b0), .DWE(1'b0),
        .PSCLK(1'b0), .PSEN(1'b0), .PSINCDEC(1'b0)
    );
endmodule
