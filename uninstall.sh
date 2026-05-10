#!/bin/bash
set -e
# Uninstaller for Dell G15 Power Sync

echo "--- Dell G15 Power Sync Uninstaller ---"

# 1. Stop and Disable Service
echo "-> Stopping and disabling systemd service..."
systemctl --user stop dell-g15-daemon.service 2>/dev/null
systemctl --user disable dell-g15-daemon.service 2>/dev/null
rm "$HOME/.config/systemd/user/dell-g15-daemon.service" 2>/dev/null
systemctl --user daemon-reload

# 2. Remove Scripts
echo "-> Removing scripts from ~/.local/bin/..."
rm "$HOME/.local/bin/g15-daemon.sh" 2>/dev/null
rm "$HOME/.local/bin/g15-cycle.sh" 2>/dev/null

# 3. Udev Rules (Optional)
if [ -f "/etc/udev/rules.d/10-alienware.rules" ]; then
    echo "-> Note: Udev rules at /etc/udev/rules.d/10-alienware.rules were kept for safety."
    echo "   You can remove them manually with: sudo rm /etc/udev/rules.d/10-alienware.rules"
fi

echo "--------------------------------------"
echo "Uninstallation complete!"
