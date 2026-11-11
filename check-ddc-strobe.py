"""Inspect the synthesized DDC and its two IQ strobe consumers."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("netlist", type=Path)
    parser.add_argument("--expect-dead", action="store_true")
    parser.add_argument("--radios", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    design = json.loads(args.netlist.read_bytes())
    nets = design["modules"]["b200"]["netnames"]
    names = ("ddc_chain.old_hb.unscaled_clip_i.reset", "ddc_chain.old_hb.clip_i.reset",
             "ddc_chain.old_hb.strobe_unscaled_clip", "ddc_chain.old_hb.strobe_clip",
             "ddc_chain.strobe", "strobe_rx", "new_rx_framer.strobe", "new_rx_control.strobe")
    for channel in range(args.radios):
        radio = f"b200_core.radio_{channel}."
        bits = [nets[radio + name]["bits"] for name in names]
        for name, value in zip(names, bits):
            print(f"{radio}{name}: {value}")
        if args.expect_dead:
            assert bits[:2] == [["x"], ["x"]] and all(value == ["0"] for value in bits[2:])
        else:
            assert all(len(value) == 1 and isinstance(value[0], int) for value in bits)
            assert bits[0] == bits[1] and all(value == bits[4] for value in bits[4:])


if __name__ == "__main__":
    main()
