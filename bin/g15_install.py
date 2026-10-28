#!/usr/bin/env python3
"""Recoverable user-only installer. No package managers or privileged operations."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def install_user(root, daemon_only=False, runner=subprocess.run, replace_fn=os.replace):
    root = Path(root)
    home = Path.home()
    config = Path(os.environ.get('XDG_CONFIG_HOME', home/'.config'))
    data = Path(os.environ.get('XDG_DATA_HOME', home/'.local/share'))
    units = config/'systemd/user'
    names = ['g15-daemon','g15-tray','g15_config.py','g15_core.py','g15_install.py','g15_gtk.py','g15_qt.py']
    payloads = {home/'.local/bin'/name: ((root/'bin'/name).read_bytes(), 0o755 if name in ('g15-daemon','g15-tray') else 0o644) for name in names}
    for source in (root/'assets').iterdir():
        if source.is_file():
            payloads[data/'dell-g15'/source.name] = (source.read_bytes(),0o644)
    for name in ('dell-g15-daemon.service','dell-g15-tray.service'):
        payloads[units/name] = (None,0o644) if daemon_only and 'tray' in name else ((root/'systemd'/name).read_bytes(),0o644)
    def quote(path):
        value = str(path)
        for old, new in [('\\','\\\\'), ('"','\\"'), ('`','\\`'), ('$','\\$'), ('%','%%')]:
            value = value.replace(old,new)
        return '"'+value+'"'
    desktop = ('[Desktop Entry]\nName=Dell G15 Control Center\nType=Application\nTerminal=false\nExec='
               +quote(home/'.local/bin/g15-tray')+' --show\nIcon='+str(data/'dell-g15/logo.svg')+'\nCategories=Settings;HardwareSettings;\n')
    payloads[data/'applications/io.github.murilogiatti.DellG15Control.desktop'] = (None if daemon_only else desktop.encode(),0o644)
    def git(*args):
        return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL).decode().strip()
    try:
        sha = git('rev-parse','HEAD') if not git('status','--porcelain') else 'unknown'
    except (OSError,subprocess.CalledProcessError):
        sha = 'unknown'
    payloads[data/'dell-g15/version.json'] = (json.dumps({'commit':sha,'repo_dir':str(root)}).encode(),0o600)
    # Read and stage everything before stopping any service.
    backups, staged = {}, {}
    applied, stopped = [], []
    existing = [name for name in ('dell-g15-daemon.service','dell-g15-tray.service') if (units/name).exists()]
    enabled, active_before = {}, {}
    services_touched = False
    def command(*args, check=True):
        result = runner(['systemctl','--user',*args],capture_output=True,text=True,timeout=20)
        if check and result.returncode:
            raise RuntimeError(result.stderr.strip() or 'systemctl failed: '+' '.join(args))
        return result.returncode == 0
    # Capture service state before mutation. A staging failure must not change services.
    for name in existing:
        enabled[name] = command('is-enabled','--quiet',name,check=False)
        active_before[name] = command('is-active','--quiet',name,check=False)
    try:
        for path,(content,mode) in payloads.items():
            backups[path] = (path.read_bytes(),path.stat().st_mode & 0o777) if path.exists() else (None,mode)
            if content is not None:
                path.parent.mkdir(parents=True,exist_ok=True)
                fd,tmp = tempfile.mkstemp(prefix='.g15-install-',dir=path.parent)
                staged[path] = Path(tmp)
                with os.fdopen(fd,'wb') as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(tmp,mode)
        for name in existing:
            services_touched = True
            if active_before[name]:
                stopped.append(name)
            command('stop',name)
        for path,(content,_mode) in payloads.items():
            if content is None:
                if path.exists(): path.unlink()
            else:
                replace_fn(staged[path],path)
            applied.append(path)
        services_touched = True
        command('daemon-reload')
        desired = ['dell-g15-daemon.service']+([] if daemon_only else ['dell-g15-tray.service'])
        command('enable',*desired)
        if daemon_only and 'dell-g15-tray.service' in existing:
            command('disable','dell-g15-tray.service')
        for name in desired:
            command('restart',name)
            command('is-active','--quiet',name)
        # Retain a return path for a successful installation over an existing version.
        version_path = data/'dell-g15/version.json'
        if backups[version_path][0] is not None:
            import g15_core
            entries = [(str(path),content,mode) for path,(content,mode) in backups.items()]
            g15_core.write_update_backup(entries,str(version_path))
    except Exception as exc:
        errors = []
        # Stop any newly started process before restoring its files.
        if applied:
            for name in ('dell-g15-daemon.service','dell-g15-tray.service'):
                try: command('stop',name,check=False)
                except Exception as err: errors.append(str(err))
        for path in reversed(applied):
            old,mode = backups[path]
            try:
                if old is None:
                    if path.exists(): path.unlink()
                else:
                    fd,tmp = tempfile.mkstemp(prefix='.g15-restore-',dir=path.parent)
                    with os.fdopen(fd,'wb') as stream: stream.write(old)
                    os.chmod(tmp,mode)
                    os.replace(tmp,path)
            except Exception as err: errors.append(f'{path}: {err}')
        if services_touched:
            try:
                command('daemon-reload')
                names_to_restore = ('dell-g15-daemon.service','dell-g15-tray.service') if applied else existing
                for name in names_to_restore:
                    command('enable' if enabled.get(name,False) else 'disable',name,check=False)
                for name in stopped: command('restart',name)
            except Exception as err: errors.append(str(err))
        raise RuntimeError(f'Installation failed: {exc}. Recovery errors: {errors or "none"}') from exc
    finally:
        for path in staged.values():
            if path.exists(): path.unlink()
    return sha


if __name__ == '__main__':
    try:
        install_user(sys.argv[1], '--daemon-only' in sys.argv[2:])
    except Exception as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)
