#!/usr/bin/env python3
"""Recover service, characteristic and descriptor declarations from btsnoop ATT.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import json
import struct
import uuid

from btsnoop import iter_att, load


def uuid_text(raw: bytes) -> str:
    if len(raw) == 2:
        return f"0x{struct.unpack('<H', raw)[0]:04x}"
    if len(raw) == 16:
        return str(uuid.UUID(bytes=raw[::-1]))
    return raw.hex()


def chunks(data: bytes, width: int):
    for offset in range(0, len(data), width):
        item = data[offset:offset + width]
        if len(item) == width:
            yield item


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture")
    args = parser.parse_args()

    services: set[tuple[int, int, str]] = set()
    characteristics: set[tuple[int, int, int, str]] = set()
    descriptors: set[tuple[int, str]] = set()
    pending: dict[tuple[int, str, int], int] = {}

    for record in iter_att(load(args.capture)):
        reverse = "rx" if record.direction == "tx" else "tx"
        if record.opcode in (0x08, 0x10) and len(record.body) >= 6:
            requested_type = struct.unpack("<H", record.body[4:6])[0]
            response_opcode = 0x09 if record.opcode == 0x08 else 0x11
            pending[(record.connection_handle, reverse, response_opcode)] = requested_type
            continue

        if record.opcode == 0x11 and record.body:
            requested = pending.pop((record.connection_handle, record.direction, 0x11), None)
            if requested != 0x2800:
                continue
            width = record.body[0]
            for item in chunks(record.body[1:], width):
                if width in (6, 20):
                    start, end = struct.unpack("<HH", item[:4])
                    services.add((start, end, uuid_text(item[4:])))

        elif record.opcode == 0x09 and record.body:
            requested = pending.pop((record.connection_handle, record.direction, 0x09), None)
            if requested != 0x2803:
                continue
            width = record.body[0]
            for item in chunks(record.body[1:], width):
                if width in (7, 21):
                    declaration = struct.unpack("<H", item[:2])[0]
                    properties = item[2]
                    value_handle = struct.unpack("<H", item[3:5])[0]
                    characteristics.add((declaration, properties, value_handle, uuid_text(item[5:])))

        elif record.opcode == 0x05 and record.body:
            fmt = record.body[0]
            width = 4 if fmt == 1 else 18 if fmt == 2 else 0
            if width:
                for item in chunks(record.body[1:], width):
                    handle = struct.unpack("<H", item[:2])[0]
                    descriptors.add((handle, uuid_text(item[2:])))

    result = {
        "services": [
            {"start": f"0x{s:04x}", "end": f"0x{e:04x}", "uuid": value}
            for s, e, value in sorted(services)
        ],
        "characteristics": [
            {
                "declaration_handle": f"0x{decl:04x}",
                "properties": f"0x{props:02x}",
                "value_handle": f"0x{value_handle:04x}",
                "uuid": value,
            }
            for decl, props, value_handle, value in sorted(characteristics)
        ],
        "descriptors": [
            {"handle": f"0x{handle:04x}", "uuid": value}
            for handle, value in sorted(descriptors)
        ],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

