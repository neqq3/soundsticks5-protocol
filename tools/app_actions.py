#!/usr/bin/env python3
"""Print confirmed App-equivalent frames without connecting to Bluetooth.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse

from ss5_actions import (
    build_brightness,
    build_color,
    build_color_reset,
    build_eq_reset,
    build_eq_write,
    build_light,
    build_speed,
    build_theme,
    build_volume,
)
from ss5_protocol import ProtocolError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="action", required=True)

    light = sub.add_parser("light")
    light.add_argument("state", choices=("on", "off"))

    brightness = sub.add_parser("brightness")
    brightness.add_argument("value", type=int)

    volume = sub.add_parser("volume")
    volume.add_argument("value", type=int, help="absolute hardware volume, 0..100")

    speed = sub.add_parser("speed")
    speed.add_argument("level", choices=("low", "medium", "high", "1", "2", "3"))

    theme = sub.add_parser("theme")
    theme.add_argument("name_or_id")

    color = sub.add_parser("color")
    color.add_argument("theme")
    color.add_argument("value", type=int)

    reset_color = sub.add_parser("reset-color")
    reset_color.add_argument("theme")

    eq = sub.add_parser("eq")
    eq.add_argument("gains_db", nargs=7, type=float, metavar="DB")

    sub.add_parser("reset-eq")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.action == "light":
            frame = build_light(args.state == "on")
        elif args.action == "brightness":
            frame = build_brightness(args.value)
        elif args.action == "volume":
            frame = build_volume(args.value)
        elif args.action == "speed":
            frame = build_speed(args.level)
        elif args.action == "theme":
            frame = build_theme(args.name_or_id)
        elif args.action == "color":
            frame = build_color(args.theme, args.value)
        elif args.action == "reset-color":
            frame = build_color_reset(args.theme)
        elif args.action == "eq":
            frame = build_eq_write(args.gains_db)
        else:
            frame = build_eq_reset()
    except ProtocolError as exc:
        parser().error(str(exc))
    print(frame.hex(" "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
