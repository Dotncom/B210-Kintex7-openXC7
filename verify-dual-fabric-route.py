"""Check post-route timing and architecture before assembling the B210 trial."""

import argparse
import json
from pathlib import Path
import re


def unused_mmcm_output(line, cells, ports):
    match = re.fullmatch(r"ERROR: No wire found for port (CLKOUT[0-6]B?) on source cell (.+)\.", line)
    if not match:
        return False
    port, name = match.groups()
    cell = cells.get(name)
    if not cell or cell['type'] != 'MMCME2_ADV' or port == 'CLKOUT1':
        return False
    bits = set(cell['connections'].get(port, ()))
    if any(bits.intersection(pin['bits']) for pin in ports.values()):
        return False
    return not any(bits.intersection(pin_bits)
                   for instance in cells.values()
                   for pin, pin_bits in instance['connections'].items()
                   if instance['port_directions'].get(pin) in ('input', 'inout'))


def check_route(log, design, radios):
    if not log.rstrip().endswith("Info: Program finished normally."):
        raise ValueError("nextpnr did not finish normally")

    convergence = re.findall(
        r"overused=(\d+) overuse=(\d+) archfail=(\d+|NA)", log)
    if not convergence or convergence[-1] != ("0", "0", "0"):
        raise ValueError("Router2 did not prove zero overuse and architecture failures")

    legal_check = "Info: Running router1 to check that route is legal..."
    if log.count(legal_check) != 1:
        raise ValueError("Expected one post-route legal check")
    _, post_route = log.split(legal_check, 1)
    errors = [line for line in log.splitlines() if line.startswith("ERROR:")]
    if any(line not in post_route or not unused_mmcm_output(line, design['cells'], design['ports'])
           for line in errors):
        raise ValueError("Unexpected router error: " + " | ".join(errors))

    timing = re.findall(
        r"Max frequency for clock\s+'([^']+)':\s+([\d.]+) MHz "
        r"\((PASS|FAIL) at ([\d.]+) MHz\)", post_route)
    limits = {"bus_clk": 100.0, "radio_clk": 61.44}
    if radios == 2:
        limits["b200_io_i0.rx_clk_bufr"] = 61.44
    actual = {name: float(target) for name, _, _, target in timing}
    if any(actual.get(name) != limit for name, limit in limits.items()):
        raise ValueError("Post-route report lacks an expected clock constraint")
    for name, frequency, result, target in timing:
        if result != "PASS":
            raise ValueError(f"Post-route timing failed for {name}: {frequency} < {target} MHz")
        print(f"{name}: {frequency} MHz (PASS at {target} MHz)")
    if errors:
        print("Post-route legality messages were confined to unused MMCM outputs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--netlist', type=Path, required=True)
    parser.add_argument('--radios', type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    try:
        design = json.loads(args.netlist.read_bytes())['modules']['b200']
        check_route(args.log.read_text(encoding="utf-8"), design, args.radios)
    except ValueError as error:
        raise SystemExit(str(error)) from error
