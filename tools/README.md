# Tools

All scripts require Python 3.10+. Only `ss5_ble.py` needs the third-party `bleak` package; offline
parsers use the standard library.

## `ss5_ble.py`

Safe online operations:

```bash
python tools/ss5_ble.py scan --timeout 15
python tools/ss5_ble.py discover --address <address-from-the-fresh-scan>
python tools/ss5_ble.py query --address <address-from-the-fresh-scan> --kind aggregate
python tools/ss5_ble.py query --address <address-from-the-fresh-scan> --kind light
python tools/ss5_ble.py query --address <address-from-the-fresh-scan> --kind eq
```

The tool deliberately has no arbitrary-write option. It fresh-scans the requested address and passes
the returned `BLEDevice` object to Bleak, reducing stale-RPA failures. It refuses to query a connected
device unless the private control service UUID is present.

The scanner prints every advertisement. An unnamed advertisement can be relevant; inspect the current
address and then use `discover`. Do not automatically connect every nearby unnamed device.

## `frame_decode.py` and `ss5_protocol.py`

Strict `AA/CMD/LEN/DATA` and TLV parsing, including the confirmed extra separator in `E2/E3` EQ
frames. Duplicate tags are preserved. Unknown tags remain raw hex.

```bash
python tools/frame_decode.py "aa 31 00"
```

## `app_actions.py` and `ss5_actions.py`

Offline builders for confirmed App-equivalent frames. They print hexadecimal only and contain no BLE
connection or send path.

```bash
python tools/app_actions.py light on
python tools/app_actions.py brightness 50
python tools/app_actions.py speed medium
python tools/app_actions.py theme sunrise
python tools/app_actions.py color sunrise 42
python tools/app_actions.py reset-color sunrise
python tools/app_actions.py eq 0.5 0 0 0 0 0 0
python tools/app_actions.py reset-eq
```

`reset-color` resets one theme's color; it is not factory reset. `reset-eq` produces the full seven-band
all-zero snapshot used after App reset + confirmation. Arbitrary EQ gain frames can be constructed for
research, but the official App's complete min/max and step mapping remain unknown.

## `att_extract.py`

Reads btsnoop/H4 records, reassembles fragmented ACL/L2CAP packets, and extracts ATT values.

```bash
python tools/att_extract.py capture.btsnoop
python tools/att_extract.py capture.btsnoop --aa-only --json
python tools/att_extract.py capture.btsnoop --stats
```

## `gatt_discovery.py`

Correlates discovery requests with responses and reconstructs service, characteristic and descriptor
declarations. 128-bit ATT UUIDs are converted from on-wire little-endian byte order.

```bash
python tools/gatt_discovery.py capture.btsnoop
```

## Platform notes

- BlueZ/Linux has been the most repeatable validation backend in the current experiments.
- Windows/WinRT behavior varies by adapter and session. Zero services or `not found` is not sufficient
  evidence that the speaker disabled GATT.
- BLE GATT discovery is unrelated to configuring the Linux A2DP audio backend. Pairing a loudspeaker
  can still fail with “Protocol not available” if PipeWire/PulseAudio/BlueALSA lacks Bluetooth audio
  profile support.
