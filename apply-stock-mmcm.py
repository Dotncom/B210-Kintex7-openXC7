"""Use the vendor mode and output enables for the identical B210 MMCM site."""

import argparse
from pathlib import Path


MMCM = "CMT_TOP_L_LOWER_B_X228Y9.MMCME2_ADV."
DISABLED_DIVIDES = {0: 25, 2: 10, 3: 1, 4: 1, 5: 1, 6: 1}


def counter_features(output, divide):
    prefix = f"{MMCM}CLKOUT{output}_"
    high, low = max(1, divide // 2), (divide + 1) // 2
    yield f"{prefix}CLKOUT1_HIGH_TIME[5:0] = 6'b{high:06b}"
    yield f"{prefix}CLKOUT1_LOW_TIME[5:0] = 6'b{low:06b}"
    if divide == 1:
        suffix = "FRACTIONAL_" if output in (5, 6) else ""
        yield f"{prefix}CLKOUT2_{suffix}NO_COUNT[0]"
    elif divide % 2:
        yield f"{prefix}CLKOUT2_EDGE[0]"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = args.source.read_text()
    for feature in ("IN_USE", "CLKOUT1_CLKOUT1_OUTPUT_ENABLE[0]", "COMP.Z_ZHOLD"):
        if source.count(f"{MMCM}{feature}\n") != 1:
            raise ValueError(f"Expected one {MMCM}{feature} feature")
    source = source.replace(f"{MMCM}COMP.Z_ZHOLD\n", f"{MMCM}COMP.ZHOLD\n", 1)
    missing = []
    for output, divide in DISABLED_DIVIDES.items():
        prefix = f"{MMCM}CLKOUT{output}_"
        enabled = f"{prefix}CLKOUT1_OUTPUT_ENABLE[0]\n"
        if source.count(enabled) > 1:
            raise ValueError(f"Duplicate {enabled.strip()} feature")
        source = source.replace(enabled, "", 1)
        if prefix not in source:
            # The primitive-only clock wrapper leaves these pins disconnected.
            # Restore their divider fields without enabling the outputs.
            missing.extend(counter_features(output, divide))
    args.destination.write_text(source + "\n" + "\n".join(missing) + "\n", newline="\n")


if __name__ == "__main__":
    main()
