#!/bin/bash
# Dell G15 Hardware Script - Energy & LED Sync
# Dynamic logic for G-Mode and Power Profiles

TARGET="$1"
COLOR_FILE="/tmp/current_kbd_color"
STATE_FILE="/tmp/kbd_backlight_state"

# Localization
LANG_CODE=$(echo $LANG | cut -d'_' -f1)
if [ "$LANG_CODE" == "pt" ]; then
    MSG_TITLE="Perfil de Energia"
else
    MSG_TITLE="Power Profile"
fi

# 1. Cycle logic if no target provided
if [ -z "$TARGET" ]; then
    CURRENT=$(/usr/bin/powerprofilesctl get)
    case "$CURRENT" in
        *power-save*) NEXT="balanced" ;;
        *balanced*)    NEXT="performance" ;;
        *)             NEXT="power-saver" ;;
    esac
    /usr/bin/powerprofilesctl set "$NEXT"
    TARGET="$NEXT"
fi

# 2. Get actual profile
ACTUAL=$(/usr/bin/powerprofilesctl get | tr -d ' ')

# 3. Define color based on profile
case "$ACTUAL" in
    *performance*) COLOR="FF0000" ;;
    *balanced*)    COLOR="00FF00" ;;
    *)             COLOR="0000FF" ;;
esac
echo "$COLOR" > "$COLOR_FILE"

# 4. Soft Brightness Logic
FINAL_COLOR="$COLOR"
if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE")" == "0" ]; then
    R=$(printf "%02X" $(( (16#${COLOR:0:2} * 30) / 100 )))
    G=$(printf "%02X" $(( (16#${COLOR:2:2} * 30) / 100 )))
    B=$(printf "%02X" $(( (16#${COLOR:4:2} * 30) / 100 )))
    FINAL_COLOR="${R}${G}${B}"
fi

# 5. Apply to hardware
/usr/bin/openrgb --noautoconnect -d 1 -c "$FINAL_COLOR" -m Static > /dev/null 2>&1

# 6. G-Mode & Notifications
GMODE_STATUS=""
if [[ "$ACTUAL" == *"performance"* ]]; then
    # Check if G-Mode is active via platform_profile
    if grep -q "performance" /sys/firmware/acpi/platform_profile 2>/dev/null || \
       grep -q "performance" /sys/devices/platform/alienware-wmi/platform_profile 2>/dev/null || \
       grep -q "performance" /sys/class/hwmon/hwmon*/device/platform-profile 2>/dev/null; then
        
        MAX_FAN=$(sensors 2>/dev/null | grep -i "RPM" | awk '{print $3}' | sort -nr | head -n 1)
        GMODE_STATUS=" (G-Mode ON 🚀 ${MAX_FAN} RPM)"
    else
        GMODE_STATUS=" (G-Mode OFF)"
    fi
fi

# Notification
USER_ID=$(id -u)
DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$USER_ID/bus" notify-send -a "Dell G15 System" "$MSG_TITLE" "${ACTUAL^}${GMODE_STATUS}"
