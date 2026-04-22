#!/bin/bash
# Dell G15 Watcher - Background Polling
LAST_PROFILE=""
BIN_PATH="$HOME/.local/bin/g15-sync.sh"

while true; do
    CURRENT=$(powerprofilesctl get | tr -d ' ')
    if [ "$CURRENT" != "$LAST_PROFILE" ]; then
        bash "$BIN_PATH" "$CURRENT"
        LAST_PROFILE="$CURRENT"
    fi
    sleep 2
done
