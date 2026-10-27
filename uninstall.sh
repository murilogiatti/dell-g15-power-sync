#!/bin/bash
set -e
# Uninstaller for Dell G15 Power Sync (Simplified)

# Localization
LANG_CODE="${LANG%%_*}"
if [ "$LANG_CODE" == "pt" ]; then
    MSG_START="--- Dell G15 Power Sync Desinstalador ---"
    MSG_STOP="-> Parando e desabilitando serviços systemd..."
    MSG_RM_SCRIPTS="-> Removendo scripts de ~/.local/bin/..."
    MSG_UDEV_NOTE="-> Nota: As regras udev em /etc/udev/rules.d/10-alienware.rules foram mantidas por segurança."
    MSG_UDEV_CMD="   Você pode removê-las manualmente com: sudo rm /etc/udev/rules.d/10-alienware.rules"
    MSG_DONE="--------------------------------------\nDesinstalação concluída!"
else
    MSG_START="--- Dell G15 Power Sync Uninstaller ---"
    MSG_STOP="-> Stopping and disabling systemd services..."
    MSG_RM_SCRIPTS="-> Removing scripts from ~/.local/bin/..."
    MSG_UDEV_NOTE="-> Note: Udev rules at /etc/udev/rules.d/10-alienware.rules were kept for safety."
    MSG_UDEV_CMD="   You can remove them manually with: sudo rm /etc/udev/rules.d/10-alienware.rules"
    MSG_DONE="--------------------------------------\nUninstallation complete!"
fi

echo "$MSG_START"

# 1. Stop and Disable Service
echo "$MSG_STOP"
systemctl --user stop dell-g15-daemon.service 2>/dev/null || true
systemctl --user disable dell-g15-daemon.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/dell-g15-daemon.service"

# Legacy services cleanup just in case
systemctl --user stop dell-g15-update.timer 2>/dev/null || true
systemctl --user disable dell-g15-update.timer 2>/dev/null || true
systemctl --user stop dell-g15-update.service 2>/dev/null || true
systemctl --user disable dell-g15-update.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/dell-g15-update.timer"
rm -f "$HOME/.config/systemd/user/dell-g15-update.service"

systemctl --user daemon-reload

# 2. Remove Script
echo "$MSG_RM_SCRIPTS"
rm -f "$HOME/.local/bin/g15-daemon.sh"
# Legacy scripts cleanup
rm -f "$HOME/.local/bin/g15-cycle.sh"
rm -f "$HOME/.local/bin/g15-update.sh"

# 3. Udev Rules (Optional)
if [ -f "/etc/udev/rules.d/10-alienware.rules" ]; then
    echo "$MSG_UDEV_NOTE"
    echo "$MSG_UDEV_CMD"
fi

echo -e "$MSG_DONE"
