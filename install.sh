#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
# User-only installation on mutable and immutable systems. Never installs dependencies.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_ONLY=0
case "${1:-}" in
    --daemon-only) DAEMON_ONLY=1 ;;
    "") ;;
    *) echo "Usage: ./install.sh [--daemon-only]" >&2; exit 2 ;;
esac
command -v python3 >/dev/null || { echo "Python 3 unavailable; nothing installed." >&2; exit 1; }
command -v systemctl >/dev/null || { echo "User systemd unavailable; nothing installed." >&2; exit 1; }
# All prerequisites are checked before stopping the installed application.
systemctl --user show-environment >/dev/null
if [ "$DAEMON_ONLY" = 0 ]; then
    python3 "$SCRIPT_DIR/bin/g15-tray" --check-dependencies || exit 1
fi
for source in g15-daemon g15-tray g15_core.py g15_gtk.py g15_qt.py; do
    test -r "$SCRIPT_DIR/bin/$source"
done
for source in dell-g15-daemon.service dell-g15-tray.service; do
    test -r "$SCRIPT_DIR/systemd/$source"
done
test -r "$SCRIPT_DIR/assets/logo.svg"
python3 - "$SCRIPT_DIR" <<'PY'
import pathlib, sys
root = pathlib.Path(sys.argv[1])
for name in ('g15-daemon', 'g15-tray', 'g15_core.py', 'g15_gtk.py', 'g15_qt.py'):
    compile((root / 'bin' / name).read_bytes(), name, 'exec')
PY
CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}"
DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}"
mkdir -p "$HOME/.local/bin" "$CONFIG_ROOT/systemd/user" "$DATA_ROOT/dell-g15"
systemctl --user stop dell-g15-daemon.service dell-g15-tray.service 2>/dev/null || true
for source in g15-daemon g15-tray g15_core.py g15_gtk.py g15_qt.py; do
    cp "$SCRIPT_DIR/bin/$source" "$HOME/.local/bin/$source"
done
chmod 755 "$HOME/.local/bin/g15-daemon" "$HOME/.local/bin/g15-tray"
chmod 644 "$HOME/.local/bin/g15_core.py" "$HOME/.local/bin/g15_gtk.py" "$HOME/.local/bin/g15_qt.py"
cp "$SCRIPT_DIR/assets/"* "$DATA_ROOT/dell-g15/"
cp "$SCRIPT_DIR/systemd/dell-g15-daemon.service" "$CONFIG_ROOT/systemd/user/"
if [ "$DAEMON_ONLY" = 0 ]; then
    cp "$SCRIPT_DIR/systemd/dell-g15-tray.service" "$CONFIG_ROOT/systemd/user/"
    mkdir -p "$DATA_ROOT/applications"
    python3 - "$DATA_ROOT" "$HOME" <<'PY'
import pathlib, sys
root, home = map(pathlib.Path, sys.argv[1:])
# Escape desktop-entry reserved characters, including paths containing spaces.
def quoted(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'
(root / 'applications/io.github.murilogiatti.DellG15Control.desktop').write_text(
    '[Desktop Entry]\nName=Dell G15 Control Center\nType=Application\nTerminal=false\n'
    + 'Exec=' + quoted(home / '.local/bin/g15-tray') + ' --show\n'
    + 'Icon=' + str(root / 'dell-g15/logo.svg') + '\nCategories=Settings;HardwareSettings;\n')
PY
else
    systemctl --user disable dell-g15-tray.service 2>/dev/null || true
    rm -f "$CONFIG_ROOT/systemd/user/dell-g15-tray.service"
    rm -f "$DATA_ROOT/applications/io.github.murilogiatti.DellG15Control.desktop"
fi
python3 - "$SCRIPT_DIR" "$DATA_ROOT/dell-g15/version.json" <<'PY'
import json, pathlib, subprocess, sys
root, output = sys.argv[1:]
try:
    sha = subprocess.check_output(['git', '-C', root, 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL).decode().strip()
    if subprocess.check_output(['git', '-C', root, 'status', '--porcelain']):
        sha = 'unknown'  # Local edits must never masquerade as a published commit.
except (OSError, subprocess.CalledProcessError):
    sha = 'unknown'
pathlib.Path(output).write_text(json.dumps({'commit': sha, 'repo_dir': root}, indent=2) + '\n')
PY
systemctl --user daemon-reload
systemctl --user enable dell-g15-daemon.service
systemctl --user restart dell-g15-daemon.service
systemctl --user is-active --quiet dell-g15-daemon.service
if [ "$DAEMON_ONLY" = 0 ]; then
    systemctl --user enable dell-g15-tray.service
    systemctl --user restart dell-g15-tray.service
    systemctl --user is-active --quiet dell-g15-tray.service
fi
python3 "$SCRIPT_DIR/bin/g15-tray" --diagnose
echo "User files installed. No system packages or permissions were changed."
echo "HID/evdev access and optional features depend on existing system permissions and components."
