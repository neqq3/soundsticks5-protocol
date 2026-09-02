#!/usr/bin/env python3
"""Minimal btsnoop/H4 reader with ACL/L2CAP reassembly.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

MAGIC = b"btsnoop\x00"
ATT_CID = 0x0004
HCI_ACL = 0x02

ATT_NAMES = {
    0x01: "Error Response",
    0x02: "Exchange MTU Request",
    0x03: "Exchange MTU Response",
    0x04: "Find Information Request",
    0x05: "Find Information Response",
    0x08: "Read By Type Request",
    0x09: "Read By Type Response",
    0x0A: "Read Request",
    0x0B: "Read Response",
    0x10: "Read By Group Type Request",
    0x11: "Read By Group Type Response",
    0x12: "Write Request",
    0x13: "Write Response",
    0x16: "Prepare Write Request",
    0x17: "Prepare Write Response",
    0x18: "Execute Write Request",
    0x19: "Execute Write Response",
    0x1B: "Handle Value Notification",
    0x1D: "Handle Value Indication",
    0x1E: "Handle Value Confirmation",
    0x23: "Multiple Handle Value Notification",
    0x52: "Write Command",
    0xD2: "Signed Write Command",
}


class SnoopError(ValueError):
    pass


@dataclass(frozen=True)
class Record:
    index: int
    offset: int
    direction: str
    timestamp: int
    packet: bytes


@dataclass(frozen=True)
class AttRecord:
    index: int
    direction: str
    connection_handle: int
    timestamp: int
    opcode: int
    body: bytes

    @property
    def name(self) -> str:
        return ATT_NAMES.get(self.opcode, f"Unknown 0x{self.opcode:02x}")


def read_header(data: bytes) -> tuple[int, int]:
    if len(data) < 16 or data[:8] != MAGIC:
        raise SnoopError("not a btsnoop file")
    return struct.unpack(">II", data[8:16])


def _normalise_h4(payload: bytes) -> bytes:
    """Accept normal H4 and the common four-byte pseudo-header variant."""
    if payload and payload[0] in range(1, 6):
        return payload
    if len(payload) >= 5 and payload[4] in range(1, 6):
        return payload[4:]
    return payload


def iter_records(data: bytes) -> Iterator[Record]:
    read_header(data)
    offset, index = 16, 0
    while offset + 24 <= len(data):
        _original, included, flags, _drops, timestamp = struct.unpack(">IIIIQ", data[offset:offset + 24])
        end = offset + 24 + included
        if end > len(data):
            raise SnoopError(f"truncated record at file offset {offset}")
        direction = "rx" if flags & 1 else "tx"
        yield Record(index, offset, direction, timestamp, _normalise_h4(data[offset + 24:end]))
        offset, index = end, index + 1


class L2capReassembler:
    def __init__(self) -> None:
        self._buffers: dict[tuple[int, str], tuple[int, int, bytearray]] = {}

    def feed(self, handle: int, pb: int, direction: str, fragment: bytes) -> list[tuple[int, bytes]]:
        key = (handle, direction)
        if pb in (0, 2):  # first fragment; boundary values used by BR/EDR and LE ACL
            if len(fragment) < 4:
                self._buffers.pop(key, None)
                return []
            length, cid = struct.unpack("<HH", fragment[:4])
            payload = bytearray(fragment[4:])
            if len(payload) >= length:
                self._buffers.pop(key, None)
                return [(cid, bytes(payload[:length]))]
            self._buffers[key] = (length, cid, payload)
            return []
        if pb == 1 and key in self._buffers:  # continuation has no L2CAP header
            length, cid, payload = self._buffers[key]
            payload.extend(fragment)
            if len(payload) >= length:
                self._buffers.pop(key, None)
                return [(cid, bytes(payload[:length]))]
        return []


def iter_att(data: bytes) -> Iterator[AttRecord]:
    reassembler = L2capReassembler()
    for record in iter_records(data):
        packet = record.packet
        if len(packet) < 5 or packet[0] != HCI_ACL:
            continue
        handle_flags, acl_length = struct.unpack("<HH", packet[1:5])
        fragment = packet[5:5 + acl_length]
        if len(fragment) != acl_length:
            continue
        handle = handle_flags & 0x0FFF
        pb = (handle_flags >> 12) & 0x03
        for cid, pdu in reassembler.feed(handle, pb, record.direction, fragment):
            if cid == ATT_CID and pdu:
                yield AttRecord(
                    record.index,
                    record.direction,
                    handle,
                    record.timestamp,
                    pdu[0],
                    pdu[1:],
                )


def load(path: str | Path) -> bytes:
    return Path(path).read_bytes()

