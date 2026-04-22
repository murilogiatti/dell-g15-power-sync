#!/bin/bash
# Uninstaller for Dell G15 Power Sync (Bilingual)

echo "--- Dell G15 Power Sync Uninstaller / Desinstalador ---"

# 1. Stop and Disable Service
echo "-> Stopping and disabling systemd service / Parando e desativando o serviço systemd..."
systemctl --user stop g15-power-sync.service 2>/dev/null
systemctl --user disable g15-power-sync.service 2>/dev/null
rm -f "$HOME/.config/systemd/user/g15-power-sync.service"
systemctl --user daemon-reload

# 2. Remove Scripts
echo "-> Removing scripts / Removendo scripts..."
rm -f "$HOME/.local/bin/g15-sync.sh"
rm -f "$HOME/.local/bin/g15-watcher.sh"
rm -f "$HOME/.local/bin/kbd_toggle.sh"

# 3. Remove Desktop Entries
echo "-> Removing desktop entries / Removendo atalhos do menu..."
rm -f "$HOME/.local/share/applications/g15-sync-cycle.desktop"
rm -f "$HOME/.local/share/applications/g15-brightness-cycle.desktop"

# 4. Udev Rules (Optional)
if [ -f "/etc/udev/rules.d/10-alienware.rules" ]; then
    echo "--------------------------------------"
    echo "EN: Do you want to remove the udev rules? (Requires sudo)"
    echo "PT: Deseja remover as regras udev? (Requer sudo)"
    read -p "(y/n) / (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[YySs]$ ]]; then
        sudo rm -f /etc/udev/rules.d/10-alienware.rules
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        echo "-> Udev rules removed / Regras udev removidas"
    fi
fi

echo "--------------------------------------"
echo "Uninstallation complete! / Desinstalação completa!"
