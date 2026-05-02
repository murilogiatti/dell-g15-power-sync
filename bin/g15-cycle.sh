#!/bin/bash
set -e
# Cycle power profiles - The daemon will detect the change and update LEDs.
CURRENT=$(powerprofilesctl get)
case "$CURRENT" in
    *power-save*) NEXT="balanced" ;;
    *balanced*)    NEXT="performance" ;;
    *)             NEXT="power-saver" ;;
esac
powerprofilesctl set "$NEXT"
