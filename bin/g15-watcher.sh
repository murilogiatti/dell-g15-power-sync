#!/bin/bash
# Dell G15 Power Profile Watcher
# Monitors for profile changes and triggers the sync script

SCRIPT_PATH="/usr/local/bin/g15-sync.sh"
LAST_PROFILE=""

while true; do
    CURRENT=$(/usr/bin/powerprofilesctl get | tr -d ' ')
    if [ "$CURRENT" != "$LAST_PROFILE" ]; then
        /usr/bin/bash "$SCRIPT_PATH" "$CURRENT"
        LAST_PROFILE="$CURRENT"
    fi
    sleep 2
done
