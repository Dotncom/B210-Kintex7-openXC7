#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 STAGED_FPGA_SOURCE OUTPUT_VVP" >&2
    exit 2
fi
root=$(cd "$(dirname "$0")" && pwd)
lib=$1/B210_Project_Firmwire.srcs/sources_1/imports/B210_Project_Firmwire/lib
iverilog -g2012 -s uart_smoke -I "$lib/control" -o "$2" "$root/uart_tb.v" \
    "$lib/control_200/cvita_uart.v" "$lib/vita_200/context_packet_gen.v" \
    "$lib/wishbone/simple_uart_rx.v" "$lib/wishbone/simple_uart_tx.v" \
    "$lib/fifo/axi_fifo.v" "$lib/fifo/axi_fifo_bram.v" \
    "$lib/fifo/axi_fifo_flop.v" "$lib/fifo/axi_fifo_flop2.v" "$lib/control/ram_2port.v"
vvp "$2"
