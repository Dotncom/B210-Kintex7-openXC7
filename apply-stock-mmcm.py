"""Use the vendor mode and output enables for the identical B210 MMCM site."""

import argparse
from pathlib import Path


MMCM = "CMT_TOP_L_LOWER_B_X228Y9.MMCME2_ADV."
UNUSED_OUTPUTS = (0, 2, 3, 4, 5, 6)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = args.source.read_text()
    changes = {f"{MMCM}COMP.Z_ZHOLD\n": f"{MMCM}COMP.ZHOLD\n"}
    changes.update({f"{MMCM}CLKOUT{out}_CLKOUT1_OUTPUT_ENABLE[0]\n": ""
                    for out in UNUSED_OUTPUTS})
    for before, after in changes.items():
        if source.count(before) != 1:
            raise ValueError(f"Expected one {before.strip()} feature")
        source = source.replace(before, after, 1)
    args.destination.write_text(source, newline="\n")


if __name__ == "__main__":
    main()
