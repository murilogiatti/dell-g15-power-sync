#!/bin/bash
# Dell G15 Power & LED Sync Daemon - Refactored for Ubuntu 26.04
# Lightweight version: Syncs keyboard backlight (always white) with screen brightness.

# Configuration
POLL_INTERVAL=2
DEVICE_NAME="Dell G Series LED Controller"
BACKLIGHT_SYSFS_DIR="/sys/class/backlight"
BACKLIGHT_PATH="${BACKLIGHT_SYSFS_DIR}/amdgpu_bl2"

# State tracking
LAST_STATE=""

# Global variable to avoid subshells
BRIGHTNESS_PERC=100

resolve_backlight_path() {
    if [ -d "$BACKLIGHT_PATH" ]; then
        return 0
    fi
    local candidate
    for candidate in "$BACKLIGHT_SYSFS_DIR"/amdgpu_bl* "$BACKLIGHT_SYSFS_DIR"/*; do
        if [ -d "$candidate" ]; then
            BACKLIGHT_PATH="$candidate"
            return 0
        fi
    done
    return 1
}

update_screen_brightness_perc() {
    if resolve_backlight_path && [ -r "$BACKLIGHT_PATH/brightness" ] && [ -r "$BACKLIGHT_PATH/max_brightness" ]; then
        local curr max
        read -r curr < "$BACKLIGHT_PATH/brightness"
        read -r max < "$BACKLIGHT_PATH/max_brightness"
        if [ "${max:-0}" -gt 0 ] 2>/dev/null; then
            BRIGHTNESS_PERC=$(( (curr * 100) / max ))
        else
            BRIGHTNESS_PERC=100
        fi
    else
        BRIGHTNESS_PERC=100
    fi
}

apply_settings() {
    update_screen_brightness_perc
    local brightness=$BRIGHTNESS_PERC

    # Define Brightness Zone (5 levels: 10%, 30%, 50%, 75%, 100%)
    # Minimum 10% to avoid controller issues.
    local zone=100
    if [ "$brightness" -le 20 ]; then zone=10;
    elif [ "$brightness" -le 40 ]; then zone=30;
    elif [ "$brightness" -le 60 ]; then zone=50;
    elif [ "$brightness" -le 80 ]; then zone=75;
    fi

    # Check if anything changed
    local state_id="${zone}"
    if [ "$state_id" != "$LAST_STATE" ]; then
        # Calculate dimmed RGB for white (FFFFFF) - max limited to 230 to avoid hardware power limiter drop
        local val
        val=$(printf "%02X" $(( (230 * zone) / 100 )))
        local final_color="${val}${val}${val}"

        if openrgb --noautoconnect -d "$DEVICE_NAME" -c "$final_color" -m Static > /dev/null 2>&1; then
            LAST_STATE="$state_id"
        fi
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Dell G15 Daemon Started (v5 White Sync)"
    while true; do
        apply_settings
        sleep "$POLL_INTERVAL"
    done
fi
