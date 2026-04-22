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

1.  **Identificação do Hardware**: O script utiliza o identificador fixo do dispositivo no OpenRGB (ID `1`, correspondente ao *Alienware LED Controller*). O controlador USB do teclado Dell G15 é tecnicamente um hardware Alienware.
2.  **Sincronização por Polling**: O monitor (`g15-watcher.sh`) verifica o estado do kernel a cada 2 segundos. Esta abordagem é mais estável entre diferentes versões de ambientes gráficos (KDE/GNOME) que sinais DBus.
3.  **Aritmética Hexadecimal e Brilho**: Realiza cálculos hexadecimais para reduzir a intensidade dos canais R, G e B quando o brilho suave está ativo, mantendo a consistência visual.

### 📋 Requisitos
- **OpenRGB**: Para comunicação com o hardware.
- **power-profiles-daemon**: Para ler o estado de energia do sistema.

---

## 🇺🇸 English

### 🚀 Functionality
This project provides the missing native integration for Dell G15 power profiles and RGB LEDs on Linux. It syncs the keyboard colors with the system power profiles (`power-profiles-daemon`).
- **Blue (Power Saver)**: Battery saving mode.
- **Green (Balanced)**: Everyday balanced use.
- **Red (Performance)**: Maximum performance (G-Mode activation).

### 🛠️ Technical Details & Operation
The solution is designed to be lightweight and resilient, operating on three fronts:

1.  **Hardware Identification**: The script uses a fixed device ID in OpenRGB (ID `1`, corresponding to the *Alienware LED Controller*). The Dell G15 keyboard USB controller is technically Alienware hardware.
2.  **Polling-based Sync**: The monitor (`g15-watcher.sh`) checks the kernel state every 2 seconds. This approach is more stable across different desktop environments (KDE/GNOME) than raw DBus signals.
3.  **Hex Math & Brightness**: It performs real-time hexadecimal calculations to scale down R, G, and B channels when soft brightness is active, ensuring visual consistency.

### 📋 Requirements
- **OpenRGB**: For hardware communication.
- **power-profiles-daemon**: To read the system power state.

---

## 📦 Instalação / Installation

```bash
git clone https://github.com/murilogiatti/dell-g15-power-sync.git
cd dell-g15-power-sync
chmod +x install.sh
./install.sh
```

### O que o instalador faz? / What does the installer do?
- **Scripts**: Copia os binários para `~/.local/bin/`. / Copies binaries to `~/.local/bin/`.
- **Systemd Service**: Cria um serviço de usuário para início automático. / Creates a user service for autostart.
- **Udev Rules**: Opcionalmente permite acesso sem sudo. / Optionally allows non-sudo hardware access.
- **Desktop Entry**: Adiciona um atalho ao menu de apps para ciclar perfis. / Adds an app menu shortcut to cycle profiles.
