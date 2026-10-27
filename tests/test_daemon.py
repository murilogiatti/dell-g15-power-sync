#!/usr/bin/env python3
"""Unit tests for Dell G15 Ambient Sync Daemon."""

import importlib.machinery
import importlib.util
import os
import tempfile
import unittest


def load_daemon_module():
    daemon_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "bin", "g15-daemon")
    )
    loader = importlib.machinery.SourceFileLoader("g15_daemon", daemon_path)
    spec = importlib.util.spec_from_loader("g15_daemon", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


g15 = load_daemon_module()


class TestDellG15Daemon(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = self.tmpdir.name

    def tearDown(self):
        self.tmpdir.cleanup()

    def _create_mock_backlight(self, name, brightness, max_brightness, bl_power=0):
        bl_dir = os.path.join(self.root, name)
        os.makedirs(bl_dir, exist_ok=True)
        with open(os.path.join(bl_dir, "brightness"), "w", encoding="utf-8") as f:
            f.write(str(brightness))
        with open(os.path.join(bl_dir, "max_brightness"), "w", encoding="utf-8") as f:
            f.write(str(max_brightness))
        with open(os.path.join(bl_dir, "bl_power"), "w", encoding="utf-8") as f:
            f.write(str(bl_power))
        return bl_dir

    def test_resolve_backlight_prefers_amdgpu_bl2_and_falls_back(self):
        self._create_mock_backlight("amdgpu_bl0", 50, 100)
        self.assertTrue(g15.resolve_backlight_dir(self.root).endswith("amdgpu_bl0"))

        self._create_mock_backlight("amdgpu_bl2", 80, 100)
        self.assertTrue(g15.resolve_backlight_dir(self.root).endswith("amdgpu_bl2"))

    def test_read_screen_state_and_bl_power(self):
        bl_dir = self._create_mock_backlight("amdgpu_bl2", 128, 255, bl_power=0)
        perc, screen_on = g15.read_screen_state(bl_dir)
        self.assertEqual(perc, 50)
        self.assertTrue(screen_on)

        # When DPMS / bl_power is non-zero (screen blanked), screen_on must be False
        bl_dir = self._create_mock_backlight("amdgpu_bl2", 128, 255, bl_power=4)
        perc, screen_on = g15.read_screen_state(bl_dir)
        self.assertFalse(screen_on)

        # When brightness is 0, screen_on must be False
        bl_dir = self._create_mock_backlight("amdgpu_bl2", 0, 255, bl_power=0)
        perc, screen_on = g15.read_screen_state(bl_dir)
        self.assertEqual(perc, 0)
        self.assertFalse(screen_on)

    def test_compute_target_zone_initial_mapping(self):
        self.assertEqual(g15.compute_target_zone(0, True, -1), 0)
        self.assertEqual(g15.compute_target_zone(50, False, 50), 0)
        self.assertEqual(g15.compute_target_zone(1, True, -1), 10)
        self.assertEqual(g15.compute_target_zone(20, True, -1), 10)
        self.assertEqual(g15.compute_target_zone(21, True, -1), 30)
        self.assertEqual(g15.compute_target_zone(40, True, -1), 30)
        self.assertEqual(g15.compute_target_zone(41, True, -1), 50)
        self.assertEqual(g15.compute_target_zone(60, True, -1), 50)
        self.assertEqual(g15.compute_target_zone(61, True, -1), 75)
        self.assertEqual(g15.compute_target_zone(80, True, -1), 75)
        self.assertEqual(g15.compute_target_zone(81, True, -1), 100)
        self.assertEqual(g15.compute_target_zone(100, True, -1), 100)

    def test_hysteresis_prevents_boundary_flicker(self):
        # Starting at zone 30 (21-40%), threshold is 40 with ±2% hysteresis (deadband 39..42)
        self.assertEqual(g15.compute_target_zone(41, True, 30), 30)
        self.assertEqual(g15.compute_target_zone(42, True, 30), 30)
        self.assertEqual(g15.compute_target_zone(43, True, 30), 50)

        # Now in zone 50, dropping to 40 or 39 stays in 50; dropping to 38 returns to 30
        self.assertEqual(g15.compute_target_zone(40, True, 50), 50)
        self.assertEqual(g15.compute_target_zone(39, True, 50), 50)
        self.assertEqual(g15.compute_target_zone(38, True, 50), 30)

    def test_build_zone_packets_protocol_bytes(self):
        # Screen off (zone 0) -> single 34-byte DIM=100 packet (0x26)
        off_pkts = g15.build_zone_packets(0, g15.ZONES_STANDARD)
        self.assertEqual(len(off_pkts), 1)
        self.assertEqual(len(off_pkts[0]), 34)
        self.assertEqual(
            list(off_pkts[0][:10]),
            [0x00, 0x03, 0x26, 100, 0x00, 0x04, 0x00, 0x01, 0x02, 0x03],
        )

        # Zone 100 -> 5 packets with RGB = 0xE6 (230) and DIM = 0
        max_pkts = g15.build_zone_packets(100, g15.ZONES_STANDARD)
        self.assertEqual(len(max_pkts), 5)
        self.assertEqual(
            list(max_pkts[2][:11]),
            [0x00, 0x03, 0x24, 0x00, 0x07, 0xD0, 0x00, 0xFA, 0xE6, 0xE6, 0xE6],
        )
        self.assertEqual(
            list(max_pkts[4][:10]),
            [0x00, 0x03, 0x26, 0x00, 0x00, 0x04, 0x00, 0x01, 0x02, 0x03],
        )

    def test_parse_relevant_uevent(self):
        self.assertEqual(
            g15.parse_relevant_uevent(b"ACTION=change\0SUBSYSTEM=backlight\0"),
            "backlight",
        )
        self.assertEqual(
            g15.parse_relevant_uevent(b"ACTION=add\0SUBSYSTEM=hidraw\0"),
            "hidraw",
        )
        self.assertIsNone(
            g15.parse_relevant_uevent(b"ACTION=change\0SUBSYSTEM=power_supply\0")
        )


if __name__ == "__main__":
    unittest.main()
