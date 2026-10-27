#!/bin/bash
set -e
# Dell G15 Ambient Sync & Control Center Installer (Direct HID + Netlink + Tray GUI)
# Compatible with Ubuntu/Debian and Fedora Workstation/Kinoite (Atomic)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LANG_CODE="${LANG%%_*}"
if [ "$LANG_CODE" == "pt" ]; then
    MSG_START="--- Dell G15 Ambient Sync & Control Center Instalador ---"
    MSG_CHECK="-> Verificando Python 3..."
    MSG_ERROR="Erro: python3 não está instalado."
    MSG_CLEAN="-> Limpando versões e serviços antigos (migração limpa)..."
    MSG_SCRIPTS="-> Binários e ícones instalados em ~/.local/"
    MSG_SERVICE="-> Serviços Systemd e atalho de aplicativo configurados"
    MSG_UDEV="-> Atualizando regras udev para acesso direto ao controlador HID (requer sudo)..."
    MSG_DONE="--------------------------------------\nInstalação concluída! O daemon e o ícone na barra superior estão ativos."
else
    MSG_START="--- Dell G15 Ambient Sync & Control Center Installer ---"
    MSG_CHECK="-> Checking for Python 3..."
    MSG_ERROR="Error: python3 is not installed."
    MSG_CLEAN="-> Cleaning up legacy files and services (clean migration)..."
    MSG_SCRIPTS="-> Binaries and icons installed in ~/.local/"
    MSG_SERVICE="-> Systemd user services and desktop shortcut configured"
    MSG_UDEV="-> Updating udev rules for direct HID controller access (requires sudo)..."
    MSG_DONE="--------------------------------------\nInstallation complete! Daemon and top-bar tray indicator are now active."
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
systemctl --user stop dell-g15-tray.service 2>/dev/null || true
systemctl --user stop dell-g15-update.timer 2>/dev/null || true
systemctl --user disable dell-g15-update.timer 2>/dev/null || true
systemctl --user stop dell-g15-update.service 2>/dev/null || true
systemctl --user disable dell-g15-update.service 2>/dev/null || true

rm -f "$HOME/.config/systemd/user/dell-g15-update.timer"
rm -f "$HOME/.config/systemd/user/dell-g15-update.service"
rm -f "$HOME/.local/bin/g15-daemon.sh"
rm -f "$HOME/.local/bin/g15-cycle.sh"
rm -f "$HOME/.local/bin/g15-update.sh"

# 3. Install direct-HID daemon, tray indicator, and visual assets/icons
mkdir -p "$HOME/.local/bin"
cp "$SCRIPT_DIR/bin/g15-daemon" "$HOME/.local/bin/g15-daemon"
cp "$SCRIPT_DIR/bin/g15-tray" "$HOME/.local/bin/g15-tray"
chmod +x "$HOME/.local/bin/g15-daemon" "$HOME/.local/bin/g15-tray"

mkdir -p "$HOME/.local/share/dell-g15"
cp "$SCRIPT_DIR/assets/"* "$HOME/.local/share/dell-g15/"

mkdir -p "$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$HOME/.local/share/icons/hicolor/scalable/status"
mkdir -p "$HOME/.local/share/icons/hicolor/64x64/status"
cp "$SCRIPT_DIR/assets/logo.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/dell-g15-control.svg"
cp "$SCRIPT_DIR/assets/logo.png" "$HOME/.local/share/icons/hicolor/256x256/apps/dell-g15-control.png"
cp "$SCRIPT_DIR/assets/tray-icon.svg" "$HOME/.local/share/icons/hicolor/scalable/status/tray-icon.svg"
cp "$SCRIPT_DIR/assets/tray-icon.png" "$HOME/.local/share/icons/hicolor/64x64/status/tray-icon.png"
echo "$MSG_SCRIPTS"

# 4. Install Systemd User Services & Desktop Launcher
mkdir -p "$HOME/.config/systemd/user/"
cp "$SCRIPT_DIR/systemd/dell-g15-daemon.service" "$HOME/.config/systemd/user/dell-g15-daemon.service"
cp "$SCRIPT_DIR/systemd/dell-g15-tray.service" "$HOME/.config/systemd/user/dell-g15-tray.service"

mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/dell-g15-control.desktop" <<EOF
[Desktop Entry]
Name=Dell G15 Control Center
Comment=Configure Dell G15 4-Zone RGB, Ambient Sync, Effects and Power Profiles
Comment[pt]=Configurar Zonas RGB, Brilho Automático, Efeitos e Energia do Dell G15
Exec=$HOME/.local/bin/g15-tray --show
Icon=$HOME/.local/share/icons/hicolor/scalable/apps/dell-g15-control.svg
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;GTK;
Keywords=Dell;G15;Alienware;RGB;Keyboard;Backlight;
EOF
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

# 6. Reload and start services
systemctl --user daemon-reload
systemctl --user enable dell-g15-daemon.service dell-g15-tray.service
systemctl --user restart dell-g15-daemon.service dell-g15-tray.service

echo -e "$MSG_DONE"
