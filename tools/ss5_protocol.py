#!/usr/bin/env python3
"""SoundSticks 5 application-frame primitives.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

MAGIC = 0xAA

CONTROL_SERVICE_UUID = "65786365-6c70-6f69-6e74-2e636f6d0000"
NOTIFY_UUID = "65786365-6c70-6f69-6e74-2e636f6d0001"
COMMAND_UUID = "65786365-6c70-6f69-6e74-2e636f6d0002"

READ_ONLY_QUERIES = {
    "auto-off": bytes.fromhex("aa b8 00"),
    "feedback-tone": bytes.fromhex("aa f1 00"),
    "light": bytes.fromhex("aa 31 00"),
    "aggregate": bytes.fromhex("aa 41 00"),
    "eq": bytes.fromhex("aa e1 00"),
}

# These commands have repeatedly been observed with DATA[0] followed by TLVs.
TLV_COMMANDS = {0x32, 0x33, 0x42}

# EQ responses/writes carry an extra 00 byte after LEN. LEN counts only the
# bytes following this separator, not the separator itself.
SEPARATOR_COMMANDS = {0xE2, 0xE3}


class ProtocolError(ValueError):
    """Raised when a frame or TLV chain is malformed."""


@dataclass(frozen=True)
class TLV:
    tag: int
    value: bytes

    def as_dict(self) -> dict[str, object]:
        return {
            "tag": f"0x{self.tag:02x}",
            "length": len(self.value),
            "value_hex": self.value.hex(" "),
        }


@dataclass(frozen=True)
class Frame:
    command: int
    data: bytes
    separator: int | None = None
    trailing: bytes = b""

    @property
    def raw(self) -> bytes:
        prefix = bytes((MAGIC, self.command, len(self.data)))
        if self.separator is not None:
            prefix += bytes((self.separator,))
        return prefix + self.data

    @property
    def status(self) -> int | None:
        return self.data[0] if self.data and self.command in TLV_COMMANDS else None

    def tlvs(self) -> list[TLV]:
        if self.command not in TLV_COMMANDS or not self.data:
            return []
        return parse_tlvs(self.data[1:])

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "command": f"0x{self.command:02x}",
            "length": len(self.data),
            "data_hex": self.data.hex(" "),
        }
        if self.separator is not None:
            result["separator"] = f"0x{self.separator:02x}"
        if self.trailing:
            result["trailing_hex"] = self.trailing.hex(" ")
        if self.command == 0x00 and len(self.data) == 2:
            result["acknowledged_command"] = f"0x{self.data[0]:02x}"
            result["ack_result"] = self.data[1]
        if self.status is not None:
            result["status"] = self.status
            result["tlvs"] = [item.as_dict() for item in self.tlvs()]
        return result


def parse_hex(text: str) -> bytes:
    """Parse human-friendly hexadecimal separated by spaces, ':' or '-'."""
    cleaned = text.replace("0x", "").replace(":", " ").replace("-", " ")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ProtocolError(f"invalid hexadecimal input: {exc}") from exc


def decode_frame(raw: bytes, *, allow_trailing: bool = False) -> Frame:
    if len(raw) < 3:
        raise ProtocolError("frame is shorter than AA/CMD/LEN")
    if raw[0] != MAGIC:
        raise ProtocolError(f"bad magic 0x{raw[0]:02x}; expected 0xaa")
    length = raw[2]
    separator: int | None = None
    data_start = 3
    if raw[1] in SEPARATOR_COMMANDS:
        if len(raw) < 4:
            raise ProtocolError("EQ frame is missing its separator byte")
        separator = raw[3]
        if separator != 0:
            raise ProtocolError(f"unexpected EQ separator 0x{separator:02x}; expected 0x00")
        data_start = 4
    end = data_start + length
    if len(raw) < end:
        raise ProtocolError(
            f"truncated frame: LEN={length}, only {len(raw) - data_start} data bytes"
        )
    trailing = raw[end:]
    if trailing and not allow_trailing:
        raise ProtocolError(f"{len(trailing)} trailing byte(s) after frame")
    return Frame(
        command=raw[1], data=raw[data_start:end], separator=separator, trailing=trailing
    )


def parse_tlvs(data: bytes) -> list[TLV]:
    items: list[TLV] = []
    offset = 0
    while offset < len(data):
        if offset + 2 > len(data):
            raise ProtocolError(f"truncated TLV header at offset {offset}")
        tag, length = data[offset], data[offset + 1]
        start, end = offset + 2, offset + 2 + length
        if end > len(data):
            raise ProtocolError(
                f"truncated TLV 0x{tag:02x} at offset {offset}: "
                f"length={length}, available={len(data) - start}"
            )
        items.append(TLV(tag=tag, value=data[start:end]))
        offset = end
    return items


def encode_frame(command: int, data: bytes = b"") -> bytes:
    if not 0 <= command <= 0xFF:
        raise ProtocolError("command must fit in one byte")
    if len(data) > 0xFF:
        raise ProtocolError("DATA exceeds the one-byte LEN field")
    prefix = bytes((MAGIC, command, len(data)))
    if command in SEPARATOR_COMMANDS:
        prefix += b"\x00"
    return prefix + data


def encode_tlvs(items: Iterable[TLV]) -> bytes:
    output = bytearray()
    for item in items:
        if not 0 <= item.tag <= 0xFF or len(item.value) > 0xFF:
            raise ProtocolError("TLV tag/value does not fit one-byte fields")
        output.extend((item.tag, len(item.value)))
        output.extend(item.value)
    return bytes(output)
