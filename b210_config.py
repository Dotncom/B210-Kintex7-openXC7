"""Read Project X-Ray bit addresses and locate B210 package pins."""

import csv
import json
import os
from pathlib import Path
import re


WORK = Path(os.environ["B210_WORK_DIR"])
REF = WORK / "references"
STOCK = WORK / "vendor-b210.bits"


def feature_bits(base, offset, fields):
    for field in fields:
        frame, bit = map(int, field.split("_"))
        yield base + frame, offset + bit // 32, bit % 32


def read_bits(path):
    with path.open() as source:
        return {line.strip() for line in source
                if line.startswith(("bit_00402f", "bit_00442f"))}


def key(frame, word, bit):
    return f"bit_{frame:08x}_{word:03d}_{bit:02d}"


def pad_locations(pattern, count, bank):
    with (REF / "xc7k325tffg676-1-package_pins.csv").open() as stream:
        pins = {row["pin"]: row for row in csv.DictReader(stream)}
    grid = json.loads((REF / "xc7k325t-tilegrid.json").read_bytes())
    xdc = (WORK / "src/pins.xdc").read_text()
    selected = re.findall(r"PACKAGE_PIN (\w+) [^\n]+get_ports \{?(" + pattern + r")", xdc)
    if len(selected) != count or len(set(selected)) != count:
        raise ValueError(f"Expected {count} distinct matching pad assignments")
    for pin, signal in selected:
        pad = pins[pin]
        tile = grid[pad["tile"]]
        if tile["type"] != "RIOB18" or pad["bank"] != bank:
            raise ValueError(f"Unexpected I/O bank for {signal} on {pin}")
        site = tile["sites"][pad["site"]]
        loc = tile["bits"]["CLB_IO_CLK"]
        yield site, int(loc["baseaddr"], 16), loc["offset"]


def positions_for(pads, fields):
    positions = {(base + frame, offset + bit // 32, bit % 32)
                 for site, base, offset in pads
                 for frame, bit in fields[site]}
    return positions
