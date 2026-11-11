#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 VENDOR_PROJECT b210-dual-fabric|b210-siso-strobe NEW_WORK_DIR" >&2
    exit 2
fi
root=$(cd "$(dirname "$0")" && pwd)
vendor=$(realpath -- "$1")
variant=$2
work=$(realpath -m -- "$3")
case "$variant" in
    b210-dual-fabric) radios=2 ;;
    b210-siso-strobe) radios=1 ;;
    *) echo "Unknown variant: $variant" >&2; exit 2 ;;
esac
yosys=${B210_YOSYS:?Set B210_YOSYS to the Yosys executable}
toolchain=${B210_NEXTPNR_ROOT:?Set B210_NEXTPNR_ROOT to the nextpnr installation}
chipdb=$(realpath -- "${B210_CHIPDB:?Set B210_CHIPDB to the FFG676 chip database}")
export B210_WORK_DIR=$work
mkdir -- "$work"

echo "Staging $variant"
python3 "$root/prepare.py" "$vendor" "$variant" "$work/src"
iverilog -g2012 -s pps_tb -o "$work/pps-test" "$root/rtl/b210_pps.v" "$root/tests/pps_tb.v"
vvp "$work/pps-test"

cd "$work/src"
echo "Synthesizing. Log: $work/synth.log"
"$yosys" -Q -s synth.ys >"$work/synth.log" 2>&1
python3 "$root/check-ddc-strobe.py" b210.json --radios "$radios"
echo "Routing. Log: $work/route.log"
"$toolchain/bin/nextpnr-himbaechel" --chipdb "$chipdb" \
    --device xc7k325tffg676-2 --placer "${B210_PLACER:-heap}" --threads "${B210_THREADS:-1}" \
    -o xdc=pins.xdc --sdc clocks.sdc --json b210.json \
    -o "fasm=$work/routed.fasm" --report "$work/route.json" >"$work/route.log" 2>&1
python3 "$root/verify-dual-fabric-route.py" "$work/route.log" --netlist b210.json --radios "$radios"

echo "Assembling. Log: $work/assemble.log"
bash "$root/assemble.sh" "$vendor" "$work" "$variant" >"$work/assemble.log" 2>&1
cd "$work"
sha256sum "$variant.bin" | tee "$variant.bin.sha256"
