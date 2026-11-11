// SPDX-License-Identifier: LGPL-3.0-or-later
`timescale 1ns/1ps
module pps_tb;
    reg clk = 0;
    always #5 clk = ~clk;
    reg reset = 1;
    reg [2:0] inputs = 0;
    reg [1:0] source = 0;
    wire pps;

    b210_pps dut(clk, reset, inputs[0], inputs[1], inputs[2], source, pps);

    task tick;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    task check;
        input expected;
        begin
            if (pps !== expected)
                $fatal(1, "source %0d inputs %b got %b expected %b", source, inputs, pps, expected);
        end
    endtask

    integer i;
    initial begin
        tick;
        check(0);
        reset = 0;
        for (i = 0; i < 3; i = i + 1) begin
            source = i;
            inputs = 3'b111 ^ (3'b001 << i);
            tick; tick;
            check(0);
            inputs = 3'b001 << i;
            tick;
            check(0);
            tick;
            check(1);
            tick;
            check(1);
            inputs = 0;
            tick;
            check(1);
            tick;
            check(0);
        end
        source = 3;
        inputs = 7;
        tick; tick;
        check(0);
        source = 0;
        #1;
        check(1);
        reset = 1;
        tick;
        check(0);
        $display("PPS source isolation, latency and reset passed");
        $finish;
    end
endmodule
