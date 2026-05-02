#!/bin/bash
# Installer for Dell G15 Power Sync (Refactored for Ubuntu 26.04)

# Localization
LANG_CODE="${LANG%%_*}"
if [ "$LANG_CODE" == "pt" ]; then
    MSG_START="--- Dell G15 Power Sync Instalador ---"
    MSG_CHECK="-> Verificando dependências..."
    MSG_ERROR="Erro: %s não está instalado. Por favor, instale-o primeiro."
    MSG_STOP="-> Parando serviço existente..."
    MSG_SCRIPTS="-> Scripts instalados em ~/.local/bin/"
    MSG_SERVICE="-> Serviço Systemd criado"
    MSG_UDEV="-> Instalando regras udev (requer sudo)..."
    MSG_DONE="--------------------------------------\nInstalação completa! O daemon está rodando.\nVocê pode usar 'g15-cycle.sh' para alternar perfis."
else
    MSG_START="--- Dell G15 Power Sync Installer ---"
    MSG_CHECK="-> Checking dependencies..."
    MSG_ERROR="Error: %s is not installed. Please install it first."
    MSG_STOP="-> Stopping existing service..."
    MSG_SCRIPTS="-> Scripts installed in ~/.local/bin/"
    MSG_SERVICE="-> Systemd service created"
    MSG_UDEV="-> Installing udev rules (requires sudo)..."
    MSG_DONE="--------------------------------------\nInstallation complete! The daemon is now running.\nYou can use 'g15-cycle.sh' to change profiles."
fi

echo -e "$MSG_START"

# 0. Check Dependencies
echo "$MSG_CHECK"
for cmd in openrgb powerprofilesctl notify-send; do
    if ! command -v "$cmd" &> /dev/null; then
        # shellcheck disable=SC2059
        printf "$MSG_ERROR\n" "$cmd"
        exit 1
    fi
done

# 1. Stop existing service if running
if systemctl --user is-active --quiet dell-g15-daemon.service; then
    echo "$MSG_STOP"
    systemctl --user stop dell-g15-daemon.service
fi

# 2. Install Scripts
mkdir -p "$HOME/.local/bin"
cp bin/g15-daemon.sh "$HOME/.local/bin/"
cp bin/g15-cycle.sh "$HOME/.local/bin/"
cp bin/g15-update.sh "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/g15-daemon.sh"
chmod +x "$HOME/.local/bin/g15-cycle.sh"
chmod +x "$HOME/.local/bin/g15-update.sh"
echo "$MSG_SCRIPTS"

# 3. Setup Systemd Service
mkdir -p "$HOME/.config/systemd/user/"
cp systemd/dell-g15-daemon.service "$HOME/.config/systemd/user/dell-g15-daemon.service"
cp systemd/dell-g15-update.service "$HOME/.config/systemd/user/dell-g15-update.service"
cp systemd/dell-g15-update.timer "$HOME/.config/systemd/user/dell-g15-update.timer"
echo "$MSG_SERVICE"

# 4. Udev Rules (For non-root hardware access)
if [ ! -f "/etc/udev/rules.d/10-alienware.rules" ]; then
    echo "$MSG_UDEV"
    sudo cp udev/10-alienware.rules /etc/udev/rules.d/
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    # Load i2c-dev for stability
    sudo modprobe i2c-dev
    echo "i2c-dev" | sudo tee /etc/modules-load.d/i2c-dev.conf
fi

# 5. Reload and Start
systemctl --user daemon-reload
systemctl --user enable dell-g15-daemon.service
systemctl --user restart dell-g15-daemon.service
systemctl --user enable dell-g15-update.timer
systemctl --user start dell-g15-update.timer

echo -e "$MSG_DONE"
