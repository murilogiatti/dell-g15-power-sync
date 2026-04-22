#!/bin/bash
# Dell G15 Keyboard Brightness Toggle
# Swaps between Full (100%) and Soft (30%) brightness using RGB math

STATE_FILE="/tmp/g15_kbd_state"
COLOR_FILE="/tmp/g15_current_color"

# Fallback: if no color is saved, assume Green
if [ ! -f "$COLOR_FILE" ]; then echo "00FF00" > "$COLOR_FILE"; fi
BASE_COLOR=$(cat "$COLOR_FILE")

# Fallback: if no state is saved, assume Full (1)
if [ ! -f "$STATE_FILE" ]; then echo "1" > "$STATE_FILE"; fi
CURRENT=$(cat "$STATE_FILE")

if [ "$CURRENT" == "1" ]; then
    # FULL -> SOFT (30%)
    R=$(printf "%02X" $(( (16#${BASE_COLOR:0:2} * 30) / 100 )))
    G=$(printf "%02X" $(( (16#${BASE_COLOR:2:2} * 30) / 100 )))
    B=$(printf "%02X" $(( (16#${BASE_COLOR:4:2} * 30) / 100 )))
    FINAL_COLOR="${R}${G}${B}"
    echo "0" > "$STATE_FILE"
    MSG_PT="Brilho: Suave"
    MSG_EN="Brightness: Soft"
else
    # SOFT -> FULL (100%)
    FINAL_COLOR="$BASE_COLOR"
    echo "1" > "$STATE_FILE"
    MSG_PT="Brilho: Forte"
    MSG_EN="Brightness: Full"
fi

# Apply to hardware (Device ID 1)
/usr/bin/openrgb --noautoconnect -d 1 -c "$FINAL_COLOR" -m Static > /dev/null 2>&1
notify-send -r 9998 "Dell G15" "$MSG_PT / $MSG_EN" -i "keyboard-brightness"
