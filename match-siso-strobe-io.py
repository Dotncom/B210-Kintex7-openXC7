"""Reapply and verify the B210 pin-local corrections on a new routed image."""

import argparse
import json
from pathlib import Path
import re


from b210_config import REF, STOCK, feature_bits, key, pad_locations, positions_for, read_bits


def pin_bits(pattern, count, bank, fields):
    pads = pad_locations(pattern, count, bank)
    addresses = positions_for(pads, fields)
    if len(addresses) != count:
        raise ValueError(f"Expected one bit per pad for {pattern}")
    return {key(*address) for address in addresses}


def tile_feature_bits(grid, tile, features):
    location = grid[tile]["bits"]["CLB_IO_CLK"]
    base = int(location["baseaddr"], 16)
    offset = location["offset"]
    return {key(*address)
            for address in feature_bits(base, offset, features)}


def right_bank_enables(grid, routed_fasm):
    db = (REF / "segbits_riob18.db").read_text().splitlines()
    feature = "RIOB18.IOB_Y0.LVCMOS12_LVCMOS15_LVCMOS18.IN"
    entry = next(line.split()[1:] for line in db if line.startswith(feature + " "))
    tiles = re.findall(r"^(RIOB18_X\d+Y\d+)\.IOB_Y0\.IBUF_HP_BANK_GLUE$",
                       routed_fasm.read_text(), re.MULTILINE)
    if not tiles or len(set(tiles)) != len(tiles):
        raise ValueError("Expected unique right-bank input enable substitutions")
    return set().union(*(tile_feature_bits(grid, tile,
                                      [value.lstrip("!") for value in entry])
                         for tile in tiles))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("routed_fasm", type=Path)
    parser.add_argument("before_gpif", type=Path)
    parser.add_argument("before_codec", type=Path)
    parser.add_argument("frames", type=Path)
    parser.add_argument("--verify", nargs=2, type=Path, metavar=("GPIF", "CODEC"))
    args = parser.parse_args()

    grid = json.loads((REF / "xc7k325t-tilegrid.json").read_bytes())
    stock = read_bits(STOCK)
    before = read_bits(args.before_gpif) | read_bits(args.before_codec)

    # GPIF pads require OLOGIC.ZINV_T1. The codec TX pads and feedback clock
    # use the ODDR output instead of the direct OMUX.D1 bypass.
    gpif = pin_bits(r"GPIF_D\[\d+\]", 32, "34",
                    {"IOB18M": [(30, 67)], "IOB18S": [(31, 60)]})
    codec = pin_bits(r"tx_codec_d\[\d+\]|tx_frame_p|codec_fb_clk_p", 14, "32",
                     {"IOB18M": [(33, 111)], "IOB18S": [(32, 16)]})
    if not gpif <= stock or codec & stock:
        raise ValueError("Vendor GPIF polarity or codec ODDR mux differs from the reference")

    # Match IFCLK OMUX.D1, ODDR.SRUSED and ZSRVAL_OQ on the fixed IFCLK pad.
    ifclk = tile_feature_bits(grid, "RIOB18_X95Y109",
                         ("33_111", "32_112", "32_108", "33_107", "33_095"))
    # Match the fixed differential codec reference input's glue and low-power fields.
    lvds = tile_feature_bits(grid, "RIOB18_X95Y27",
                        ("38_008", "38_028", "38_040", "39_015", "39_021",
                         "39_037", "39_041", "38_124", "39_003"))
    normalized = right_bank_enables(grid, args.routed_fasm)
    if (before ^ stock) & normalized:
        raise ValueError("Normalized right-bank input enables differ from the reference")

    selected = gpif | codec | ifclk | lvds
    expected = (before - selected) | (stock & selected)
    delta = before ^ expected
    frames = sorted({int(bit.split("_")[1], 16) for bit in delta})
    if args.verify:
        actual = set().union(*(read_bits(path) for path in args.verify))
        if actual != expected:
            raise ValueError(f"Unexpected bank configuration delta: {len(actual ^ expected)} bits")
        print(f"Verified {len(delta)} changed bits in {len(frames)} frames and "
              f"{len(normalized)} normalized input-enable bits")
        return

    if not delta:
        raise ValueError("No frame changes were required. Check the openXC7 version before proceeding")
    with args.frames.open("w") as destination:
        for frame in frames:
            words = [sum(1 << bit for bit in range(32)
                         if key(frame, word, bit) in expected)
                     for word in range(101)]
            destination.write(f"{frame:08x} " + ",".join(f"{word:08x}" for word in words) + "\n")


if __name__ == "__main__":
    main()
