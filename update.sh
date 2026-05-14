#!/bin/bash
set -e
# Update script from Legacy (Profiles) to Simplified (White LED) version

echo "--- Migrando do Dell G15 Power Sync (Legado) para Simplificado ---"

echo "-> Limpando serviços antigos de atualização..."
systemctl --user stop dell-g15-update.timer 2>/dev/null || true
systemctl --user disable dell-g15-update.timer 2>/dev/null || true
systemctl --user stop dell-g15-update.service 2>/dev/null || true
systemctl --user disable dell-g15-update.service 2>/dev/null || true

rm -f "$HOME/.config/systemd/user/dell-g15-update.timer"
rm -f "$HOME/.config/systemd/user/dell-g15-update.service"

echo "-> Removendo scripts obsoletos (g15-cycle e g15-update)..."
rm -f "$HOME/.local/bin/g15-cycle.sh"
rm -f "$HOME/.local/bin/g15-update.sh"

systemctl --user daemon-reload

echo "-> Arquivos legados removidos. Executando o instalador da nova versão..."
./install.sh
