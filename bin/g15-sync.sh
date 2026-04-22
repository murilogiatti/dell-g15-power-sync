#!/bin/bash
# Dell G15 Power & LED Sync
# Compatible with Dell G15 5515 (4-Zone RGB) and similar models

TARGET="$1"
# Use temporary files in a generic location
COLOR_FILE="/tmp/g15_current_color"
STATE_FILE="/tmp/kbd_backlight_state"

# Determine Profile
if [ -z "$TARGET" ]; then
    CURRENT=$(powerprofilesctl get)
    case "$CURRENT" in
        *power-save*) NEXT="balanced" ;;
        *balanced*)    NEXT="performance" ;;
        *)             NEXT="power-saver" ;;
    esac
    powerprofilesctl set "$NEXT"
    TARGET="$NEXT"
fi

# Map Colors (Supports 4-zone by applying color to all zones via OpenRGB)
ACTUAL=$(powerprofilesctl get)
case "$ACTUAL" in
    *performance*) COLOR="FF0000" ;; # Red
    *balanced*)    COLOR="00FF00" ;; # Green
    *)             COLOR="0000FF" ;; # Blue
esac

echo "$COLOR" > "$COLOR_FILE"

# Apply Soft Brightness if requested
FINAL_COLOR="$COLOR"
if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE")" == "0" ]; then
    R=$(printf "%02X" $(( (16#${COLOR:0:2} * 30) / 100 )))
    G=$(printf "%02X" $(( (16#${COLOR:2:2} * 30) / 100 )))
    B=$(printf "%02X" $(( (16#${COLOR:4:2} * 30) / 100 )))
    FINAL_COLOR="${R}${G}${B}"
fi

# Apply to hardware (ID 1 is standard for Dell G15 in OpenRGB)
openrgb --noautoconnect -d 1 -c "$FINAL_COLOR" -m Static > /dev/null 2>&1
