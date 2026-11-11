// SPDX-License-Identifier: LGPL-3.0-or-later
`timescale 1ns/1ps
module uart_smoke;
    localparam integer DIV = 2604; // 100 MHz bus, 38400 baud
    localparam [79:0] MESSAGE = "$GNGGA,0\r\n";
    reg clk = 0, reset = 1, gps_txd = 1;
    reg in_valid = 0, in_last = 0;
    reg [63:0] in_data = 0;
    wire in_ready, out_valid, out_last;
    wire [63:0] out_data;
    integer received = 0;
    integer index;

    always #5 clk = ~clk;

    cvita_uart #(.SIZE(7)) dut (
        .clk(clk), .rst(reset), .rxd(gps_txd), .txd(),
        .i_tdata(in_data), .i_tlast(in_last),
        .i_tvalid(in_valid), .i_tready(in_ready),
        .o_tdata(out_data), .o_tlast(out_last),
        .o_tvalid(out_valid), .o_tready(1'b1)
    );

    task put_word(input [63:0] word_data, input last);
        begin
            @(negedge clk);
            in_data = word_data;
            in_last = last;
            in_valid = 1;
            @(posedge clk);
            while (!in_ready) @(posedge clk);
            @(negedge clk);
            in_valid = 0;
        end
    endtask

    task put_byte(input [7:0] value);
        integer bit_index;
        begin
            gps_txd = 0;
            repeat (DIV) @(negedge clk);
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
                gps_txd = value[bit_index];
                repeat (DIV) @(negedge clk);
            end
            gps_txd = 1;
            repeat (DIV) @(negedge clk);
        end
    endtask

    always @(posedge clk) begin
        if (out_valid && out_last) begin
            if (received >= 10 || out_data[7:0] !== MESSAGE[79-8*received -: 8])
                $fatal(1, "UART byte %0d was %02x", received, out_data[7:0]);
            received = received + 1;
        end
    end

    initial begin
        repeat (8) @(negedge clk);
        reset = 0;
        put_word(64'h0000000000030010, 0);
        put_word({16'b0, 16'd2604, 32'h20}, 1);
        repeat (DIV) @(negedge clk);
        for (index = 0; index < 10; index = index + 1)
            put_byte(MESSAGE[79-8*index -: 8]);
        repeat (DIV) @(negedge clk);
        if (received != 10) $fatal(1, "Expected 10 UART bytes, received %0d", received);
        $display("38400 baud UART to CHDR passed (%0d bytes)", received);
        $finish;
    end
endmodule
