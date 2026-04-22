#!/bin/bash
# Installer for Dell G15 Power Sync

echo "--- Dell G15 Power Sync Installer ---"

# 1. Install Scripts
mkdir -p "$HOME/.local/bin"
cp bin/g15-sync.sh "$HOME/.local/bin/"
cp bin/g15-watcher.sh "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/g15-sync.sh"
chmod +x "$HOME/.local/bin/g15-watcher.sh"

# 2. Setup Systemd Service
mkdir -p "$HOME/.config/systemd/user/"
cat <<EOF > "$HOME/.config/systemd/user/g15-power-sync.service"
[Unit]
Description=Dell G15 Power & LED Sync
After=graphical-session.target

[Service]
ExecStart=$HOME/.local/bin/g15-watcher.sh
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

# 3. Setup Desktop Entry (App Menu)
mkdir -p "$HOME/.local/share/applications/"
sed "s|\$HOME|$HOME|g" desktop/g15-sync-cycle.desktop > "$HOME/.local/share/applications/g15-sync-cycle.desktop"

# 4. Udev Rules (Optional but recommended)
read -p "Do you want to install udev rules for non-root hardware access? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo cp udev/10-alienware.rules /etc/udev/rules.d/
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo "Udev rules installed."
fi

# 5. Reload and Start
systemctl --user daemon-reload
systemctl --user enable g15-power-sync.service
systemctl --user restart g15-power-sync.service

echo "--------------------------------------"
echo "Installation complete!"
echo "The service is running and will start automatically on login."
echo "The 'Dell G15 Cycle Power' shortcut is now available in your App Menu."
