#!/usr/bin/env python3
"""Stage user-supplied B210 sources and apply the openXC7 patches."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent
IMPORTS = Path('B210_Project_Firmwire.srcs/sources_1/imports/B210_Project_Firmwire')
CONTROL = IMPORTS / 'lib/control'
PINS = 'top/b200/b210.xdc'
VARIANTS = ('b210-dual-fabric', 'b210-siso-strobe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vendor_project', type=Path)
    parser.add_argument('variant', choices=VARIANTS)
    parser.add_argument('stage', type=Path)
    args = parser.parse_args()

    manifest = json.loads((ROOT / 'vendor-inputs.json').read_text())
    files = {}
    for name, expected in manifest.items():
        data = (args.vendor_project / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f'Unsupported vendor source revision: {name}')
        files[name] = ''.join(line.rstrip() + '\n' for line in data.decode('utf-8').splitlines())

    args.stage.mkdir(parents=True, exist_ok=False)
    for name, contents in files.items():
        if name == PINS:
            continue
        dest = args.stage / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(contents, encoding='utf-8', newline='\n')

    for patch in ('fpga-common', f'fpga-{args.variant}'):
        subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1',
                        '-i', str(ROOT / 'patches' / f'{patch}.patch')], cwd=args.stage, check=True)

    inputs = (ROOT / 'sources.txt').read_text().splitlines()
    for name in ('mult_macro.v', 'b210_clock.v', 'b210_pps.v'):
        shutil.copyfile(ROOT / 'rtl' / name, args.stage / name)
        inputs.append(name)
    rtl = ' '.join(f'"{name}"' for name in inputs)
    (args.stage / 'synth.ys').write_text(
        f'read_verilog -D TARGET_B210 -I{CONTROL.as_posix()} {rtl}\n'
        'synth_xilinx -family xc7 -top b200 -flatten\n'
        'check -assert\nwrite_json b210.json\n', newline='\n')

    pins = [line for line in files[PINS].splitlines()
            if line.startswith('set_property -dict {PACKAGE_PIN ')]
    pins.append('set_property -dict {PACKAGE_PIN B14 IOSTANDARD LVCMOS33 PULLTYPE PULLUP} [get_ports gps_txd]')
    (args.stage / 'pins.xdc').write_text('\n'.join(pins) + '\n', newline='\n')
    shutil.copyfile(ROOT / 'clocks.sdc', args.stage / 'clocks.sdc')
    print(f'Staged {len(inputs)} Verilog files for {args.variant}')


if __name__ == '__main__':
    main()
