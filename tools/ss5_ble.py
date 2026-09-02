#!/usr/bin/env python3
"""BLE scanner, GATT discovery, safe queries and explicit volume control.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from bleak import BleakClient, BleakScanner

from ss5_actions import build_volume
from ss5_protocol import (
    COMMAND_UUID,
    CONTROL_SERVICE_UUID,
    NOTIFY_UUID,
    READ_ONLY_QUERIES,
    ProtocolError,
    decode_frame,
)


def _hex_map(values: dict[Any, bytes]) -> dict[str, str]:
    return {str(key): bytes(value).hex(" ") for key, value in values.items()}


async def scan(timeout: float) -> list[dict[str, object]]:
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    rows: list[dict[str, object]] = []
    for device, adv in found.values():
        rows.append(
            {
                "address": device.address,
                "name": adv.local_name or device.name,
                "rssi": adv.rssi,
                "service_uuids": sorted(str(value).lower() for value in (adv.service_uuids or [])),
                "service_data": _hex_map(adv.service_data),
                "manufacturer_data": _hex_map(adv.manufacturer_data),
            }
        )
    return sorted(rows, key=lambda row: int(row["rssi"]), reverse=True)


async def find_exact(address: str, timeout: float):
    target = address.upper()
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    for device, adv in found.values():
        if device.address.upper() == target:
            return device, adv
    return None, None


async def discover(address: str, timeout: float) -> dict[str, object]:
    device, adv = await find_exact(address, timeout)
    if device is None:
        raise RuntimeError("address was not seen in the fresh scan; the RPA may have rotated")
    async with BleakClient(device, timeout=timeout) as client:
        services = []
        for service in client.services:
            services.append(
                {
                    "uuid": str(service.uuid).lower(),
                    "characteristics": [
                        {
                            "uuid": str(char.uuid).lower(),
                            "properties": sorted(char.properties),
                            "descriptors": [str(desc.uuid).lower() for desc in char.descriptors],
                        }
                        for char in service.characteristics
                    ],
                }
            )
        uuids = {row["uuid"] for row in services}
        return {
            "address": device.address,
            "name": adv.local_name or device.name,
            "control_service_present": CONTROL_SERVICE_UUID in uuids,
            "services": services,
        }


async def query(address: str, timeout: float, kind: str, wait: float) -> dict[str, object]:
    device, adv = await find_exact(address, timeout)
    if device is None:
        raise RuntimeError("address was not seen in the fresh scan; the RPA may have rotated")
    notifications: list[dict[str, object]] = []
    async with BleakClient(device, timeout=timeout) as client:
        service_uuids = {str(service.uuid).lower() for service in client.services}
        if CONTROL_SERVICE_UUID not in service_uuids:
            raise RuntimeError("connected device does not expose the SoundSticks control service")

        def on_notify(_sender: Any, data: bytearray) -> None:
            raw = bytes(data)
            row: dict[str, object] = {"hex": raw.hex(" ")}
            try:
                row["frame"] = decode_frame(raw).as_dict()
            except ProtocolError as exc:
                row["decode_error"] = str(exc)
            notifications.append(row)

        await client.start_notify(NOTIFY_UUID, on_notify)
        await client.write_gatt_char(COMMAND_UUID, READ_ONLY_QUERIES[kind], response=False)
        await asyncio.sleep(wait)
        await client.stop_notify(NOTIFY_UUID)
    return {
        "address": device.address,
        "name": adv.local_name or device.name,
        "query": kind,
        "request_hex": READ_ONLY_QUERIES[kind].hex(" "),
        "notifications": notifications,
    }


async def set_volume(address: str, timeout: float, value: int, wait: float) -> dict[str, object]:
    """Set hardware volume and collect the ACK/state notifications."""
    device, adv = await find_exact(address, timeout)
    if device is None:
        raise RuntimeError("address was not seen in the fresh scan; the RPA may have rotated")
    request = build_volume(value)
    notifications: list[dict[str, object]] = []
    async with BleakClient(device, timeout=timeout) as client:
        service_uuids = {str(service.uuid).lower() for service in client.services}
        if CONTROL_SERVICE_UUID not in service_uuids:
            raise RuntimeError("connected device does not expose the SoundSticks control service")

        def on_notify(_sender: Any, data: bytearray) -> None:
            raw = bytes(data)
            row: dict[str, object] = {"hex": raw.hex(" ")}
            try:
                row["frame"] = decode_frame(raw).as_dict()
            except ProtocolError as exc:
                row["decode_error"] = str(exc)
            notifications.append(row)

        await client.start_notify(NOTIFY_UUID, on_notify)
        await client.write_gatt_char(COMMAND_UUID, request, response=False)
        await asyncio.sleep(wait)
        await client.stop_notify(NOTIFY_UUID)
    return {
        "address": device.address,
        "name": adv.local_name or device.name,
        "action": "set-volume",
        "requested_percent": value,
        "request_hex": request.hex(" "),
        "notifications": notifications,
    }


async def async_main(args: argparse.Namespace) -> object:
    if args.action == "scan":
        return await scan(args.timeout)
    if args.action == "discover":
        return await discover(args.address, args.timeout)
    if args.action == "set-volume":
        return await set_volume(args.address, args.timeout, args.value, args.wait)
    return await query(args.address, args.timeout, args.kind, args.wait)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    scan_parser = sub.add_parser("scan", help="dump every advertisement without name filtering")
    scan_parser.add_argument("--timeout", type=float, default=15.0)

    discover_parser = sub.add_parser("discover", help="fresh-scan an address and enumerate GATT")
    discover_parser.add_argument("--address", required=True)
    discover_parser.add_argument("--timeout", type=float, default=20.0)

    query_parser = sub.add_parser("query", help="send one allow-listed read-only query")
    query_parser.add_argument("--address", required=True)
    query_parser.add_argument("--kind", choices=sorted(READ_ONLY_QUERIES), default="aggregate")
    query_parser.add_argument("--timeout", type=float, default=20.0)
    query_parser.add_argument("--wait", type=float, default=2.0)

    volume_parser = sub.add_parser("set-volume", help="set private-BLE hardware volume (can be loud)")
    volume_parser.add_argument("--address", required=True)
    volume_parser.add_argument("--value", required=True, type=int, help="direct percent, 0..100")
    volume_parser.add_argument("--timeout", type=float, default=20.0)
    volume_parser.add_argument("--wait", type=float, default=2.0)
    volume_parser.add_argument(
        "--confirm",
        action="store_true",
        help="required acknowledgement that changing hardware volume can be loud",
    )

    args = parser.parse_args()
    if args.action == "set-volume" and not args.confirm:
        parser.error("set-volume requires --confirm because it changes hardware volume")
    try:
        result = asyncio.run(async_main(args))
    except Exception as exc:  # platform BLE errors are intentionally reported as data
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
