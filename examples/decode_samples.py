#!/usr/bin/env python3
"""Decode the repository's de-identified sample frames.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from ss5_protocol import decode_frame, parse_hex  # noqa: E402


def main() -> int:
    samples = Path(__file__).with_name("frames.txt")
    for line in samples.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        print(json.dumps(decode_frame(parse_hex(text)).as_dict(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

