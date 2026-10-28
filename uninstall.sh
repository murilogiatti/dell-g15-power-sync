#!/bin/bash
set -e
# Dell G15 Ambient Sync & Control Center Uninstaller

LANG_CODE="${LANG%%_*}"
if [ "$LANG_CODE" == "pt" ]; then
    MSG_START="--- Dell G15 Ambient Sync Desinstalador ---"
    MSG_STOP="-> Parando e desabilitando serviços systemd..."
    MSG_RM_SCRIPTS="-> Removendo binários, ícones e atalhos de ~/.local/..."
    MSG_UDEV_NOTE="-> Nota: A regra udev em /etc/udev/rules.d/10-alienware.rules foi mantida por segurança."
    MSG_DONE="--------------------------------------\nDesinstalação concluída!"
else
    MSG_START="--- Dell G15 Ambient Sync Uninstaller ---"
    MSG_STOP="-> Stopping and disabling systemd services..."
    MSG_RM_SCRIPTS="-> Removing binaries, icons and shortcuts from ~/.local/..."
    MSG_UDEV_NOTE="-> Note: Udev rule at /etc/udev/rules.d/10-alienware.rules was kept for safety."
    MSG_DONE="--------------------------------------\nUninstallation complete!"
fi

echo "$MSG_START"

echo "$MSG_STOP"
systemctl --user stop dell-g15-tray.service 2>/dev/null || true
systemctl --user disable dell-g15-tray.service 2>/dev/null || true
systemctl --user stop dell-g15-daemon.service 2>/dev/null || true
systemctl --user disable dell-g15-daemon.service 2>/dev/null || true
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/dell-g15-tray.service"
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/dell-g15-daemon.service"

# Also purge any legacy units if present
systemctl --user stop dell-g15-update.timer 2>/dev/null || true
systemctl --user disable dell-g15-update.timer 2>/dev/null || true
systemctl --user stop dell-g15-update.service 2>/dev/null || true
systemctl --user disable dell-g15-update.service 2>/dev/null || true
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/dell-g15-update.timer"
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/dell-g15-update.service"

echo "$MSG_RM_SCRIPTS"
rm -f "$HOME/.local/bin/g15-daemon"
rm -f "$HOME/.local/bin/g15-tray"
rm -f "$HOME/.local/bin/g15_install.py"
rm -f "$HOME/.local/bin/g15_config.py"
rm -f "$HOME/.local/bin/g15_core.py"
rm -f "$HOME/.local/bin/g15_gtk.py"
rm -f "$HOME/.local/bin/g15_qt.py"
rm -f "$HOME/.local/bin/g15-daemon.sh"
rm -f "$HOME/.local/bin/g15-cycle.sh"
rm -f "$HOME/.local/bin/g15-update.sh"
rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/dell-g15"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps/io.github.murilogiatti.DellG15Control.svg"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps/io.github.murilogiatti.DellG15Control.png"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps/dell-g15-control.svg"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps/dell-g15-control.png"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/status/tray-icon.svg"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/64x64/status/tray-icon.png"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/applications/io.github.murilogiatti.DellG15Control.desktop"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/applications/dell-g15-control.desktop"

if [ -f "/etc/udev/rules.d/10-alienware.rules" ]; then
    echo "$MSG_UDEV_NOTE"
fi

if ! systemctl --user daemon-reload; then
    echo "User files removed; systemd reload failed. Service state could not be confirmed." >&2
    exit 1
fi
echo -e "$MSG_DONE"
