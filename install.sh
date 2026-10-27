#!/bin/bash
set -e
# Dell G15 Ambient Sync Installer (Direct HID + Netlink Architecture)
# Compatible with Ubuntu/Debian and Fedora Workstation/Kinoite (Atomic)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LANG_CODE="${LANG%%_*}"
if [ "$LANG_CODE" == "pt" ]; then
    MSG_START="--- Dell G15 Ambient Sync Instalador ---"
    MSG_CHECK="-> Verificando Python 3..."
    MSG_ERROR="Erro: python3 não está instalado."
    MSG_CLEAN="-> Limpando versões e serviços antigos (migração limpa)..."
    MSG_SCRIPTS="-> Daemon instalado em ~/.local/bin/g15-daemon"
    MSG_SERVICE="-> Serviço Systemd configurado em ~/.config/systemd/user/"
    MSG_UDEV="-> Atualizando regras udev para acesso direto ao controlador HID (requer sudo)..."
    MSG_DONE="--------------------------------------\nInstalação concluída! O Dell G15 Ambient Sync está ativo."
else
    MSG_START="--- Dell G15 Ambient Sync Installer ---"
    MSG_CHECK="-> Checking for Python 3..."
    MSG_ERROR="Error: python3 is not installed."
    MSG_CLEAN="-> Cleaning up legacy files and services (clean migration)..."
    MSG_SCRIPTS="-> Daemon installed at ~/.local/bin/g15-daemon"
    MSG_SERVICE="-> Systemd user service configured at ~/.config/systemd/user/"
    MSG_UDEV="-> Updating udev rules for direct HID controller access (requires sudo)..."
    MSG_DONE="--------------------------------------\nInstallation complete! Dell G15 Ambient Sync is now running."
fi

echo -e "$MSG_START"

# 1. Check Python 3
echo "$MSG_CHECK"
if ! command -v python3 &> /dev/null; then
    echo "$MSG_ERROR"
    exit 1
fi

# 2. Clean migration from any legacy version (v1-v5)
echo "$MSG_CLEAN"
systemctl --user stop dell-g15-daemon.service 2>/dev/null || true
systemctl --user stop dell-g15-update.timer 2>/dev/null || true
systemctl --user disable dell-g15-update.timer 2>/dev/null || true
systemctl --user stop dell-g15-update.service 2>/dev/null || true
systemctl --user disable dell-g15-update.service 2>/dev/null || true

rm -f "$HOME/.config/systemd/user/dell-g15-update.timer"
rm -f "$HOME/.config/systemd/user/dell-g15-update.service"
rm -f "$HOME/.local/bin/g15-daemon.sh"
rm -f "$HOME/.local/bin/g15-cycle.sh"
rm -f "$HOME/.local/bin/g15-update.sh"

# 3. Install new direct-HID daemon
mkdir -p "$HOME/.local/bin"
cp "$SCRIPT_DIR/bin/g15-daemon" "$HOME/.local/bin/g15-daemon"
chmod +x "$HOME/.local/bin/g15-daemon"
echo "$MSG_SCRIPTS"

# 4. Install Systemd User Service
mkdir -p "$HOME/.config/systemd/user/"
cp "$SCRIPT_DIR/systemd/dell-g15-daemon.service" "$HOME/.config/systemd/user/dell-g15-daemon.service"
echo "$MSG_SERVICE"

# 5. Udev Rules (Works on both standard Linux and immutable Fedora Kinoite /etc)
if ! cmp -s "$SCRIPT_DIR/udev/10-alienware.rules" "/etc/udev/rules.d/10-alienware.rules"; then
    if [ -t 0 ] || sudo -n true 2>/dev/null; then
        echo "$MSG_UDEV"
        sudo cp "$SCRIPT_DIR/udev/10-alienware.rules" /etc/udev/rules.d/10-alienware.rules
        sudo udevadm control --reload-rules
        sudo udevadm trigger --subsystem-match=hidraw --subsystem-match=usb
    fi
fi

# 6. Reload and start daemon
systemctl --user daemon-reload
systemctl --user enable dell-g15-daemon.service
systemctl --user restart dell-g15-daemon.service

echo -e "$MSG_DONE"
