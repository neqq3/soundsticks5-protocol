# SoundSticks 5 Protocol Research

Unofficial reverse-engineering research and validation tools for the BLE/GATT control protocol used
by Harman Kardon SoundSticks 5.

This project is not affiliated with, authorized, sponsored, or endorsed by Harman Kardon, HARMAN
International, or their affiliates. Product names and trademarks belong to their respective owners.

## Scope

This repository contains evidence-graded protocol notes, App-control mappings, safe read-only BLE
probes, frame decoders, and offline btsnoop/HCI/ATT analysis tools. It deliberately excludes APKs,
firmware, official assets,
large raw captures, Home Assistant integrations, ESP32 product implementations, and destructive
operations such as OTA, factory reset, or unbinding.

The current evidence primarily comes from one standard, non-Wi-Fi SoundSticks 5 unit and its tested
firmware. Regional variants, other SKUs, Wi-Fi editions, and future firmware may behave differently.
Read every claim together with its evidence level in [FACTS.md](FACTS.md).

The control plane uses BLE GATT. Audio uses Bluetooth Classic A2DP/AVRCP. The speaker is therefore
not a BLE-only device.

## Quick start

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

python tools/ss5_ble.py scan --timeout 15
python tools/ss5_ble.py discover --address <CURRENT_ADDRESS>
python tools/ss5_ble.py query --address <CURRENT_ADDRESS> --kind aggregate
```

The BLE address is a rotating private address (RPA). Never hard-code a MAC/RPA or treat a cached
address as device identity. Advertising names may be absent. The control service UUID is the preferred
final identity check:

```text
65786365-6c70-6f69-6e74-2e636f6d0000
```

Offline analysis:

```bash
python tools/frame_decode.py "aa 42 11 00 41 01 01 42 01 1c 43 01 00 44 00 45 00 36 01 01"
python tools/att_extract.py capture.btsnoop --aa-only
python tools/gatt_discovery.py capture.btsnoop
```

Build App-equivalent frames offline (prints hex only; never connects or transmits):

```bash
python tools/app_actions.py brightness 50
python tools/app_actions.py color ocean 50
python tools/app_actions.py reset-color ocean
python tools/app_actions.py reset-eq
```

## Repository guide

- [FACTS.md](FACTS.md): authoritative evidence baseline
- [docs/protocol.md](docs/protocol.md): protocol layout and confirmed commands
- [docs/app-reference.md](docs/app-reference.md): app-derived properties, presets, defaults, and EQ
- [docs/audio-volume.md](docs/audio-volume.md): AVRCP volume scale and silent step experiment
- [docs/capture-and-analysis.md](docs/capture-and-analysis.md): reproducible capture workflow
- [docs/safety.md](docs/safety.md): safety boundaries
- [docs/research-questions.md](docs/research-questions.md): open questions and suggested experiments
- [results/experiment-summary.md](results/experiment-summary.md): sanitized experiment summaries
- [results/reference-values.json](results/reference-values.json): machine-readable reference values
- [tools/README.md](tools/README.md): tool reference

## Licensing

- Code and tools: Apache License 2.0, see [LICENSE-CODE](LICENSE-CODE)
- Documentation and research text: CC BY 4.0, see [LICENSE-DOCS](LICENSE-DOCS)
