#!/bin/bash
set -e

# Caminho do repositório local
REPO_DIR="$HOME/github/dell-g15-power-sync"

LANG_CODE="${LANG%%_*}"
if [ "$LANG_CODE" == "pt" ]; then
    MSG_START="--- Atualizando Dell G15 Power Sync ---"
    MSG_ERR_DIR="Repositório não encontrado em $REPO_DIR"
    MSG_PULL="-> Baixando atualizações do GitHub..."
    MSG_INSTALL="-> Reinstalando..."
else
    MSG_START="--- Updating Dell G15 Power Sync ---"
    MSG_ERR_DIR="Repository not found at $REPO_DIR"
    MSG_PULL="-> Pulling updates from GitHub..."
    MSG_INSTALL="-> Reinstalling..."
fi

echo -e "$MSG_START"

if [ ! -d "$REPO_DIR/.git" ]; then
    echo "$MSG_ERR_DIR"
    exit 1
fi

cd "$REPO_DIR"
echo "$MSG_PULL"
git pull origin main

echo "$MSG_INSTALL"
./install.sh