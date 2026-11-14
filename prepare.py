#!/usr/bin/env python3
"""Stage user-supplied B210 sources and apply the openXC7 patches."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from project import VARIANTS, apply_project


ROOT = Path(__file__).resolve().parent
IMPORTS = Path('B210_Project_Firmwire.srcs/sources_1/imports/B210_Project_Firmwire')
CONTROL = IMPORTS / 'lib/control'
PINS = 'top/b200/b210.xdc'


def stage_sources(vendor_project, variant, stage, iq_passthrough=None, project=None):
    manifest = json.loads((ROOT / 'vendor-inputs.json').read_text())
    files = {}
    for name, expected in manifest.items():
        data = (vendor_project / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'Unsupported vendor source revision: {name}')
        files[name] = ''.join(line.rstrip() + '\n' for line in data.decode('utf-8').splitlines())

    stage.mkdir(parents=True, exist_ok=False)
    for name, contents in files.items():
        if name == PINS:
            continue
        dest = stage / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(contents, encoding='utf-8', newline='\n')

    for patch in ('fpga-common', f'fpga-{variant}'):
        subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1',
                        '-i', str(ROOT / 'patches' / f'{patch}.patch')], cwd=stage, check=True)

    inputs = (ROOT / 'sources.txt').read_text().splitlines()
    for name in ('mult_macro.v', 'b210_clock.v', 'b210_pps.v'):
        shutil.copyfile(ROOT / 'rtl' / name, stage / name)
        inputs.append(name)
    pins = [line for line in files[PINS].splitlines()
            if line.startswith('set_property -dict {PACKAGE_PIN ')]
    pins.append('set_property -dict {PACKAGE_PIN B14 IOSTANDARD LVCMOS33 PULLTYPE PULLUP} [get_ports gps_txd]')
    (stage / 'pins.xdc').write_text('\n'.join(pins) + '\n', newline='\n')
    shutil.copyfile(ROOT / 'clocks.sdc', stage / 'clocks.sdc')

    extra_inputs = apply_project(project, stage, variant) if project else []
    if iq_passthrough:
        # Accept only the exact combinational identity emitted by FPGA Lab.
        pipeline = iq_passthrough.read_text(encoding='utf-8')
        canonical = ''.join(line.split('//', 1)[0] for line in pipeline.splitlines())
        canonical = ''.join(canonical.split())
        expected = ('moduleobrii_iq_pipeline(inputwireclk,inputwirereset,inputwirein_valid,'
                    'inputwiresigned[15:0]in_i,in_q,outputwireout_valid,out_trigger,'
                    'outputwiresigned[15:0]out_i,out_q);assignout_valid=in_valid;'
                    "assignout_i=in_i;assignout_q=in_q;assignout_trigger=1'b0;endmodule")
        if canonical != expected:
            raise ValueError('B210 requires the zero-latency IQ16 passthrough from FPGA Lab')
        radio = stage / IMPORTS / 'lib/radio_200/radio_legacy.v'
        source = radio.read_text(encoding='utf-8')
        ddc_port = '.sample(sample_rx), .run(run_rx), .strobe(strobe_rx),'
        declaration = '   wire [31:0] \tsample_rx;'
        if source.count(ddc_port) != 1 or source.count(declaration) != 1:
            raise ValueError('Unexpected B210 radio IQ connections')
        source = source.replace(ddc_port, '.sample(obrii_ddc_iq), .run(run_rx), .strobe(obrii_ddc_valid),')
        source = source.replace(declaration, declaration + '''
   wire [31:0] obrii_ddc_iq;
   wire obrii_ddc_valid;
   obrii_iq_pipeline obrii_iq (
      .clk(radio_clk), .reset(radio_rst), .in_valid(obrii_ddc_valid),
      .in_i(obrii_ddc_iq[31:16]), .in_q(obrii_ddc_iq[15:0]),
      .out_valid(strobe_rx), .out_trigger(), .out_i(sample_rx[31:16]), .out_q(sample_rx[15:0])
   );
''')
        radio.write_text(source, encoding='utf-8', newline='\n')
        (stage / 'obrii_iq_pipeline.v').write_text(pipeline, encoding='utf-8', newline='\n')
        inputs.append('obrii_iq_pipeline.v')

    read = f'read_verilog -D TARGET_B210 -I{CONTROL.as_posix()}'
    if project:
        read += ' -Iuser'
    commands = [f'{read} ' + ' '.join(f'"{name}"' for name in inputs)]
    if extra_inputs:
        commands.append(f'{read} -sv ' + ' '.join(f'"{name}"' for name in extra_inputs))
    commands.extend(('synth_xilinx -family xc7 -top b200 -flatten', 'check -assert', 'write_json b210.json'))
    (stage / 'synth.ys').write_text('\n'.join(commands) + '\n', newline='\n')
    print(f'Staged {len(inputs) + len(extra_inputs)} Verilog files for {variant}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vendor_project', type=Path)
    parser.add_argument('variant', choices=VARIANTS)
    parser.add_argument('stage', type=Path)
    parser.add_argument('--iq-passthrough', type=Path)
    parser.add_argument('--project', type=Path)
    args = parser.parse_args()
    try:
        stage_sources(args.vendor_project, args.variant, args.stage, args.iq_passthrough, args.project)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
