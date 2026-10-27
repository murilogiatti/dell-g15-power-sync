#!/bin/bash
set -e
# Dell G15 Ambient Sync & Control Center Uninstaller

LANG_CODE="${LANG%%_*}"
if [ "$LANG_CODE" == "pt" ]; then
    MSG_START="--- Dell G15 Ambient Sync Desinstalador ---"
    MSG_STOP="-> Parando e desabilitando serviços systemd..."
    MSG_RM_SCRIPTS="-> Removendo binários e atalhos de ~/.local/..."
    MSG_UDEV_NOTE="-> Nota: A regra udev em /etc/udev/rules.d/10-alienware.rules foi mantida por segurança."
    MSG_UDEV_CMD="   Para removê-la manualmente: sudo rm -f /etc/udev/rules.d/10-alienware.rules"
    MSG_DONE="--------------------------------------\nDesinstalação concluída!"
else
    MSG_START="--- Dell G15 Ambient Sync Uninstaller ---"
    MSG_STOP="-> Stopping and disabling systemd services..."
    MSG_RM_SCRIPTS="-> Removing binaries and shortcuts from ~/.local/..."
    MSG_UDEV_NOTE="-> Note: Udev rule at /etc/udev/rules.d/10-alienware.rules was kept for safety."
    MSG_UDEV_CMD="   To remove it manually: sudo rm -f /etc/udev/rules.d/10-alienware.rules"
    MSG_DONE="--------------------------------------\nUninstallation complete!"
fi

echo "$MSG_START"

echo "$MSG_STOP"
systemctl --user stop dell-g15-tray.service 2>/dev/null || true
systemctl --user disable dell-g15-tray.service 2>/dev/null || true
systemctl --user stop dell-g15-daemon.service 2>/dev/null || true
systemctl --user disable dell-g15-daemon.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/dell-g15-tray.service"
rm -f "$HOME/.config/systemd/user/dell-g15-daemon.service"

# Also purge any legacy units if present
systemctl --user stop dell-g15-update.timer 2>/dev/null || true
systemctl --user disable dell-g15-update.timer 2>/dev/null || true
systemctl --user stop dell-g15-update.service 2>/dev/null || true
systemctl --user disable dell-g15-update.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/dell-g15-update.timer"
rm -f "$HOME/.config/systemd/user/dell-g15-update.service"

systemctl --user daemon-reload

echo "$MSG_RM_SCRIPTS"
rm -f "$HOME/.local/bin/g15-daemon"
rm -f "$HOME/.local/bin/g15-tray"
rm -f "$HOME/.local/bin/g15-daemon.sh"
rm -f "$HOME/.local/bin/g15-cycle.sh"
rm -f "$HOME/.local/bin/g15-update.sh"
rm -f "$HOME/.local/share/applications/dell-g15-control.desktop"

if [ -f "/etc/udev/rules.d/10-alienware.rules" ]; then
    echo "$MSG_UDEV_NOTE"
    echo "$MSG_UDEV_CMD"
fi

echo -e "$MSG_DONE"
