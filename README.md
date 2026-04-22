# Dell G15 Power & LED Sync (Linux)

Automatically synchronizes your keyboard backlight color with the system power profile on Dell G15 laptops. Optimized for **Dell G15 5515** and similar models with 4-Zone RGB keyboards.

---

## 🇧🇷 Português

### 🚀 Funcionalidade
Este projeto resolve a falta de integração nativa no Linux para o controle de energia e LEDs do Dell G15. Ele sincroniza as cores do teclado RGB com os perfis de energia do sistema (`power-profiles-daemon`).
- **Azul (Power Saver)**: Modo economia de bateria.
- **Verde (Balanced)**: Equilíbrio para uso cotidiano.
- **Vermelho (Performance)**: Desempenho máximo (ativação do G-Mode).

### 🛠️ Detalhes Técnicos e Funcionamento
A solução foi desenhada para ser leve e resiliente, operando em três frentes:

1.  **Identificação do Hardware**: O script utiliza o identificador fixo do dispositivo no OpenRGB (geralmente ID `1`, correspondente ao *Alienware LED Controller*). Isso é necessário porque o controlador USB do teclado Dell G15 é tecnicamente um dispositivo Alienware.
2.  **Sincronização por Polling**: O monitor (`g15-watcher.sh`) verifica o estado do kernel a cada 2 segundos. Optamos por esta abordagem em vez de sinais DBus brutos por ser mais estável entre diferentes versões do KDE Plasma e GNOME, garantindo que o LED nunca fique "preso" em uma cor errada.
3.  **Aritmética Hexadecimal e Brilho**: O script `g15-sync.sh` realiza cálculos hexadecimais para reduzir a intensidade dos canais R, G e B quando o modo de brilho suave está ativo, garantindo consistência visual.

### 📋 Requisitos
- **OpenRGB**: Para comunicação com o hardware.
- **power-profiles-daemon**: Para ler o estado de energia do sistema.
- **Sessão Gráfica**: KDE Plasma, GNOME ou qualquer ambiente que utilize `power-profiles-daemon`.

---

## 🇺🇸 English

### 🚀 Functionality
Seamlessly syncs RGB keyboard colors with Linux power profiles (`power-profiles-daemon`).
- **Blue**: Power Saver Mode.
- **Green**: Balanced Mode.
- **Red**: Performance Mode.

### 🛠️ Technical Deep Dive
1.  **Hardware ID**: Uses OpenRGB Device ID `1` (Alienware LED Controller), which is the standard for Dell G15 keyboards.
2.  **Robust Polling**: The `g15-watcher.sh` checks the system state every 2 seconds. This ensures compatibility across different desktop environments where DBus signals might behave inconsistently.
3.  **Hex Math & Dimming**: `g15-sync.sh` performs real-time hexadecimal calculations to scale RGB values for "soft brightness" modes.

---

## 📦 Instalação / Installation

```bash
git clone https://github.com/murilogiatti/dell-g15-power-sync.git
cd dell-g15-power-sync
chmod +x install.sh
./install.sh
```

### O que o instalador faz? / What does the installer do?
- **Scripts**: Copia os binários para `~/.local/bin/`.
- **Systemd Service**: Cria e ativa um serviço de usuário que inicia o monitor automaticamente no login.
- **Udev Rules**: Opcionalmente, instala regras para permitir acesso ao hardware sem `sudo`.
- **Menu/Desktop**: O instalador **não** cria um ícone no menu iniciar por padrão, pois o objetivo é ser um serviço invisível de background. No entanto, o comando `g15-sync.sh` (sem argumentos) pode ser vinculado a qualquer atalho de teclado global para ciclar perfis manualmente.

---

## Technical Flow / Fluxo Técnico
1. **Event**: User changes profile in Desktop UI.
2. **Detection**: `g15-watcher` reads the state from `powerprofilesctl`.
3. **Execution**: `openrgb` updates the Alienware controller via USB.
