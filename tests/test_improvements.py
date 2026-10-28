"""Regression coverage for persistence, EEPROM admission, recovery and releases."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from test_daemon import g15 as daemon, g15_core as core, BIN_DIR
import g15_install


class Improvements(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for mod in (daemon, core):
            for attr, value in [('CONFIG_DIR', str(self.root)), ('CONFIG_PATH', str(self.root/'config.json'))]:
                patch = mock.patch.object(mod, attr, value)
                patch.start()
                self.addCleanup(patch.stop)
        patch = mock.patch.object(core,'VERSION_FILE',str(self.root/'version.json'))
        patch.start()
        self.addCleanup(patch.stop)

    def test_independent_edits_merge_and_same_field_last_writer_wins(self):
        core.save_config(core.normalize_config({}))
        a,b = core.load_config(),core.load_config()
        a['speed']=85
        core.save_config(a)
        b['manual_brightness']=35
        core.save_config(b)
        self.assertEqual(core.load_config()['speed'],85)
        self.assertEqual(core.load_config()['manual_brightness'],35)
        a['speed']=50
        core.save_config(a)
        self.assertEqual(core.load_config()['manual_brightness'],35)

    def test_all_three_original_profiles_restore_exactly(self):
        for profile in ('balanced','power-saver','performance'):
            cfg=core.normalize_config({})
            calls=[]
            for target in (True,False):
                core.apply_g_mode_transition(cfg,target,get_profile_fn=lambda:profile,
                    set_profile_fn=lambda p:calls.append(p) or True,save_fn=lambda _:None)
            self.assertEqual(calls[-1],profile)

    def boot_step(self,state,hw):
        with mock.patch.object(daemon,'resolve_backlight_dir',return_value=None):
            return daemon.process_daemon_sync_step(state,config_dir=str(self.root),apply_hw_fn=hw)

    def test_boot_never_runs_without_persisted_admission(self):
        cfg=core.load_config()
        core.request_boot_save(cfg)
        state={'backlight_dir':None,'hidraw_path':'fake','ifd':-1}
        hw=mock.Mock(return_value=(True,(0,1,2,3)))
        try:
            with mock.patch.object(daemon,'update_config_preserving_concurrent_edits',side_effect=OSError('full')):
                self.boot_step(state,hw)
                self.boot_step(state,hw)
            hw.assert_not_called()
        finally:
            if state['ifd']>=0:os.close(state['ifd'])

    def test_boot_executes_once_when_completion_persistence_fails(self):
        core.request_boot_save(core.load_config())
        state={'backlight_dir':None,'hidraw_path':'fake','ifd':-1}
        hw=mock.Mock(return_value=(True,(0,1,2,3)))
        real=daemon.update_config_preserving_concurrent_edits
        calls=0
        def persist(*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls>1:raise OSError('completion failed')
            return real(*args,**kwargs)
        try:
            with mock.patch.object(daemon,'update_config_preserving_concurrent_edits',side_effect=persist):
                self.boot_step(state,hw)
                self.boot_step(state,hw)
            self.assertEqual(sum(c.kwargs.get('save_boot',False) for c in hw.call_args_list),1)
        finally:
            if state['ifd']>=0:os.close(state['ifd'])

    def test_restart_does_not_replay_interrupted_eeprom_request(self):
        cfg=core.load_config()
        seq=core.request_boot_save(cfg)
        daemon.update_config_preserving_concurrent_edits(lambda c:c.update(save_boot_status={'seq':seq,'state':'running','ok':None}))
        state={'backlight_dir':None,'hidraw_path':'fake','ifd':-1}
        hw=mock.Mock(return_value=(True,(0,1,2,3)))
        try:
            self.boot_step(state,hw)
            self.assertFalse(any(c.kwargs.get('save_boot',False) for c in hw.call_args_list))
            self.assertFalse(core.load_config()['save_boot'])
        finally:
            if state['ifd']>=0:os.close(state['ifd'])

    def test_release_tag_resolves_to_immutable_sha(self):
        responses=[{'tag_name':'v0.2.0','name':'Stable','draft':False,'prerelease':False},{'sha':'b'*40}]
        urls=[]
        def fetch(request,**kwargs):
            urls.append(request.full_url)
            return io.StringIO(json.dumps(responses.pop(0)))
        with mock.patch.object(core.urllib.request,'urlopen',side_effect=fetch):
            self.assertEqual(core.fetch_latest_github_commit(),('b'*40,'Stable'))
        self.assertTrue(urls[0].endswith('/releases/latest'))
        self.assertTrue(urls[1].endswith('/commits/v0.2.0'))
        self.assertFalse(any('/commits/main' in u for u in urls))

    def test_persistent_rollback_restores_files_and_version(self):
        dest=self.root/'asset'
        dest.write_bytes(b'old')
        core.write_local_version('a'*40)
        manifest=[('assets/a',str(dest),0o644),('assets/b',str(self.root/'new'),0o644)]
        core.stage_and_apply_update('b'*40,files_map=manifest,fetcher=lambda _:b'new')
        self.assertEqual(dest.read_bytes(),b'new')
        self.assertEqual(core.restore_previous_update(files_map=manifest),'a'*40)
        self.assertEqual(dest.read_bytes(),b'old')
        self.assertFalse((self.root/'new').exists())

    def test_daemon_status_changes_only_when_needed(self):
        state={'hidraw_path':'fake','hardware_ok':True,'last_sig':(50,)}
        daemon.publish_daemon_status(state,str(self.root))
        self.assertIn('OK',core.daemon_status_label())
        with mock.patch.object(daemon.config_store,'write_json') as writer:
            daemon.publish_daemon_status(state,str(self.root))
            writer.assert_not_called()
        state['hardware_ok']=False
        daemon.publish_daemon_status(state,str(self.root))
        self.assertNotIn('Controller OK',core.daemon_status_label())

    def install_failure(self,where):
        home=self.root/'home'
        target=home/'.local/bin/g15-daemon'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'original')
        target.chmod(0o700)
        log=[]
        def runner(args,**kwargs):
            log.append(args)
            fail=where=='restart' and 'restart' in args
            return subprocess.CompletedProcess(args,1 if fail else 0,'','injected failure' if fail else '')
        count=0
        def replace(src,dst):
            nonlocal count
            count+=1
            if where=='copy' and count==2:raise OSError('copy failed')
            os.replace(src,dst)
        env={'HOME':str(home),'XDG_CONFIG_HOME':str(home/'config'),'XDG_DATA_HOME':str(home/'data')}
        with mock.patch.dict(os.environ,env):
            with self.assertRaises(RuntimeError):
                g15_install.install_user(Path(BIN_DIR).parent,runner=runner,replace_fn=replace)
        self.assertEqual(target.read_bytes(),b'original')
        self.assertEqual(target.stat().st_mode & 0o777,0o700)
        self.assertFalse((home/'.local/bin/g15_core.py').exists())
        self.assertFalse(list(home.rglob('.g15-install-*')))

    def test_install_mid_copy_failure_restores_previous_files(self):
        self.install_failure('copy')

    def test_install_restart_failure_restores_previous_files(self):
        self.install_failure('restart')


if __name__=='__main__':unittest.main()
