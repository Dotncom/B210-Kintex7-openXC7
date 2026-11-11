#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 NEW_WORK_DIR" >&2
    exit 2
fi
root=$(cd "$(dirname "$0")" && pwd)
work=$(realpath -m -- "$1")
toolchain=${B210_NEXTPNR_ROOT:?Set B210_NEXTPNR_ROOT}
arch=$toolchain/share/nextpnr/himbaechel/uarch/xilinx
mkdir -- "$work"
db=$(bash "$root/prepare-db.sh" "$toolchain/share/nextpnr/external/prjxray-db" "$work/db")
python3 "$root/generate-chipdb.py" "$arch/gen/xilinx_gen.py" \
    --xray "$db/kintex7" --metadata "$arch/meta/kintex7" --device xc7k325t \
    --bba "$work/xc7k325t.bba"
"$toolchain/bin/bbasm" -l "$work/xc7k325t.bba" "$work/xc7k325t.bin"
sha256sum "$work/xc7k325t.bin"
