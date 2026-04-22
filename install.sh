#!/bin/bash
# Installer for Dell G15 Power Sync (Bilingual)

echo "--- Dell G15 Power Sync Installer / Instalador ---"

# 0. Check Dependencies
echo "-> Checking dependencies / Verificando dependências..."
for cmd in openrgb powerprofilesctl notify-send; do
    if ! command -v $cmd &> /dev/null; then
        echo "EN: Error: $cmd is not installed."
        echo "PT: Erro: $cmd não está instalado."
        exit 1
    fi
done

# 1. Stop existing service if running
if systemctl --user is-active --quiet g15-power-sync.service; then
    echo "-> Stopping existing service for update / Parando serviço existente para atualização..."
    systemctl --user stop g15-power-sync.service
fi

# 2. Install Scripts
mkdir -p "$HOME/.local/bin"
cp bin/g15-sync.sh "$HOME/.local/bin/"
cp bin/g15-watcher.sh "$HOME/.local/bin/"
cp bin/kbd_toggle.sh "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/g15-sync.sh"
chmod +x "$HOME/.local/bin/g15-watcher.sh"
chmod +x "$HOME/.local/bin/kbd_toggle.sh"
echo "-> Scripts installed / Scripts instalados"

# 3. Setup Systemd Service
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
echo "-> Systemd service created / Serviço Systemd criado"

# 4. Setup Desktop Entries (App Menu)
mkdir -p "$HOME/.local/share/applications/"
sed "s|\$HOME|$HOME|g" desktop/g15-sync-cycle.desktop > "$HOME/.local/share/applications/g15-sync-cycle.desktop"
sed "s|\$HOME|$HOME|g" desktop/g15-brightness-cycle.desktop > "$HOME/.local/share/applications/g15-brightness-cycle.desktop"
echo "-> App Menu shortcuts created / Atalhos no menu criados"

# 5. Udev Rules
if [ ! -f "/etc/udev/rules.d/10-alienware.rules" ]; then
    echo "--------------------------------------"
    echo "EN: Do you want to install udev rules for non-root hardware access?"
    echo "PT: Deseja instalar as regras udev para acesso ao hardware sem root?"
    read -p "(y/n) / (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[YySs]$ ]]; then
        sudo cp udev/10-alienware.rules /etc/udev/rules.d/
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        echo "-> Udev rules installed / Regras udev instaladas"
    fi
else
    echo "-> Udev rules already present / Regras udev já presentes"
fi

# 6. Reload and Start
systemctl --user daemon-reload
systemctl --user enable g15-power-sync.service
systemctl --user restart g15-power-sync.service

echo "--------------------------------------"
echo "Installation/Update complete! / Instalação/Atualização completa!"
echo "The shortcuts are now available in your App Menu. / Os atalhos estão no menu."
