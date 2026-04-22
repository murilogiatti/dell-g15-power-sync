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
A solução opera em quatro frentes técnicas:

1.  **Identificação do Hardware**: O controlador USB do teclado Dell G15 é identificado pelo OpenRGB como *Alienware LED Controller* (ID `1`).
2.  **Sincronização por Polling**: O monitor (`g15-watcher.sh`) verifica o estado do kernel a cada 2 segundos, garantindo estabilidade e baixo consumo.
3.  **Alternância de Brilho (kbd_toggle.sh)**: Como o firmware Dell limita o controle de brilho ACPI no Linux, este script emula dois níveis (100% e 30%) através de cálculos hexadecimais nos canais RGB.
4.  **Aritmética Hexadecimal**: Realiza o cálculo `(Cor Base * 0.3)` para manter a tonalidade correta mesmo em brilho reduzido.

### 📋 Requisitos
- **OpenRGB**: Para comunicação com o hardware.
- **power-profiles-daemon**: Para ler o estado de energia do sistema.

---

## 🇺🇸 English

### 🚀 Functionality
Syncs RGB keyboard colors with Linux power profiles (`power-profiles-daemon`).
- **Blue (Power Saver)**: Battery saving mode.
- **Green (Balanced)**: Everyday balanced use.
- **Red (Performance)**: Maximum performance (G-Mode).

### 🛠️ Technical Details & Operation
The solution operates on four technical fronts:

1.  **Hardware Identification**: The Dell G15 keyboard USB controller is detected as *Alienware LED Controller* (ID `1`).
2.  **Polling-based Sync**: The `g15-watcher.sh` monitor checks kernel state every 2 seconds for stability and low power impact.
3.  **Brightness Toggle (kbd_toggle.sh)**: Emulates two brightness levels (100% & 30%) by recalculating RGB hex values, bypassing ACPI firmware limitations on Linux.
4.  **Hex Math**: Performs `(Base Color * 0.3)` calculation to maintain correct hue even at low brightness.

---

## 📦 Instalação / Installation

```bash
git clone https://github.com/murilogiatti/dell-g15-power-sync.git
cd dell-g15-power-sync
chmod +x install.sh
./install.sh
```

### O que o instalador faz? / What does the installer do?
- **Scripts**: Copia `g15-sync.sh`, `g15-watcher.sh` e `kbd_toggle.sh` para `~/.local/bin/`.
- **Systemd Service**: Cria um serviço de usuário para início automático do monitor.
- **Udev Rules**: Opcionalmente permite acesso ao hardware sem `sudo`.
- **Desktop Entry**: Adiciona atalhos ao menu de apps para Ciclo de Energia e Alternância de Brilho.
