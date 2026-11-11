"""Normalize the right-bank input enable against this B210 vendor image."""

import argparse
import json
from pathlib import Path
import re


from b210_config import REF, STOCK
GLUE = "IOB_Y0.IBUF_HP_BANK_GLUE"
ENABLE = "IOB_Y0.LVCMOS12_LVCMOS15_LVCMOS18.IN"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    tiles = json.loads((REF / "xc7k325t-tilegrid.json").read_bytes())
    bits = set((STOCK).read_text().splitlines())
    db = (REF / "segbits_riob18.db").read_text().splitlines()
    features = {line.split()[0]: line.split()[1:] for line in db if line.strip()}
    if f"RIOB18.{GLUE}" in features:
        raise ValueError("Database already defines this feature")
    expected = features[f"RIOB18.{ENABLE}"]

    source = args.source.read_text()
    pattern = re.compile(rf"^(RIOB18_X\d+Y\d+)\.{re.escape(GLUE)}$", re.MULTILINE)
    changed = []

    def replace(match):
        tile = match[1]
        loc = tiles[tile]["bits"]["CLB_IO_CLK"]
        base, offset = int(loc["baseaddr"], 16), loc["offset"]
        for feature_bit in expected:
            frame, bit = (int(n) for n in feature_bit.lstrip("!").split("_"))
            address = f"bit_{base + frame:08x}_{offset + bit // 32:03d}_{bit % 32:02d}"
            if (address in bits) == feature_bit.startswith("!"):
                raise ValueError(f"Vendor image disagrees with {tile}.{ENABLE} at {address}")
        changed.append(tile)
        return f"{tile}.{ENABLE}"

    corrected = pattern.sub(replace, source)
    if not changed:
        raise ValueError("No right-bank input enable substitutions")
    args.destination.write_text(corrected, newline="\n")
    print(f"Matched {len(changed)} right-bank input enables to the vendor image")


if __name__ == "__main__":
    main()
