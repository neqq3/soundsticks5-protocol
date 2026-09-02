#!/usr/bin/env python3
"""Extract ATT writes, notifications and values from a btsnoop file.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import collections
import json
import struct

from btsnoop import iter_att, load
from ss5_protocol import ProtocolError, decode_frame

VALUE_OPS = {0x12, 0x16, 0x1B, 0x1D, 0x52, 0xD2}


def split_value(opcode: int, body: bytes) -> tuple[int | None, bytes]:
    if opcode in VALUE_OPS and len(body) >= 2:
        return struct.unpack("<H", body[:2])[0], body[2:]
    if opcode == 0x0B:
        return None, body
    return None, b""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture")
    parser.add_argument("--aa-only", action="store_true", help="show only values starting with 0xaa")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rows = []
    counts: collections.Counter[str] = collections.Counter()
    for record in iter_att(load(args.capture)):
        counts[record.name] += 1
        attribute_handle, value = split_value(record.opcode, record.body)
        if args.aa_only and not value.startswith(b"\xaa"):
            continue
        row: dict[str, object] = {
            "record": record.index,
            "direction": record.direction,
            "connection_handle": f"0x{record.connection_handle:04x}",
            "operation": record.name,
        }
        if attribute_handle is not None:
            row["attribute_handle"] = f"0x{attribute_handle:04x}"
        if value:
            row["value_hex"] = value.hex(" ")
            if value.startswith(b"\xaa"):
                try:
                    row["aa_frame"] = decode_frame(value).as_dict()
                except ProtocolError as exc:
                    row["aa_decode_error"] = str(exc)
        rows.append(row)

    if args.stats:
        print(json.dumps(dict(counts), indent=2))
    elif args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for row in rows:
            handle = row.get("attribute_handle", "------")
            value = row.get("value_hex", "")
            print(
                f"#{row['record']:05d} {row['direction'].upper()} "
                f"conn={row['connection_handle']} attr={handle} "
                f"{row['operation']}: {value}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

