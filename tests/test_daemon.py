#!/usr/bin/env python3
"""Unit tests for Dell G15 Ambient Sync Daemon & RGB Engine."""

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

BIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin"))
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)

import g15_core  # noqa: E402


def load_daemon_module():
    daemon_path = os.path.join(BIN_DIR, "g15-daemon")
    loader = importlib.machinery.SourceFileLoader("g15_daemon", daemon_path)
    spec = importlib.util.spec_from_loader("g15_daemon", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def load_tray_module():
    tray_path = os.path.join(BIN_DIR, "g15-tray")
    loader = importlib.machinery.SourceFileLoader("g15_tray", tray_path)
    spec = importlib.util.spec_from_loader("g15_tray", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


g15 = load_daemon_module()
g15_tray = load_tray_module()


class TestDellG15Daemon(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = self.tmpdir.name
        self.addCleanup(self.tmpdir.cleanup)
        for module in (g15_core, g15):
            for attr, value in (("CONFIG_DIR", self.root), ("CONFIG_PATH", os.path.join(self.root, "config.json")),
                                ("DATA_DIR", self.root), ("VERSION_FILE", os.path.join(self.root, "version.json"))):
                if hasattr(module, attr):
                    patcher = mock.patch.object(module, attr, value)
                    patcher.start()
                    self.addCleanup(patcher.stop)

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

        # Verify force_seq and g_mode are tracked in state signature so Fn+F5 / Fn+F9 always re-apply
        sig1 = g15.make_state_signature(reloaded, 75)
        reloaded["force_seq"] = reloaded.get("force_seq", 0) + 1
        sig2 = g15.make_state_signature(reloaded, 75)
        self.assertNotEqual(sig1, sig2)

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

    def test_invalid_config_values_are_sanitized_without_crashing(self):
        cfg_file = os.path.join(self.root, "bad_config.json")
        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write(
                '{"speed": null, "manual_brightness": "abc", "sync_screen": "no", '
                '"mode": "invalid_fx", "zones_rgb": ["ZZZZZZ", 123, null, "#112233"], '
                '"force_seq": "bad"}'
            )

        cfg = g15.load_config(cfg_file)
        self.assertEqual(cfg["speed"], 40)
        self.assertEqual(cfg["manual_brightness"], 100)
        self.assertTrue(cfg["sync_screen"])
        self.assertEqual(cfg["mode"], "static")
        self.assertEqual(cfg["zones_rgb"], ["E6E6E6", "E6E6E6", "E6E6E6", "112233"])
        self.assertEqual(cfg["force_seq"], 0)

        # Must also build packets and compute effective state cleanly
        eff, _auto = g15.compute_effective_state(cfg, 50, True, -1)
        pkts = g15.build_zone_packets(eff, (0, 1, 2, 3), config=cfg)
        self.assertEqual(len(pkts), 11)

        # Tray config normalizer must behave identically
        tray_cfg = g15_tray.load_config(cfg_file)
        self.assertEqual(tray_cfg["speed"], 40)
        self.assertEqual(tray_cfg["manual_brightness"], 100)

    def test_rebuild_inotify_watches_on_backlight_recreation(self):
        bl1 = self._create_mock_backlight("amdgpu_bl0", 50, 100)
        ifd1 = g15.open_inotify_watches(bl1, config_dir=self.root)
        self.assertGreaterEqual(ifd1, 0)

        bl2 = self._create_mock_backlight("amdgpu_bl2", 80, 100)
        ifd2 = g15.rebuild_inotify_watches(ifd1, bl2, config_dir=self.root)
        self.assertGreaterEqual(ifd2, 0)
        os.close(ifd2)

    def test_atomic_updater_pins_commit_and_rolls_back_on_failure(self):
        dest_a = os.path.join(self.root, "bin", "g15-daemon")
        dest_b = os.path.join(self.root, "assets", "banner.svg")
        os.makedirs(os.path.dirname(dest_a), exist_ok=True)
        os.makedirs(os.path.dirname(dest_b), exist_ok=True)
        with open(dest_a, "wb") as f:
            f.write(b"print('old_daemon')\n")
        with open(dest_b, "wb") as f:
            f.write(b"<svg>old</svg>")

        files_map = (
            ("bin/g15-daemon", dest_a, 0o755),
            ("assets/banner.svg", dest_b, 0o644),
        )
        requested_urls = []

        def fake_fetch_ok(url):
            requested_urls.append(url)
            if url.endswith("bin/g15-daemon"):
                return b"print('new_daemon')\n"
            return b"<svg>new</svg>"

        sha = "a1b2c3d4e5f60123456789abcdef0123456789ab"
        g15_tray.stage_and_apply_update(sha, files_map=files_map, fetcher=fake_fetch_ok)
        self.assertTrue(all(sha in u for u in requested_urls))
        with open(dest_a, "rb") as f:
            self.assertEqual(f.read(), b"print('new_daemon')\n")

        # Now simulate a syntax error in a downloaded Python binary: existing files must remain untouched
        def fake_fetch_corrupt(url):
            if url.endswith("bin/g15-daemon"):
                return b"def broken_syntax(:\n"
            return b"<svg>corrupt</svg>"

        with self.assertRaises(g15_core.UpdateError):
            g15_tray.stage_and_apply_update(
                "d" * 40, files_map=files_map, fetcher=fake_fetch_corrupt
            )
        with open(dest_a, "rb") as f:
            self.assertEqual(f.read(), b"print('new_daemon')\n")

    def test_gmode_restores_previous_power_profile_and_reports_failure(self):
        cfg = g15_core.normalize_config({"zones_rgb": ["00E5FF"] * 4, "mode": "breathing"})
        set_calls = []

        # Case 1: User starts in power-saver, G-Mode succeeds, then disabling restores power-saver
        changed, active_prof, _title, _body = g15_core.apply_g_mode_transition(
            cfg,
            target_state=True,
            get_profile_fn=lambda: "power-saver",
            set_profile_fn=lambda p: (set_calls.append(p) or True),
            save_fn=lambda _c: None,
        )
        self.assertTrue(changed)
        self.assertEqual(active_prof, "performance")
        self.assertEqual(set_calls[-1], "performance")
        self.assertEqual(cfg["pre_gmode"]["power_profile"], "power-saver")

        changed, active_prof, _title, _body = g15_core.apply_g_mode_transition(
            cfg,
            target_state=False,
            get_profile_fn=lambda: "performance",
            set_profile_fn=lambda p: (set_calls.append(p) or True),
            save_fn=lambda _c: None,
        )
        self.assertTrue(changed)
        self.assertEqual(active_prof, "power-saver")
        self.assertEqual(set_calls[-1], "power-saver")
        self.assertEqual(cfg["mode"], "breathing")

        # Case 2: set_power_profile fails -> notification must NOT claim High Performance succeeded
        changed, _active_prof, _title, body = g15_core.apply_g_mode_transition(
            cfg,
            target_state=True,
            get_profile_fn=lambda: "balanced",
            set_profile_fn=lambda _p: False,
            save_fn=lambda _c: None,
        )
        self.assertTrue(changed)
        self.assertTrue(
            "indisponível" in body.lower() or "unavailable" in body.lower()
        )

    def test_save_boot_waits_for_daemon_confirmation(self):
        cfg = g15_core.normalize_config({})
        expected_seq = g15_core.request_boot_save(cfg, save_fn=lambda _c: None)
        self.assertGreater(expected_seq, 0)
        self.assertTrue(cfg["save_boot"])

        self.assertEqual(g15_core.evaluate_boot_save_feedback(cfg, expected_seq)[0], "pending")
        for state, ok, expected in (("running", None, "running"), ("done", False, "failed"), ("done", True, "success")):
            cfg["save_boot_status"] = {"seq": expected_seq, "state": state, "ok": ok}
            self.assertEqual(g15_core.evaluate_boot_save_feedback(cfg, expected_seq)[0], expected)
        self.assertEqual(g15_core.evaluate_boot_save_feedback(cfg, expected_seq + 1)[0], "pending")

    def test_desktop_backend_detection_and_composite_xdg_strings(self):
        self.assertEqual(
            g15_core.detect_desktop_backend({"XDG_CURRENT_DESKTOP": "ubuntu:GNOME"}),
            "gtk",
        )
        self.assertEqual(
            g15_core.detect_desktop_backend({"XDG_CURRENT_DESKTOP": "GNOME-Classic:GNOME"}),
            "gtk",
        )
        self.assertEqual(
            g15_core.detect_desktop_backend({"XDG_CURRENT_DESKTOP": "KDE"}),
            "qt",
        )
        self.assertEqual(
            g15_core.detect_desktop_backend({"XDG_CURRENT_DESKTOP": "ubuntu:KDE"}),
            "qt",
        )
        self.assertEqual(
            g15_core.detect_desktop_backend({"DESKTOP_SESSION": "plasma"}),
            "qt",
        )
        self.assertEqual(
            g15_core.detect_desktop_backend(
                {"XDG_CURRENT_DESKTOP": "ubuntu:GNOME", "G15_UI_BACKEND": "qt"}
            ),
            "qt",
        )

        # CLI --backend override
        backend, rest = g15_core.parse_backend_override(
            ["g15-tray", "--backend", "qt", "--show"],
            env={"XDG_CURRENT_DESKTOP": "GNOME"},
        )
        self.assertEqual(backend, "qt")
        self.assertEqual(rest, ["g15-tray", "--show"])

        backend2, rest2 = g15_core.parse_backend_override(
            ["g15-tray", "--backend=gtk", "--toggle-gmode"],
            env={"XDG_CURRENT_DESKTOP": "KDE"},
        )
        self.assertEqual(backend2, "gtk")
        self.assertEqual(rest2, ["g15-tray", "--toggle-gmode"])

        with self.assertRaises(ValueError):
            g15_core.parse_backend_override(["g15-tray", "--backend", "wxwidgets"])

    def test_toolkit_isolation_and_no_silent_fallback(self):
        # 1. Verify g15_core never imports gi, PyQt6, or PySide6
        code = (
            "import sys; sys.path.insert(0, %r); import g15_core; "
            "forbidden = [m for m in ('gi', 'PyQt6', 'PySide6') if m in sys.modules]; "
            "assert not forbidden, f'Forbidden modules imported in g15_core: {forbidden}'"
            % BIN_DIR
        )
        subprocess.check_call([sys.executable, "-c", code])

        # 2. Verify g15_gtk never imports PyQt6 or PySide6 when loaded
        code_gtk = (
            "import sys; sys.path.insert(0, %r); import g15_gtk; "
            "assert 'gi' in sys.modules; "
            "forbidden = [m for m in ('PyQt6', 'PySide6') if m in sys.modules]; "
            "assert not forbidden, f'Qt imported inside GTK backend: {forbidden}'"
            % BIN_DIR
        )
        probe = subprocess.run([sys.executable, "-c", "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')"], capture_output=True)
        if probe.returncode == 0:
            subprocess.check_call([sys.executable, "-c", code_gtk])

        # 3. Verify that if a requested backend's toolkit is missing, load_ui_backend raises RuntimeError
        # with distribution-specific install instructions and NEVER imports the other toolkit
        code_missing_qt = "\n".join(
            [
                "import builtins, sys, importlib.machinery, importlib.util",
                f"sys.path.insert(0, {BIN_DIR!r})",
                "real_import = builtins.__import__",
                "def fake_import(name, *a, **kw):",
                "    if name.startswith('PyQt6'):",
                "        raise ImportError('No PyQt6')",
                "    return real_import(name, *a, **kw)",
                "builtins.__import__ = fake_import",
                f"loader = importlib.machinery.SourceFileLoader('g15_tray_iso', {os.path.join(BIN_DIR, 'g15-tray')!r})",
                "spec = importlib.util.spec_from_loader('g15_tray_iso', loader)",
                "mod = importlib.util.module_from_spec(spec)",
                "loader.exec_module(mod)",
                "try:",
                "    mod.load_ui_backend('qt')",
                "    raise AssertionError('Expected RuntimeError')",
                "except RuntimeError as e:",
                "    msg = str(e)",
                "    assert 'PyQt6' in msg and 'Kirigami' in msg, msg",
                "    assert 'gi' not in sys.modules, 'GTK/gi was imported during Qt backend failure!'",
            ]
        )
        subprocess.check_call([sys.executable, "-c", code_missing_qt])

    def test_backlight_cycle_and_brightness_step_shared_logic(self):
        cfg = g15_core.normalize_config({"sync_screen": True, "manual_brightness": 100})
        g15_core.apply_backlight_cycle(cfg, save_fn=lambda _c: None)
        self.assertFalse(cfg["sync_screen"])
        self.assertEqual(cfg["manual_brightness"], 100)

        g15_core.apply_backlight_cycle(cfg, save_fn=lambda _c: None)
        self.assertFalse(cfg["sync_screen"])
        self.assertEqual(cfg["manual_brightness"], 50)

        g15_core.apply_backlight_cycle(cfg, save_fn=lambda _c: None)
        self.assertFalse(cfg["sync_screen"])
        self.assertEqual(cfg["manual_brightness"], 0)

        g15_core.apply_backlight_cycle(cfg, save_fn=lambda _c: None)
        self.assertTrue(cfg["sync_screen"])
        self.assertEqual(cfg["manual_brightness"], 100)

        val, _t, _b = g15_core.apply_brightness_step(cfg, -1, save_fn=lambda _c: None)
        self.assertFalse(cfg["sync_screen"])
        self.assertEqual(val, 75)


if __name__ == "__main__":
    unittest.main()
