#!/bin/bash
# dell_g15_daemon.sh (Versão Sensível e Estável)
# Centraliza: Cores por Perfil + 3 Níveis de Brilho + G-Mode.

DEVICE_NAME="Dell G Series LED Controller"
POLL_INTERVAL=2
COLOR_FILE="/tmp/current_kbd_color"
LAST_PROFILE_FILE="/tmp/last_power_profile"
LAST_APPLIED_COLOR_FILE="/tmp/last_applied_color"
LOG_FILE="/tmp/dell_g15_daemon.log"

log_event() {
    echo "$(date '+%H:%M:%S') - $1" >> "$LOG_FILE"
}

apply_led() {
    local profile=$1
    local screen_perc=$2
    
    # 1. Definir Cor Base
    local base_color="00FF00"
    case "$profile" in
        *performance*) base_color="FF0000" ;;
        *balanced*)    base_color="00FF00" ;;
        *save*)        base_color="0000FF" ;;
        *)             base_color="0000FF" ;;
    esac
    echo "$base_color" > "$COLOR_FILE"

    # 2. Definir Nível conforme suas 3 faixas
    local k_level=100
    if [ "$screen_perc" -le 30 ]; then
        k_level=30
    elif [ "$screen_perc" -le 70 ]; then
        k_level=70
    else
        k_level=100
    fi

    # 3. Cálculo RGB
    local r g b final_color
    r=$(printf "%02X" $(( (16#${base_color:0:2} * k_level) / 100 )))
    g=$(printf "%02X" $(( (16#${base_color:2:2} * k_level) / 100 )))
    b=$(printf "%02X" $(( (16#${base_color:4:2} * k_level) / 100 )))
    final_color="${r}${g}${b}"

    # 4. Trava de Mudança
    local last_color=""
    [ -f "$LAST_APPLIED_COLOR_FILE" ] && last_color=$(cat "$LAST_APPLIED_COLOR_FILE")

    if [ "$final_color" != "$last_color" ]; then
        log_event "AÇÃO: Tela=$screen_perc%, Perfil=$profile -> Aplicando $final_color ($k_level%)"
        openrgb --noautoconnect -d "$DEVICE_NAME" -c "$final_color" -m Static > /dev/null 2>&1
        echo "$final_color" > "$LAST_APPLIED_COLOR_FILE"
    fi
}

# --- INÍCIO ---
echo "Master Daemon v3 Iniciado."
echo "" > "$LOG_FILE"
rm "$LAST_APPLIED_COLOR_FILE" 2>/dev/null

while true; do
    # Captura porcentagem exata da tela
    CUR_P=$(powerprofilesctl get | tr -d ' ')
    LAST_P=$(cat "$LAST_PROFILE_FILE" 2>/dev/null)
    
    # Método mais sensível para pegar a porcentagem
    PERC_B=$(brightnessctl -m | awk -F, '{print $4}' | tr -d '%')

    # Se a captura falhar por algum motivo, usa o cálculo manual
    if [ -z "$PERC_B" ]; then
        CUR_B=$(brightnessctl g)
        MAX_B=$(brightnessctl m)
        PERC_B=$(( (CUR_B * 100) / MAX_B ))
    fi

    apply_led "$CUR_P" "$PERC_B"

    if [ "$CUR_P" != "$LAST_P" ]; then
        echo "$CUR_P" > "$LAST_PROFILE_FILE"
        notify-send -t 2000 -a "Dell G15" "Perfil: ${CUR_P^}" "Modo dinâmico ativo." &
    fi

    sleep "$POLL_INTERVAL"
done
