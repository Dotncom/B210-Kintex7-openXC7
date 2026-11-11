"""Extract and check the raw B210 configuration stream."""

import argparse
import hashlib
from pathlib import Path


PART = b"xc7k325tffg676-2"
SYNC = bytes.fromhex("AA995566")
WRITE_IDCODE = bytes.fromhex("30018001")


def read_payload(bit):
    position = 2 + int.from_bytes(bit[:2], "big")
    if bit[position:position + 2] != b"\x00\x01":
        raise ValueError("Invalid bitstream header")
    position += 2
    headers = {}
    for tag in b"abcde":
        if bit[position] != tag:
            raise ValueError(f"Missing bitstream tag {chr(tag)}")
        position += 1
        width = 4 if tag == ord("e") else 2
        size = int.from_bytes(bit[position:position + width], "big")
        position += width
        end = position + size
        if end > len(bit):
            raise ValueError("Truncated bitstream")
        headers[chr(tag)] = bit[position:end]
        position = end
    if position != len(bit) or headers["b"].rstrip(b"\x00") != PART:
        raise ValueError("Unexpected part or trailing bytes")
    return headers["e"]


def read_idcode(payload):
    sync = payload.find(SYNC, 0, 512)
    if sync < 0:
        raise ValueError("Missing configuration sync word")
    for offset in range(sync + 4, min(1024, len(payload) - 7), 4):
        if payload[offset:offset + 4] == WRITE_IDCODE:
            return int.from_bytes(payload[offset + 4:offset + 8], "big")
    raise ValueError("Missing configuration IDCODE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bit", type=Path)
    parser.add_argument("vendor", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = read_payload(args.bit.read_bytes())
    vendor = args.vendor.read_bytes()
    idcode = read_idcode(payload)
    if idcode != read_idcode(vendor):
        raise ValueError(f"Unexpected IDCODE {idcode:#010x}")
    args.output.write_bytes(payload)
    print(f"IDCODE {idcode:#010x}, {len(payload)} bytes")
    print(hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    main()
