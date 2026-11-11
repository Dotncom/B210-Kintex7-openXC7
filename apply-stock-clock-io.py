"""Match the clock I/O configuration to the vendor settings on the same pads."""

import argparse
from pathlib import Path


REMOVE = (
    "RIOI_X95Y109.OLOGIC_Y0.ODDR.SRUSED",
    "RIOI_X95Y109.OLOGIC_Y0.ZSRVAL_OQ",
    "RIOB18_X95Y27.DIFF.ZIBUF_LOW_PWR",
    "RIOB18_X95Y27.IOB_Y0.IBUFDS_BANK_GLUE",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = args.source.read_text()
    for feature in REMOVE:
        line = feature + "\n"
        if source.count(line) != 1:
            raise ValueError(f"Expected one {feature} feature")
        source = source.replace(line, "", 1)
    # RIOI.OLOGIC_Y0.OMUX.D1 is bit 33_111. Force that documented
    # bypass select clear to match Vivado's ODDR-sourced IFCLK.
    source += "\nRIOI_X95Y109.TRIAL_ODDR_OMUX_Q\n"
    args.destination.write_text(source, newline="\n")


if __name__ == "__main__":
    main()
