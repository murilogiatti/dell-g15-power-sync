#!/usr/bin/env python3
"""Unit tests for Dell G15 Ambient Sync Daemon & RGB Engine."""

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

        # When brightness is 0 but bl_power is 0 (minimum slider step), screen_on stays True (10% floor)
        bl_dir = self._create_mock_backlight("amdgpu_bl2", 0, 255, bl_power=0)
        perc, screen_on = g15.read_screen_state(bl_dir)
        self.assertEqual(perc, 0)
        self.assertTrue(screen_on)

    def test_compute_target_zone_initial_mapping(self):
        self.assertEqual(g15.compute_target_zone(50, False, 50), 0)
        self.assertEqual(g15.compute_target_zone(0, True, -1), 10)
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
        zones_4 = (0x00, 0x01, 0x02, 0x03)
        # Screen off (zone 0) -> single 34-byte DIM=100 packet (0x26)
        off_pkts = g15.build_zone_packets(0, zones_4)
        self.assertEqual(len(off_pkts), 1)
        self.assertEqual(len(off_pkts[0]), 34)
        self.assertEqual(
            list(off_pkts[0][:10]),
            [0x00, 0x03, 0x26, 100, 0x00, 0x04, 0x00, 0x01, 0x02, 0x03],
        )

        # Zone 100 -> DIM(0) first, NEW, 4x(SEL+ACT), and FINISH_PLAY as the final packet!
        max_pkts = g15.build_zone_packets(100, zones_4)
        self.assertEqual(len(max_pkts), 11)
        # First packet must be DIM(0)
        self.assertEqual(
            list(max_pkts[0][:10]),
            [0x00, 0x03, 0x26, 0x00, 0x00, 0x04, 0x00, 0x01, 0x02, 0x03],
        )
        # First zone ADD_ACTION must have RGB = 0xE6 (230)
        self.assertEqual(
            list(max_pkts[3][:11]),
            [0x00, 0x03, 0x24, 0x00, 0x07, 0xD0, 0x00, 0xFA, 0xE6, 0xE6, 0xE6],
        )
        # Final packet MUST be USER_ANIM_FINISH_PLAY (0x21 0x00 0x03 0xFF 0xFF)
        self.assertEqual(
            list(max_pkts[-1][:9]),
            [0x00, 0x03, 0x21, 0x00, 0x03, 0xFF, 0xFF, 0x00, 0x00],
        )

    def test_per_zone_rgb_and_modes_and_boot_save(self):
        zones_4 = (0x00, 0x01, 0x02, 0x03)
        cfg = dict(g15.DEFAULT_CONFIG)
        cfg["per_zone"] = True
        cfg["power_cap"] = False
        cfg["zones_rgb"] = ["FF0000", "00FF00", "0000FF", "FFFF00"]

        pkts = g15.build_zone_packets(50, zones_4, config=cfg)
        # Zone 0 scaled at 50% -> R=127 (0x7F), G=0, B=0
        self.assertEqual(list(pkts[3][8:11]), [127, 0, 0])
        # Zone 1 scaled at 50% -> R=0, G=127 (0x7F), B=0
        self.assertEqual(list(pkts[5][8:11]), [0, 127, 0])

        # Morph mode packs two 0x02 actions per zone into a single 0x24 packet
        cfg["mode"] = "morph"
        cfg["zones_rgb2"] = ["00E5FF"] * 4
        morph_pkts = g15.build_zone_packets(100, zones_4, config=cfg)
        self.assertEqual(len(morph_pkts), 11)
        self.assertEqual(morph_pkts[3][3], 0x02)
        self.assertEqual(morph_pkts[3][11], 0x02)

        # Save boot EEPROM uses slot 0x0061 and ends with SAVE (0x02), SET_DEFAULT (0x06), PLAY (0x07)
        boot_pkts = g15.build_zone_packets(100, zones_4, config=cfg, save_boot=True)
        self.assertEqual(list(boot_pkts[1][:7]), [0x00, 0x03, 0x21, 0x00, 0x04, 0x00, 0x61])
        self.assertEqual(list(boot_pkts[-3][:7]), [0x00, 0x03, 0x21, 0x00, 0x02, 0x00, 0x61])
        self.assertEqual(list(boot_pkts[-2][:7]), [0x00, 0x03, 0x21, 0x00, 0x06, 0x00, 0x61])
        self.assertEqual(list(boot_pkts[-1][:7]), [0x00, 0x03, 0x21, 0x00, 0x07, 0x00, 0x61])

        # Animation speed mapping: 10% (slowest) must have much larger duration/tempo than 100% (fastest)
        slow_dur, slow_tempo = g15.compute_anim_timing("breathing", 10)
        fast_dur, fast_tempo = g15.compute_anim_timing("breathing", 100)
        self.assertGreater(slow_dur, fast_dur)
        self.assertGreater(slow_tempo, fast_tempo)
        self.assertEqual((slow_dur, slow_tempo), (4500, 450))
        self.assertEqual((fast_dur, fast_tempo), (500, 50))

        spec_slow_dur, spec_slow_tempo = g15.compute_anim_timing("rainbow", 10)
        spec_fast_dur, spec_fast_tempo = g15.compute_anim_timing("rainbow", 100)
        self.assertGreater(spec_slow_dur, spec_fast_dur)
        self.assertGreater(spec_slow_tempo, spec_fast_tempo)

    def test_config_load_and_save_atomic(self):
        cfg_file = os.path.join(self.root, "config.json")
        cfg = g15.load_config(cfg_file)
        self.assertTrue(cfg["sync_screen"])
        cfg["sync_screen"] = False
        cfg["manual_brightness"] = 75
        cfg["zones_rgb"] = ["#00e5ff", "ff2200", "00e676", "b388ff"]
        g15.save_config(cfg, cfg_file)

        reloaded = g15.load_config(cfg_file)
        self.assertFalse(reloaded["sync_screen"])
        self.assertEqual(reloaded["manual_brightness"], 75)
        self.assertEqual(reloaded["zones_rgb"][0], "00E5FF")

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
