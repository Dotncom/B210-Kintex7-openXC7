# B210 Kintex-7 openXC7

Experimental openXC7 build for the OpenSourceSDRLab B210 clone with a
`xc7k325tffg676-2`. The dual-radio variant preserves both RX and TX paths
and routes the board's read-only GNSS UART into the UHD control stream.
The single-radio variant bypasses the MIMO clock divider.

- `patches/fpga-common.patch` connects the GPS UART, applies the DDC strobe
  corrections and installs the replacement clock and PPS paths.
- The two variant patches select the radio count and clock routing. The dual
  variant uses a fabric divider where the open router cannot route BUFR to
  BUFGMUX on this part.
- `rtl/b210_clock.v` builds the 100 MHz GPIF and bus clock from the 40 MHz
  differential input using a Series 7 MMCM with globally buffered feedback.
- `rtl/b210_pps.v` synchronizes the GPS, external and synthesized PPS signals
  separately, then selects a source with the existing UHD control register.

## Build on Linux or WSL

Install Python 3.10+, GNU `patch`, Bash, Icarus Verilog and the
[openXC7 toolchain](https://github.com/openXC7/toolchain-nix). Acquire the
[vendor FPGA project](https://github.com/OpenSourceSDRLab/B210-Kintex-7)
separately. Extract the project including its imported Verilog and
`B210_Project_Firmwire.runs/impl_1/b200.bit` and `b200.bin` files. The
`vendor-inputs.json` and `reference-images.sha256` manifests identify the
revision this build accepts.

Set `B210_YOSYS` to the Yosys executable, `B210_NEXTPNR_ROOT` to the
nextpnr prefix with its bundled Xilinx metadata and Project X-Ray database,
`B210_FPGA_AS` to the `fpga-as` executable and `B210_PRJXRAY_BIN` to the
directory containing `bitread` and `xc7patch`. Set `B210_CHIPDB` to the
`xc7k325t.bin` matching that nextpnr installation, or generate it with:

```sh
mkdir -p work
bash make-chipdb.sh work/chipdb
export B210_CHIPDB="$PWD/work/chipdb/xc7k325t.bin"
bash build.sh /path/to/B210_Project_Firmwire b210-dual-fabric work/dual
```

Each output directory must be new. Use `b210-siso-strobe` as the variant for
single-radio synthesis. The flow
simulates PPS, synthesizes the design, checks the IQ strobe in each radio,
routes, then assembles the `.bit` and raw UHD `.bin`. Logs and SHA-256 are
written to the work directory. Assembly derives a small set of board I/O
settings from the locally supplied stock reference, checks the MMCM
configuration and compares the device IDCODE.

Run `bash tests/check-uart.sh work/dual/src work/dual/uart-test` to check
the 38400 baud UART-to-CHDR path with a synthetic NMEA line.

The tested tool builds were Yosys 0.67, nextpnr-himbaechel 1.0.0,
fpga-as 0.0.1 and Project X-Ray 0.9.2. The tested Kintex-7 chip database
has SHA-256 `8ee790e25cec5a5593363e52e708a70f68eb0a525164d53fb8057cac16407511`.
The package overlay uses the FFG676 pin map and generic openXC7 timing
when the exact FFG676-2 record is missing. The timing report is a routing
estimate. Hardware validation of a new image is a separate step.

## GNSS on the host

In a checkout of [Ettus UHD v4.3.0.0](https://github.com/EttusResearch/uhd/tree/v4.3.0.0),
apply `patches/uhd-4.3-b210-gnss.patch` followed by
`patches/uhd-4.3-b210-gsv.patch` with `git apply`, then build UHD. Open the
receiver with `b210_gnss_baud=38400` to expose `gnss_gga`, `gnss_rmc` and
`gnss_gsv`. Select the local FPGA file explicitly with `fpga=/path/to/image.bin`
for a temporary UHD load. GNSS sentence reception and PPS time-source selection
are independent.

See [licensing and provenance](NOTICE.md) for the source and input boundaries.
