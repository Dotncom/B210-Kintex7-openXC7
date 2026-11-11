// SPDX-License-Identifier: LGPL-3.0-or-later
module b210_pps (
    input wire clk,
    input wire reset,
    input wire gps_pps,
    input wire external_pps,
    input wire internal_pps,
    input wire [1:0] source,
    output reg pps
);
    // Keep each source independent until it reaches the radio clock domain.
    (* ASYNC_REG = "TRUE" *) reg [2:0] pps_meta;
    (* ASYNC_REG = "TRUE" *) reg [2:0] pps_sync;

    always @(posedge clk) begin
        if (reset) begin
            pps_meta <= 3'b000;
            pps_sync <= 3'b000;
        end else begin
            pps_meta <= {internal_pps, external_pps, gps_pps};
            pps_sync <= pps_meta;
        end
    end

    // Match the UHD B200 time-source selector in the core's control register.
    always @* begin
        case (source)
            2'b00: pps = pps_sync[0];
            2'b01: pps = pps_sync[1];
            2'b10: pps = pps_sync[2];
            default: pps = 1'b0;
        endcase
    end
endmodule
