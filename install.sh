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
for source in g15-daemon g15-tray g15_config.py g15_install.py g15_core.py g15_gtk.py g15_qt.py; do
    test -r "$SCRIPT_DIR/bin/$source"
done
for source in dell-g15-daemon.service dell-g15-tray.service; do
    test -r "$SCRIPT_DIR/systemd/$source"
done
test -r "$SCRIPT_DIR/assets/logo.svg"
python3 - "$SCRIPT_DIR" <<'PY'
import pathlib, sys
root = pathlib.Path(sys.argv[1])
for name in ('g15-daemon', 'g15-tray', 'g15_config.py', 'g15_install.py', 'g15_core.py', 'g15_gtk.py', 'g15_qt.py'):
    compile((root / 'bin' / name).read_bytes(), name, 'exec')
PY
ARGS=()
if [ "$DAEMON_ONLY" = 1 ]; then ARGS+=(--daemon-only); fi
python3 "$SCRIPT_DIR/bin/g15_install.py" "$SCRIPT_DIR" "${ARGS[@]}"
python3 "$SCRIPT_DIR/bin/g15-tray" --diagnose
echo "User files installed. No system packages or permissions were changed."
echo "HID/evdev access and optional features depend on existing system permissions and components."
