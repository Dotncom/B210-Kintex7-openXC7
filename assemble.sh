#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 VENDOR_PROJECT WORK_DIR VARIANT" >&2
    exit 2
fi
root=$(cd "$(dirname "$0")" && pwd)
vendor=$(realpath -- "$1")/B210_Project_Firmwire.runs/impl_1/b200.bit
work=$(realpath -- "$2")
variant=$3
export B210_WORK_DIR=$work
toolchain=${B210_NEXTPNR_ROOT:?Set B210_NEXTPNR_ROOT}
assembler=${B210_FPGA_AS:?Set B210_FPGA_AS}
xray=${B210_PRJXRAY_BIN:?Set B210_PRJXRAY_BIN}
part_name=xc7k325tffg676-2
test -s "$work/routed.fasm"
test ! -e "$work/$variant.bit"
test ! -e "$work/$variant.bin"
(cd "$(dirname "$vendor")" && sha256sum --check --status "$root/reference-images.sha256")

scratch=$work/assembly
refs=$work/references
mkdir -- "$scratch" "$refs"
db=$(bash "$root/prepare-db.sh" "$toolchain/share/nextpnr/external/prjxray-db" "$scratch/db")
kintex=$db/kintex7
part=$kintex/xc7k325tffg676-1/part.yaml
ln -s "$part" "$refs/xc7k325tffg676-1-part.yaml"
ln -s "$kintex/xc7k325tffg676-1/package_pins.csv" "$refs/xc7k325tffg676-1-package_pins.csv"
ln -s "$kintex/xc7k325t/tilegrid.json" "$refs/xc7k325t-tilegrid.json"
ln -s "$kintex/segbits_cmt_top_l_lower_b.db" "$refs/"
ln -s "$kintex/segbits_riob18.db" "$refs/"

"$xray/bitread" -y -z -part_file "$part" -o "$work/vendor-b210.bits" "$vendor"
python3 "$root/normalize-siso-fasm.py" "$work/routed.fasm" "$scratch/normalized.fasm"
python3 "$root/apply-stock-mmcm.py" "$scratch/normalized.fasm" "$scratch/mmcm.fasm"
python3 "$root/apply-stock-clock-io.py" "$scratch/mmcm.fasm" "$scratch/clocks.fasm"

mv "$kintex/segbits_rioi.db" "$kintex/segbits_rioi.upstream"
cat "$kintex/segbits_rioi.upstream" > "$kintex/segbits_rioi.db"
printf '\nRIOI.TRIAL_ODDR_OMUX_Q !33_111\n' >> "$kintex/segbits_rioi.db"
"$assembler" --prjxray_db_path="$kintex" --part "$part_name" \
    "$scratch/clocks.fasm" > "$scratch/pre.bit"

read_io() {
    "$xray/bitread" -y -z -F 0x00402F80:0x00402FA9 -part_file "$part" \
        -o "$scratch/$1-gpif.bits" "$2"
    "$xray/bitread" -y -z -F 0x00442F80:0x00442FA9 -part_file "$part" \
        -o "$scratch/$1-codec.bits" "$2"
}

read_io before "$scratch/pre.bit"
python3 "$root/match-siso-strobe-io.py" "$work/routed.fasm" "$scratch/before-gpif.bits" \
    "$scratch/before-codec.bits" "$scratch/patch.frames"
"$xray/xc7patch" -part_file "$part" -part_name "$part_name" \
    -bitstream_file "$scratch/pre.bit" -frm_file "$scratch/patch.frames" \
    -output_file "$scratch/post.bit"
read_io after "$scratch/post.bit"
python3 "$root/match-siso-strobe-io.py" "$work/routed.fasm" "$scratch/before-gpif.bits" \
    "$scratch/before-codec.bits" "$scratch/patch.frames" \
    --verify "$scratch/after-gpif.bits" "$scratch/after-codec.bits"

"$xray/bitread" -y -z -F 0x00442F00:0x00442F1D -part_file "$part" \
    -o "$scratch/mmcm.bits" "$scratch/post.bit"
python3 "$root/compare-mmcm.py" "$scratch/mmcm.bits" | tee "$scratch/mmcm.log"
grep -Fxq 'Different named MMCM settings: 0' "$scratch/mmcm.log"
python3 "$root/bit-to-b210-bin.py" "$scratch/post.bit" "${vendor%.bit}.bin" "$scratch/post.bin"
cp -- "$scratch/post.bit" "$work/$variant.bit"
cp -- "$scratch/post.bin" "$work/$variant.bin"
