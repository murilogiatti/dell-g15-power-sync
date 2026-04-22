#!/bin/bash
# Dell G15 Power & LED Sync
# Compatible with Dell G15 5515 (4-Zone RGB) and similar models

COMMAND="$1"
COLOR_FILE="/tmp/g15_current_color"
STATE_FILE="/tmp/kbd_backlight_state"

# 1. Handle Brightness Toggle
if [ "$COMMAND" == "brightness" ]; then
    if [ ! -f "$STATE_FILE" ] || [ "$(cat "$STATE_FILE")" == "1" ]; then
        echo "0" > "$STATE_FILE"
        MSG="LED: Suave (30%) / Soft"
    else
        echo "1" > "$STATE_FILE"
        MSG="LED: Forte (100%) / Full"
    fi
    # Re-apply current profile with new brightness
    CURRENT=$(powerprofilesctl get)
    COMMAND="$CURRENT"
fi

# 2. Handle Profile Cycle
if [ -z "$COMMAND" ]; then
    CURRENT=$(powerprofilesctl get)
    case "$CURRENT" in
        *power-save*) NEXT="balanced" ;;
        *balanced*)    NEXT="performance" ;;
        *)             NEXT="power-saver" ;;
    esac
    powerprofilesctl set "$NEXT"
    COMMAND="$NEXT"
fi

# 3. Map Colors
case "$COMMAND" in
    *performance*) COLOR="FF0000" ; MSG_P="Performance" ;;
    *balanced*)    COLOR="00FF00" ; MSG_P="Balanced" ;;
    *)             COLOR="0000FF" ; MSG_P="Power Saver" ;;
esac

echo "$COLOR" > "$COLOR_FILE"

# 4. Apply Soft Brightness if requested
FINAL_COLOR="$COLOR"
if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE")" == "0" ]; then
    R=$(printf "%02X" $(( (16#${COLOR:0:2} * 30) / 100 )))
    G=$(printf "%02X" $(( (16#${COLOR:2:2} * 30) / 100 )))
    B=$(printf "%02X" $(( (16#${COLOR:4:2} * 30) / 100 )))
    FINAL_COLOR="${R}${G}${B}"
fi

# 5. Apply to hardware (ID 1 is standard for Dell G15)
/usr/bin/openrgb --noautoconnect -d 1 -c "$FINAL_COLOR" -m Static > /dev/null 2>&1

# Notify user only on manual cycle (command was empty or 'brightness')
if [ -z "$1" ] || [ "$1" == "brightness" ]; then
    notify-send -r 9999 "G15 Hardware" "${MSG_P:-$MSG}" -i preferences-system-power-management
fi
