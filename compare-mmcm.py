"""Compare the two images' named MMCM configuration bits on B210."""

import argparse
from pathlib import Path

from b210_config import REF, STOCK
DB = REF / "segbits_cmt_top_l_lower_b.db"
MMCM_FRAME = 0x00442F00


def coordinates(bits):
    for bit in bits:
        frame, offset = map(int, bit.lstrip("!").split("_"))
        yield f"bit_{MMCM_FRAME + frame:08x}_{offset // 32:03d}_{offset % 32:02d}", bit[0] != "!"


def bitset(path):
    return {line.strip() for line in path.open() if line.startswith("bit_00442f")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial", type=Path)
    args = parser.parse_args()
    stock, trial = bitset(STOCK), bitset(args.trial)
    print(f"Column bits: stock={len(stock)} trial={len(trial)}")
    count = 0
    for line in DB.read_text().splitlines():
        if not line.startswith("CMT_TOP_L_LOWER_B.MMCME2_ADV."):
            continue
        feature, *bits = line.split()
        address = tuple(coordinates(bits))
        original = all((bit in stock) == val for bit, val in address)
        new = all((bit in trial) == val for bit, val in address)
        if original != new:
            print(f"{int(original)} -> {int(new)} {feature.split('.', 2)[2]}")
            count += 1
    print(f"Different named MMCM settings: {count}")


if __name__ == "__main__":
    main()
