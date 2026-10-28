"""Regression tests use temporary data, fake hardware and no live services/network."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from test_daemon import g15 as daemon, g15_core as core, BIN_DIR


class Regressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config.json'
        for mod in (core, daemon):
            for key, val in [('CONFIG_DIR', str(self.root)), ('CONFIG_PATH', str(self.config))]:
                patch = mock.patch.object(mod, key, val)
                patch.start()
                self.addCleanup(patch.stop)
        patch = mock.patch.object(core, 'VERSION_FILE', str(self.root / 'version.json'))
        patch.start()
        self.addCleanup(patch.stop)

    def test_nonfinite_json_all_numeric_fields(self):
        for number in ('1e999', '-1e999', 'NaN', 'Infinity', '"Infinity"', 'null', '[]', '{}'):
            self.config.write_text('{"speed":'+number+',"manual_brightness":'+number+
                ',"force_seq":'+number+',"save_boot_seq":'+number+
                ',"save_boot_status":{"seq":'+number+',"ok":true}}')
            for mod in (core, daemon):
                cfg = mod.load_config(str(self.config))
                self.assertTrue(10 <= cfg['speed'] <= 100)
                self.assertTrue(0 <= cfg['manual_brightness'] <= 100)
                self.assertGreaterEqual(cfg['save_boot_status']['seq'], 0)

    def update(self, replace):
        old = self.root / 'old'
        old.write_bytes(b'old')
        old.chmod(0o600)
        new = self.root / 'new'
        last = self.root / 'last'
        files = [('assets/a', str(old), 0o644), ('assets/b', str(new), 0o644),
                 ('assets/c', str(last), 0o644)]
        with self.assertRaises(core.UpdateError) as exc:
            core.stage_and_apply_update('a'*40, files, fetcher=lambda _: b'new', replace_fn=replace)
        return old, new, last, exc.exception

    def test_mid_swap_rollback_restores_permissions_and_removes_new_files(self):
        count = 0
        def replace(src, dst):
            nonlocal count
            count += 1
            if count == 3:
                raise OSError('injected swap failure')
            os.replace(src, dst)
        old, new, last, error = self.update(replace)
        self.assertEqual(error.stage, 'apply')
        self.assertEqual(old.read_bytes(), b'old')
        self.assertEqual(old.stat().st_mode & 0o777, 0o600)
        self.assertFalse(new.exists())
        self.assertFalse(last.exists())
        self.assertFalse(list(self.root.glob('*.staged.*')))
        self.assertFalse((self.root / 'version.json').exists())

    def test_rollback_failure_is_reported(self):
        real = os.replace
        def replace(src, dst):
            if str(src).endswith('.2'):
                raise OSError('swap failure')
            real(src, dst)
        def fail_restore(src, dst):
            if '.rollback.' in str(src):
                raise OSError('restore failure')
            real(src, dst)
        with mock.patch.object(core.os, 'replace', side_effect=fail_restore):
            _, _, _, error = self.update(replace)
        self.assertEqual(error.stage, 'rollback')
        self.assertTrue(error.rollback_errors)

    def test_staging_failure_cleans_first_partial_file(self):
        target = self.root / 'target'
        with mock.patch.object(core.os, 'chmod', side_effect=OSError('chmod failed')):
            with self.assertRaises(core.UpdateError):
                core.stage_and_apply_update('b'*40, [('assets/a', str(target), 0o644)], fetcher=lambda _: b'data')
        self.assertFalse(list(self.root.glob('*.staged.*')))
        self.assertFalse(target.exists())

    def test_update_never_calls_git_or_services(self):
        with mock.patch.object(core.subprocess, 'call', side_effect=AssertionError('external command')):
            core.stage_and_apply_update('c'*40, [('assets/a', str(self.root/'a'), 0o644)],
                                        fetcher=lambda _: b'data', repo_dir=str(self.root))
        self.assertEqual(json.loads((self.root/'version.json').read_text())['commit'], 'c'*40)

    def test_boot_write_preserves_changes_and_does_not_repeat_for_brightness_edit(self):
        cfg = core.normalize_config({})
        seq = core.request_boot_save(cfg)
        calls = []
        def hw(path, level, zones, config=None, save_boot=False):
            calls.append(save_boot)
            if save_boot:
                latest = core.load_config()
                latest['manual_brightness'] = 35
                latest['force_seq'] += 1
                core.save_config(latest)
            return True, (0,1,2,3)
        state = {'backlight_dir':None, 'hidraw_path':'fake', 'ifd':-1}
        try:
            with mock.patch.object(daemon, 'resolve_backlight_dir', return_value=None):
                daemon.process_daemon_sync_step(state, config_dir=str(self.root), apply_hw_fn=hw)
            result = core.load_config()
            self.assertEqual(result['manual_brightness'], 35)
            self.assertFalse(result['save_boot'])
            self.assertEqual(core.evaluate_boot_save_feedback(result, seq)[0], 'success')
            self.assertEqual(core.evaluate_boot_save_feedback(result, seq+1)[0], 'pending')
            self.assertEqual(calls.count(True), 1)
        finally:
            if state['ifd'] >= 0: os.close(state['ifd'])

    def test_same_path_backlight_recreation_rebuilds_real_watches(self):
        blroot = self.root / 'backlight'
        bl = blroot / 'amdgpu_bl2'
        def create():
            bl.mkdir(parents=True)
            for n, v in [('brightness','50'),('max_brightness','100'),('bl_power','0')]:
                (bl/n).write_text(v)
        create()
        fd, meta = daemon.open_inotify_watches(str(bl), str(self.root), return_meta=True)
        state = {'backlight_dir':str(bl), 'hidraw_path':'fake', 'ifd':fd, 'inotify_meta':meta}
        try:
            shutil.rmtree(bl)
            create()
            raw = os.read(fd, 65536)
            _, invalidated = daemon.parse_inotify_events(raw)
            self.assertTrue(invalidated)
            daemon.process_daemon_sync_step(state, pending_bl_rebind=invalidated,
                backlight_root=str(blroot), config_dir=str(self.root),
                apply_hw_fn=lambda *a, **k: (True,(0,1,2,3)))
            self.assertTrue(state['inotify_meta']['backlight_ok'])
            (bl/'brightness').write_text('75')
            self.assertTrue(os.read(state['ifd'], 65536))
        finally:
            os.close(state['ifd'])

    def test_newer_boot_request_survives_previous_operation(self):
        cfg = core.normalize_config({})
        first = core.request_boot_save(cfg)
        seqs = []
        def hw(path, level, zones, config=None, save_boot=False):
            if save_boot:
                latest = core.load_config()
                seqs.append(core.request_boot_save(latest))
            return False, zones
        state = {'backlight_dir':None, 'hidraw_path':'missing', 'ifd':-1}
        try:
            with mock.patch.object(daemon, 'resolve_backlight_dir', return_value=None):
                daemon.process_daemon_sync_step(state, config_dir=str(self.root), apply_hw_fn=hw)
            latest = core.load_config()
            self.assertTrue(latest['save_boot'])
            self.assertEqual(latest['save_boot_seq'], seqs[0])
            self.assertEqual(core.evaluate_boot_save_feedback(latest, first)[0], 'failed')
            self.assertEqual(core.evaluate_boot_save_feedback(latest, seqs[0])[0], 'pending')
        finally:
            if state['ifd'] >= 0: os.close(state['ifd'])

    def test_gui_timeout_covers_maximum_boot_sequence(self):
        cfg = daemon.normalize_config({'mode':'spectrum'})
        packets = daemon.build_zone_packets(100, tuple(range(25)), config=cfg, save_boot=True)
        self.assertGreater(core.BOOT_SAVE_TIMEOUT_SEC, (len(packets)+2)*daemon.PACKET_DELAY_SEC)

    def test_version_failure_reports_files_already_applied(self):
        target = self.root/'asset'
        with mock.patch.object(core, 'write_local_version', side_effect=OSError('read-only version')):
            with self.assertRaises(core.UpdateError) as error:
                core.stage_and_apply_update('d'*40, [('assets/a',str(target),0o644)], fetcher=lambda _:b'new')
        self.assertEqual(error.exception.stage, 'version_record')
        self.assertEqual(target.read_bytes(), b'new')

    def test_probe_timeout_is_structured_failure(self):
        with mock.patch.object(core.subprocess, 'run', side_effect=subprocess.TimeoutExpired('probe',5)):
            self.assertEqual(core.check_backend_dependencies('gtk')[1], 'probe_failed')

    def test_missing_sensors_are_not_zero(self):
        data = core.read_telemetry(str(self.root))
        self.assertTrue(all(v is None for v in data.values()))
        self.assertIn('N/A', core.format_detailed_telemetry_label(data))

    def test_immutable_message_never_recommends_installing_components(self):
        for backend in ('gtk','qt'):
            message = core.format_missing_backend_instructions(backend, immutable=True)
            for forbidden in ('sudo ', 'rpm-ostree install', 'pip install', 'toolbox', 'dnf install'):
                self.assertNotIn(forbidden, message)
            self.assertIn('--daemon-only', message)

    def test_headless_cli_does_not_import_any_toolkit(self):
        env = dict(os.environ, XDG_CONFIG_HOME=str(self.root), PYTHONDONTWRITEBYTECODE='1')
        script = """
import builtins, runpy, sys
original = builtins.__import__
def checked(name, *args, **kwargs):
    if name.split('.')[0] in ('gi','PyQt6','PySide6'):
        raise AssertionError('Unexpected graphical import: '+name)
    return original(name,*args,**kwargs)
builtins.__import__ = checked
sys.path.insert(0, sys.argv[1])
sys.argv = [sys.argv[1]+'/g15-tray','--headless','--cycle-backlight']
runpy.run_path(sys.argv[0],run_name='__main__')
"""
        result = subprocess.run([sys.executable, '-c', script, BIN_DIR],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root/'dell-g15/config.json').exists())

    def test_service_restart_failure_is_visible(self):
        with mock.patch.object(core.subprocess, 'run', side_effect=FileNotFoundError('systemctl')):
            ok, detail = core.restart_systemd_services()
        self.assertFalse(ok)
        self.assertIn('systemctl', detail)

    def test_missing_display_is_distinct(self):
        ok, status, _ = core.check_backend_dependencies('qt', require_display=True, env={})
        self.assertFalse(ok)
        self.assertEqual(status, 'missing_display')

    def test_daemon_only_install_in_disposable_home_with_mock_services(self):
        self.install_in_disposable_home(daemon_only=True)

    def test_full_install_in_disposable_home_with_mock_services(self):
        ok, _, _ = core.check_backend_dependencies('gtk')
        if not ok:
            self.skipTest('GTK dependencies unavailable')
        self.install_in_disposable_home(daemon_only=False)

    def test_uninstall_preserves_configuration(self):
        self.install_in_disposable_home(daemon_only=True, uninstall=True)

    def install_in_disposable_home(self, daemon_only, uninstall=False):
        home = self.root/'home'
        home.mkdir()
        fakebin = self.root/'commands'
        fakebin.mkdir()
        log = self.root/'systemctl.log'
        for command in ('systemctl','busctl','powerprofilesctl','sudo','rpm-ostree'):
            file = fakebin/command
            if command == 'systemctl':
                file.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$SERVICE_LOG"\nexit 0\n')
            else:
                file.write_text('#!/bin/sh\nexit 1\n')
            file.chmod(0o755)
        env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home/'config'),
                   XDG_DATA_HOME=str(home/'data'), PATH=str(fakebin)+os.pathsep+os.environ['PATH'],
                   SERVICE_LOG=str(log), PYTHONDONTWRITEBYTECODE='1')
        env['G15_UI_BACKEND'] = 'gtk'
        config = home/'config/dell-g15/config.json'
        config.parent.mkdir(parents=True)
        config.write_text('{"manual_brightness":35}')
        args = ['bash', str(Path(BIN_DIR).parent/'install.sh')]
        if daemon_only:
            args.append('--daemon-only')
        result = subprocess.run(args,
                                env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((home/'.local/bin/g15-daemon').exists())
        self.assertTrue((home/'config/systemd/user/dell-g15-daemon.service').exists())
        self.assertEqual(config.read_text(), '{"manual_brightness":35}')
        self.assertEqual((home/'config/systemd/user/dell-g15-tray.service').exists(), not daemon_only)
        self.assertEqual((home/'data/applications/io.github.murilogiatti.DellG15Control.desktop').exists(), not daemon_only)
        commands = log.read_text().splitlines()
        self.assertEqual('--user restart dell-g15-tray.service' in commands, not daemon_only)
        self.assertIn('--user restart dell-g15-daemon.service',commands)
        if uninstall:
            result = subprocess.run(['bash', str(Path(BIN_DIR).parent/'uninstall.sh')],
                                    env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(config.read_text(), '{"manual_brightness":35}')
            for name in ('g15-daemon','g15-tray','g15_core.py','g15_gtk.py','g15_qt.py'):
                self.assertFalse((home/'.local/bin'/name).exists())
            self.assertFalse((home/'data/dell-g15').exists())
            self.assertFalse((home/'config/systemd/user/dell-g15-daemon.service').exists())


    def test_missing_gui_prerequisites_leave_existing_installation_untouched(self):
        # Minimal repository fixture with a failing dependency probe, not a missing host package.
        repo = self.root/'repo'
        (repo/'bin').mkdir(parents=True)
        shutil.copy(Path(BIN_DIR).parent/'install.sh',repo/'install.sh')
        (repo/'bin/g15-tray').write_text("import sys; print('missing_library: simulated'); sys.exit(1)")
        home = self.root/'existing'
        binary = home/'.local/bin/g15-daemon'
        binary.parent.mkdir(parents=True)
        binary.write_text('existing version')
        commands = self.root/'commands'
        commands.mkdir()
        log = self.root/'log'
        fake = commands/'systemctl'
        fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$SERVICE_LOG"\nexit 0\n')
        fake.chmod(0o755)
        env = dict(os.environ, HOME=str(home), PATH=str(commands)+os.pathsep+os.environ['PATH'],
                   SERVICE_LOG=str(log), XDG_CONFIG_HOME=str(home/'config'), XDG_DATA_HOME=str(home/'data'))
        result = subprocess.run(['bash',str(repo/'install.sh')],env=env,capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(binary.read_text(),'existing version')
        self.assertEqual(log.read_text().splitlines(),['--user show-environment'])
        self.assertFalse((home/'data').exists())

    def test_colors_require_exactly_six_hex_digits(self):
        for module in (core, daemon):
            for color in ('-FFFFF', '+FFFFF', 'FF FF0', '0x1234'):
                cfg = module.normalize_config({'zones_rgb':[color]*4})
                self.assertEqual(cfg['zones_rgb'],['E6E6E6']*4)

    def test_installer_only_writes_user_files(self):
        text = (Path(BIN_DIR).parent/'install.sh').read_text()
        for forbidden in ('sudo ', 'rpm-ostree ', '/etc/udev', 'pip install', 'dnf install', 'apt install'):
            self.assertNotIn(forbidden, text)
        self.assertIn('--daemon-only', text)


class GtkFeedback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ok, _, _ = core.check_backend_dependencies('gtk')
        if not ok:
            raise unittest.SkipTest('GTK dependencies unavailable')
        try:
            import g15_gtk
        except (ImportError, ValueError):
            raise unittest.SkipTest('GTK unavailable')
        cls.gtk = g15_gtk

    def controller(self, status=None):
        from types import SimpleNamespace
        return SimpleNamespace(cfg={'save_boot_status':status}, _pending_boot_seq=42,
                               _boot_timeout_id=12, window=None,
                               send_osd_notification=mock.Mock())

    def test_local_build_never_starts_remote_updates(self):
        from types import SimpleNamespace
        controller = SimpleNamespace(local_commit='unknown', send_osd_notification=mock.Mock())
        with mock.patch.object(core, 'fetch_latest_github_commit', side_effect=AssertionError('network')):
            self.gtk.G15ControlApp.check_for_updates_async(controller,manual=False)
            controller.send_osd_notification.assert_not_called()
            self.gtk.G15ControlApp.check_for_updates_async(controller,manual=True)
            self.gtk.G15ControlApp.perform_self_update_async(controller)
        self.assertEqual(controller.send_osd_notification.call_count,2)
        self.assertEqual(core.local_build_update_notice('a'*40),'')

    def test_feedback_pending_and_running_never_claim_success(self):
        for status in (None, {'seq':41,'state':'done','ok':True},
                       {'seq':42,'state':'running','ok':None}):
            controller = self.controller(status)
            self.gtk.G15ControlApp._check_save_boot_feedback(controller)
            self.assertEqual(controller._pending_boot_seq,42)
            controller.send_osd_notification.assert_not_called()

    def test_feedback_completion_cancels_deadline(self):
        for ok in (True,False):
            controller = self.controller({'seq':42,'state':'done','ok':ok})
            with mock.patch.object(self.gtk.GLib,'source_remove') as remove:
                self.gtk.G15ControlApp._check_save_boot_feedback(controller)
            remove.assert_called_once_with(12)
            self.assertEqual(controller._pending_boot_seq,0)
            controller.send_osd_notification.assert_called_once()

    def test_stale_timeout_does_not_erase_new_request_timer(self):
        controller = self.controller()
        self.gtk.G15ControlApp._on_save_boot_timeout(controller,41)
        self.assertEqual(controller._boot_timeout_id,12)
        self.assertEqual(controller._pending_boot_seq,42)
        controller.send_osd_notification.assert_not_called()

    def test_matching_timeout_reports_no_confirmation(self):
        controller = self.controller()
        self.gtk.G15ControlApp._on_save_boot_timeout(controller,42)
        self.assertEqual(controller._pending_boot_seq,0)
        self.assertEqual(controller._boot_timeout_id,0)
        controller.send_osd_notification.assert_called_once()


class QtSmoke(unittest.TestCase):
    def test_qml_loads_without_controller_side_effects(self):
        if importlib.util.find_spec('PyQt6') is None:
            self.skipTest('PyQt6 unavailable; QML not validated locally')
        # A stub backend supplies all QML properties/slots, without touching host hardware or services.
        source = Path(BIN_DIR, 'g15_qt.py').read_text()
        tree = ast.parse(source)
        qml_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_build_kirigami_qml')
        qml = ast.literal_eval(next(n.value for n in qml_fn.body if isinstance(n, ast.Return)))
        script = '''
import sys
from PyQt6.QtCore import QByteArray, QUrl
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine
sys.path.insert(0, sys.argv[1])
import g15_qt, g15_core
# Patch runtime integrations before controller construction.
from unittest.mock import patch
with patch.object(g15_qt.G15QtController, '_setup_tray_icon'), patch.object(g15_qt.G15QtController, '_setup_config_watcher'), patch.object(g15_qt.G15QtController, '_setup_hotkey_monitors'), patch.object(g15_core, 'read_telemetry', return_value={}), patch.object(g15_core, 'get_power_profile', return_value=None), patch.object(g15_core, 'load_config', return_value=g15_core.normalize_config({})), patch.object(g15_core, 'read_local_version', return_value=('unknown','')):
 app = QApplication([])
 controller = g15_qt.G15QtController(app)
 engine = QQmlApplicationEngine()
 engine.rootContext().setContextProperty('backend',controller)
 engine.loadData(QByteArray(sys.stdin.buffer.read()),QUrl('qrc:/smoke.qml'))
 assert engine.rootObjects(), 'QML root failed to load'
'''
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                   XDG_CONFIG_HOME=tempfile.gettempdir(), PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, '-c', script, BIN_DIR], input=qml, text=True,
                                env=env, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == '__main__':
    unittest.main()
