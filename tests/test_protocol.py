"""SPDX-License-Identifier: Apache-2.0"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from ss5_protocol import (
    READ_ONLY_QUERIES,
    ProtocolError,
    TLV,
    decode_frame,
    encode_frame,
    encode_tlvs,
    parse_hex,
)
from ss5_actions import (
    app_eq_percent_to_gain_db,
    app_eq_step_to_gain_db,
    build_color_reset,
    build_eq_reset,
    build_eq_write,
    build_volume,
)


class ProtocolTests(unittest.TestCase):
    def test_query(self):
        frame = decode_frame(parse_hex("aa 41 00"))
        self.assertEqual(frame.command, 0x41)
        self.assertEqual(frame.data, b"")

    def test_product_settings_queries_are_read_only(self):
        self.assertEqual(READ_ONLY_QUERIES["feedback-tone"], parse_hex("aa f1 00"))
        self.assertEqual(READ_ONLY_QUERIES["auto-off"], parse_hex("aa b8 00"))

    def test_aggregate_tlvs(self):
        frame = decode_frame(
            parse_hex("aa 42 11 00 41 01 01 42 01 1c 43 01 00 44 00 45 00 36 01 01")
        )
        self.assertEqual(frame.status, 0)
        self.assertEqual([item.tag for item in frame.tlvs()], [0x41, 0x42, 0x43, 0x44, 0x45, 0x36])
        self.assertEqual(frame.tlvs()[3].value, b"")

    def test_duplicate_tags_are_preserved(self):
        frame = decode_frame(parse_hex("aa 32 09 00 4c 02 10 36 4c 02 11 32"))
        self.assertEqual([item.value for item in frame.tlvs()], [b"\x10\x36", b"\x11\x32"])

    def test_truncation_and_trailing_are_rejected(self):
        with self.assertRaises(ProtocolError):
            decode_frame(parse_hex("aa 42 04 00"))
        with self.assertRaises(ProtocolError):
            decode_frame(parse_hex("aa 41 00 ff"))

    def test_encoding(self):
        data = b"\x00" + encode_tlvs([TLV(0x99, b"\x01")])
        self.assertEqual(encode_frame(0x33, data), parse_hex("aa 33 04 00 99 01 01"))

    def test_eq_special_separator_and_length(self):
        raw = build_eq_write([0.5, 0, 0, 0, 0, 0, 0])
        self.assertEqual(raw[:4], parse_hex("aa e3 61 00"))
        self.assertEqual(len(raw), 101)
        frame = decode_frame(raw)
        self.assertEqual(frame.separator, 0)
        self.assertEqual(len(frame.data), 97)
        self.assertEqual(frame.data[:6], parse_hex("c2 07 80 bb 00 00"))
        self.assertEqual(
            [frame.data[6 + 13 * index] for index in range(7)],
            [0, 1, 1, 1, 1, 1, 2],
        )
        self.assertEqual(frame.raw, raw)

        response_raw = b"\xaa\xe2\x62\x00\xc2" + frame.data
        response = decode_frame(response_raw)
        self.assertEqual(response.separator, 0)
        self.assertEqual(len(response.data), 98)
        self.assertEqual(response.data[0], 0xC2)
        self.assertEqual(response.data[1:], frame.data)

    def test_eq_reset_is_all_zero_snapshot(self):
        raw = build_eq_reset()
        frame = decode_frame(raw)
        self.assertEqual(frame.data[:7], parse_hex("c2 07 80 bb 00 00 00"))
        self.assertEqual(frame.data[7:11], b"\x00\x00\x00\x00")
        self.assertEqual(frame.data[-12:-8], b"\x00\x00\x00\x00")

    def test_color_reset_is_not_factory_reset(self):
        self.assertEqual(build_color_reset("ocean"), parse_hex("aa 33 04 00 50 01 10"))

    def test_private_ble_absolute_volume(self):
        self.assertEqual(build_volume(0), parse_hex("aa 43 04 00 42 01 00"))
        self.assertEqual(build_volume(3), parse_hex("aa 43 04 00 42 01 03"))
        self.assertEqual(build_volume(100), parse_hex("aa 43 04 00 42 01 64"))
        with self.assertRaises(ProtocolError):
            build_volume(101)

    def test_app_eq_slider_mapping(self):
        self.assertEqual(app_eq_step_to_gain_db(1, -12), -6.0)
        self.assertEqual(app_eq_step_to_gain_db(1, 7), 3.5)
        self.assertEqual(app_eq_step_to_gain_db(0, -12), -9.0)
        self.assertEqual(app_eq_step_to_gain_db(0, 12), 6.0)
        self.assertEqual(app_eq_percent_to_gain_db(2, 0), -6.0)
        self.assertEqual(app_eq_percent_to_gain_db(2, 50), 0.0)
        self.assertEqual(app_eq_percent_to_gain_db(2, 100), 6.0)


if __name__ == "__main__":
    unittest.main()
