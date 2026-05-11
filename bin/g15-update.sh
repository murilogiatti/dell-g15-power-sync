#!/bin/bash
set -e

# Caminho do repositório local
REPO_DIR="$HOME/github/dell-g15-power-sync"

LANG_CODE="${LANG%%_*}"
if [ "$LANG_CODE" == "pt" ]; then
    MSG_START="--- Atualizando Dell G15 Power Sync ---"
    MSG_ERR_DIR="Repositório não encontrado em $REPO_DIR"
    MSG_FETCH="-> Verificando novas versões no GitHub..."
    MSG_UPDATE="-> Atualização encontrada! Baixando..."
    MSG_INSTALL="-> Reinstalando e reiniciando o serviço..."
    MSG_UPTODATE="-> Nenhuma atualização encontrada. O sistema já está na versão mais recente."
else
    MSG_START="--- Updating Dell G15 Power Sync ---"
    MSG_ERR_DIR="Repository not found at $REPO_DIR"
    MSG_FETCH="-> Checking for new versions on GitHub..."
    MSG_UPDATE="-> Update found! Pulling..."
    MSG_INSTALL="-> Reinstalling and restarting service..."
    MSG_UPTODATE="-> No updates found. The system is already up to date."
fi

echo -e "$MSG_START"

if [ ! -d "$REPO_DIR/.git" ]; then
    echo "$MSG_ERR_DIR"
    exit 1
fi

cd "$REPO_DIR"
echo "$MSG_FETCH"
git fetch origin main > /dev/null 2>&1

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
    echo "$MSG_UPDATE"
    git pull origin main
    echo "$MSG_INSTALL"
    ./install.sh
else
    echo "$MSG_UPTODATE"
fi
