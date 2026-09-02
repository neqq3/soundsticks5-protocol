#!/usr/bin/env python3
"""Decode one SoundSticks 5 AA frame as JSON.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import json

from ss5_protocol import ProtocolError, decode_frame, parse_hex


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hex_frame", help="frame bytes, for example 'aa 41 00'")
    parser.add_argument("--allow-trailing", action="store_true")
    args = parser.parse_args()
    try:
        frame = decode_frame(parse_hex(args.hex_frame), allow_trailing=args.allow_trailing)
    except ProtocolError as exc:
        parser.error(str(exc))
    print(json.dumps(frame.as_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

