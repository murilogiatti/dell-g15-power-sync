#!/bin/bash
set -e
# Update script from Legacy (Profiles) to Simplified (White LED) version

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Localization
LANG_CODE="${LANG%%_*}"
if [ "$LANG_CODE" == "pt" ]; then
    MSG_START="--- Migrando do Dell G15 Power Sync (Legado) para Simplificado ---"
    MSG_CLEAN_SVC="-> Limpando serviços antigos de atualização..."
    MSG_CLEAN_BIN="-> Removendo scripts obsoletos (g15-cycle e g15-update)..."
    MSG_RUN_INST="-> Arquivos legados removidos. Executando o instalador da nova versão..."
else
    MSG_START="--- Migrating from Dell G15 Power Sync (Legacy) to Simplified ---"
    MSG_CLEAN_SVC="-> Cleaning up legacy update services..."
    MSG_CLEAN_BIN="-> Removing obsolete scripts (g15-cycle and g15-update)..."
    MSG_RUN_INST="-> Legacy files removed. Running the new version installer..."
fi

echo "$MSG_START"

echo "$MSG_CLEAN_SVC"
systemctl --user stop dell-g15-update.timer 2>/dev/null || true
systemctl --user disable dell-g15-update.timer 2>/dev/null || true
systemctl --user stop dell-g15-update.service 2>/dev/null || true
systemctl --user disable dell-g15-update.service 2>/dev/null || true

rm -f "$HOME/.config/systemd/user/dell-g15-update.timer"
rm -f "$HOME/.config/systemd/user/dell-g15-update.service"

echo "$MSG_CLEAN_BIN"
rm -f "$HOME/.local/bin/g15-cycle.sh"
rm -f "$HOME/.local/bin/g15-update.sh"

systemctl --user daemon-reload

echo "$MSG_RUN_INST"
"$SCRIPT_DIR/install.sh"
