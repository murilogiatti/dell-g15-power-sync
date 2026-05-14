#!/bin/bash
set -e
# Uninstaller for Dell G15 Power Sync (Simplified)

echo "--- Dell G15 Power Sync Uninstaller ---"

# 1. Stop and Disable Service
echo "-> Stopping and disabling systemd services..."
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
echo "-> Removing scripts from ~/.local/bin/..."
rm -f "$HOME/.local/bin/g15-daemon.sh"
# Legacy scripts cleanup
rm -f "$HOME/.local/bin/g15-cycle.sh"
rm -f "$HOME/.local/bin/g15-update.sh"

# 3. Udev Rules (Optional)
if [ -f "/etc/udev/rules.d/10-alienware.rules" ]; then
    echo "-> Note: Udev rules at /etc/udev/rules.d/10-alienware.rules were kept for safety."
    echo "   You can remove them manually with: sudo rm /etc/udev/rules.d/10-alienware.rules"
fi

echo "--------------------------------------"
echo "Uninstallation complete!"
