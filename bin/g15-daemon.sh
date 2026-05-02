#!/bin/bash
# Dell G15 Power & LED Sync Daemon - Refactored for Ubuntu 26.04
# Lightweight version: No external brightness dependencies.

# Configuration
POLL_INTERVAL=${POLL_INTERVAL:-2}
DEVICE_NAME=${DEVICE_NAME:-"Dell G Series LED Controller"}
BACKLIGHT_PATH=${BACKLIGHT_PATH:-"/sys/class/backlight/amdgpu_bl2"}

# Localization
LANG_CODE=$(echo "$LANG" | cut -d'_' -f1)
if [ "$LANG_CODE" == "pt" ]; then
    MSG_TITLE="Dell G15"
    MSG_PROFILE="Perfil"
    MSG_SYNCED="LEDs sincronizados"
    COLOR_RED="Vermelho"
    COLOR_GREEN="Verde"
    COLOR_BLUE="Azul"
else
    MSG_TITLE="Dell G15"
    MSG_PROFILE="Profile"
    MSG_SYNCED="LEDs synced"
    COLOR_RED="Red"
    COLOR_GREEN="Green"
    COLOR_BLUE="Blue"
fi

# State tracking
LAST_STATE=""
LAST_PROFILE=""

get_screen_brightness_perc() {
    if [ -d "$BACKLIGHT_PATH" ]; then
        local curr
        curr=$(cat "$BACKLIGHT_PATH/brightness")
        local max
        max=$(cat "$BACKLIGHT_PATH/max_brightness")
        echo $(( (curr * 100) / max ))
    else
        echo 100
    fi
}

apply_settings() {
    local profile
    profile=$(powerprofilesctl get)
    local brightness
    brightness=$(get_screen_brightness_perc)
    
    # Define Base Color
    local color="0000FF" # Default Blue (Power Save)
    [[ "$profile" == *"performance"* ]] && color="FF0000"
    [[ "$profile" == *"balanced"* ]] && color="00FF00"
    
    # Define Brightness Zone (0-30, 31-70, 71-100)
    local zone=100
    if [ "$brightness" -le 30 ]; then zone=30;
    elif [ "$brightness" -le 70 ]; then zone=70;
    fi

    # Check if anything changed
    local state_id="${profile}_${zone}"
    if [ "$state_id" != "$LAST_STATE" ]; then
        # Calculate dimmed RGB
        local r
        r=$(printf "%02X" $(( (16#${color:0:2} * zone) / 100 )))
        local g
        g=$(printf "%02X" $(( (16#${color:2:2} * zone) / 100 )))
        local b
        b=$(printf "%02X" $(( (16#${color:4:2} * zone) / 100 )))
        local final_color="${r}${g}${b}"
        
        openrgb --noautoconnect -d "$DEVICE_NAME" -c "$final_color" -m Static > /dev/null 2>&1
        
        # Define Color Name for Notification
        local color_name="$COLOR_BLUE"
        [[ "$color" == "FF0000" ]] && color_name="$COLOR_RED"
        [[ "$color" == "00FF00" ]] && color_name="$COLOR_GREEN"
        
        # Notify profile change
        if [ "$profile" != "$LAST_PROFILE" ]; then
            notify-send -t 1500 -a "$MSG_TITLE" "${MSG_PROFILE}: ${profile^}" "${MSG_SYNCED}: ${color_name}"
            LAST_PROFILE="$profile"
        fi
        LAST_STATE="$state_id"
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Dell G15 Daemon Started (v4 Simplified)"
    while true; do
        apply_settings
        sleep "$POLL_INTERVAL"
    done
fi
