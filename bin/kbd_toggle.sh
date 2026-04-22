#!/bin/bash
# Script to toggle keyboard brightness via RGB calculation
STATE_FILE="/tmp/kbd_backlight_state"
COLOR_FILE="/tmp/current_kbd_color"

# Localization
LANG_CODE=$(echo $LANG | cut -d'_' -f1)
if [ "$LANG_CODE" == "pt" ]; then
    MSG_TITLE="Teclado"
    INT_SOFT="Suave"
    INT_STRONG="Forte"
    # Colors
    COLOR_RED="Vermelho"
    COLOR_GREEN="Verde"
    COLOR_BLUE="Azul"
    COLOR_UNKNOWN="Cor"
else
    MSG_TITLE="Keyboard"
    INT_SOFT="Soft"
    INT_STRONG="Strong"
    # Colors
    COLOR_RED="Red"
    COLOR_GREEN="Green"
    COLOR_BLUE="Blue"
    COLOR_UNKNOWN="Color"
fi

# Initial state checks
if [ ! -f "$COLOR_FILE" ]; then echo "00FF00" > "$COLOR_FILE"; fi
BASE_COLOR=$(cat "$COLOR_FILE")
if [ ! -f "$STATE_FILE" ]; then echo "1" > "$STATE_FILE"; fi
CURRENT=$(cat "$STATE_FILE")

# Dynamic Color Name Detection
case "$BASE_COLOR" in
    "FF0000") CURRENT_COLOR_NAME="$COLOR_RED" ;;
    "00FF00") CURRENT_COLOR_NAME="$COLOR_GREEN" ;;
    "0000FF") CURRENT_COLOR_NAME="$COLOR_BLUE" ;;
    *)         CURRENT_COLOR_NAME="$COLOR_UNKNOWN" ;;
esac

if [ "$CURRENT" == "1" ]; then
    # STRONG -> SOFT (30%)
    R=$(printf "%02X" $(( (16#${BASE_COLOR:0:2} * 30) / 100 )))
    G=$(printf "%02X" $(( (16#${BASE_COLOR:2:2} * 30) / 100 )))
    B=$(printf "%02X" $(( (16#${BASE_COLOR:4:2} * 30) / 100 )))
    FINAL_COLOR="${R}${G}${B}"
    echo "0" > "$STATE_FILE"
    MSG="${CURRENT_COLOR_NAME} ${INT_SOFT}"
else
    # SOFT -> STRONG (100%)
    FINAL_COLOR="$BASE_COLOR"
    echo "1" > "$STATE_FILE"
    MSG="${CURRENT_COLOR_NAME} ${INT_STRONG}"
fi

openrgb --noautoconnect -d "Dell G Series LED Controller" -c "$FINAL_COLOR" -m Static > /dev/null 2>&1

# Notification for Plasma/GNOME
USER_ID=$(id -u)
DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$USER_ID/bus" notify-send -a "Dell G15 System" "$MSG_TITLE" "$MSG"
