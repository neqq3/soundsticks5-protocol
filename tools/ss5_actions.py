#!/usr/bin/env python3
"""Offline builders for confirmed SoundSticks 5 App actions.

This module never opens Bluetooth or writes to a device.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import struct
from collections.abc import Sequence

from ss5_protocol import ProtocolError, TLV, encode_frame, encode_tlvs

THEMES = {
    "ocean": (0x10, 54),
    "aurora": (0x11, 50),
    "blossom": (0x12, 75),
    "sunrise": (0x13, 60),
    "fireplace": (0x14, 72),
    "static": (0x15, 0),
}
THEME_NAMES_BY_ID = {value[0]: name for name, value in THEMES.items()}
SPEEDS = {"low": 1, "medium": 2, "high": 3}

EQ_FREQUENCIES_HZ = (125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0)
EQ_Q = (0.707, 2.0, 2.0, 2.0, 2.0, 2.0, 0.707)
EQ_FILTER_TYPES = (0, 1, 1, 1, 1, 1, 2)
EQ_BODY_PREFIX = bytes.fromhex("c2 07 80 bb 00 00")
APP_EQ_MIN_STEP = -12
APP_EQ_MAX_STEP = 12


def _percent(value: int) -> int:
    if not 0 <= value <= 100:
        raise ProtocolError("value must be in the inclusive range 0..100")
    return value


def resolve_theme(value: str | int) -> tuple[int, int]:
    if isinstance(value, str) and value.lower() in THEMES:
        return THEMES[value.lower()]
    try:
        theme_id = int(value, 0) if isinstance(value, str) else value
    except ValueError as exc:
        raise ProtocolError(f"unknown theme {value!r}") from exc
    name = THEME_NAMES_BY_ID.get(theme_id)
    if name is None:
        raise ProtocolError("theme must be a known name or ID in 0x10..0x15")
    return THEMES[name]


def _setting_frame(*items: TLV) -> bytes:
    return encode_frame(0x33, b"\x00" + encode_tlvs(items))


def build_light(enabled: bool) -> bytes:
    return _setting_frame(TLV(0x99, bytes((int(enabled),))))


def build_brightness(value: int) -> bytes:
    return _setting_frame(TLV(0x45, bytes((_percent(value),))))


def build_speed(value: str | int) -> bytes:
    if isinstance(value, str) and value.lower() in SPEEDS:
        level = SPEEDS[value.lower()]
    else:
        try:
            level = int(value)
        except (TypeError, ValueError) as exc:
            raise ProtocolError("speed must be low/medium/high or 1/2/3") from exc
    if level not in (1, 2, 3):
        raise ProtocolError("speed must be low/medium/high or 1/2/3")
    return _setting_frame(TLV(0x4D, bytes((level,))))


def build_volume(value: int) -> bytes:
    """Build App's private-BLE absolute-volume command (direct percent)."""
    return encode_frame(0x43, b"\x00" + encode_tlvs([TLV(0x42, bytes((_percent(value),)))]))


def build_theme(value: str | int) -> bytes:
    theme_id, default_color = resolve_theme(value)
    return build_color(theme_id, default_color)


def build_color(theme: str | int, value: int) -> bytes:
    theme_id, _ = resolve_theme(theme)
    return _setting_frame(
        TLV(0x4F, bytes((theme_id,))),
        TLV(0x4C, bytes((theme_id, _percent(value)))),
    )


def build_color_reset(theme: str | int) -> bytes:
    """Build App's per-theme color-reset action (not factory reset)."""
    theme_id, _ = resolve_theme(theme)
    return _setting_frame(TLV(0x50, bytes((theme_id,))))


def build_eq_write(gains_db: Sequence[float]) -> bytes:
    """Build a complete seven-band E3 snapshot using the observed fixed layout."""
    if len(gains_db) != 7:
        raise ProtocolError("EQ requires exactly seven gain values")
    body = bytearray(EQ_BODY_PREFIX)
    for gain, frequency, q_value, filter_type in zip(
        gains_db, EQ_FREQUENCIES_HZ, EQ_Q, EQ_FILTER_TYPES, strict=True
    ):
        body.append(filter_type)
        body.extend(struct.pack("<fff", float(gain), frequency, q_value))
    if len(body) != 97:
        raise AssertionError(f"internal EQ body length is {len(body)}, expected 97")
    return encode_frame(0xE3, bytes(body))


def build_eq_reset() -> bytes:
    """Build the all-zero EQ snapshot applied by App reset + confirmation."""
    return build_eq_write((0.0,) * 7)


def app_eq_step_to_gain_db(band_index: int, app_step: int) -> float:
    """Map HK One's displayed -12..12 EQ step to its E3 gain value."""
    if not 0 <= band_index < 7:
        raise ProtocolError("EQ band index must be in 0..6")
    if not isinstance(app_step, int) or not APP_EQ_MIN_STEP <= app_step <= APP_EQ_MAX_STEP:
        raise ProtocolError("App EQ step must be an integer in -12..12")
    gain = app_step / 2.0
    # HK One 2.5.4 applies this correction to the first band of every 7-band EQ.
    if band_index == 0 and gain < 0:
        gain *= 1.5
    return gain


def app_eq_percent_to_gain_db(band_index: int, percent: int) -> float:
    """Map a 0..100 UI slider to the nearest one of HK One's 25 EQ positions."""
    step = (_percent(percent) * 24 + 50) // 100 + APP_EQ_MIN_STEP
    return app_eq_step_to_gain_db(band_index, step)
