# Dell G15 Power & LED Sync (Linux)

Automatically synchronizes your keyboard backlight color with the system power profile on Dell G15 laptops. Optimized for **Dell G15 5515** and similar models with 4-Zone RGB keyboards.

---

## 🇧🇷 Português

### 🚀 Funcionalidade
Este projeto sincroniza as cores do teclado RGB com os perfis de energia do Linux (`power-profiles-daemon`). 
- **Azul (Power Saver)**: Economia de bateria.
- **Verde (Balanced)**: Uso cotidiano.
- **Vermelho (Performance)**: Desempenho máximo (G-Mode).

### 🛠️ Arquitetura Técnica
A solução é dividida em três camadas de software:

1.  **g15-sync.sh (O Core)**:
    - **Aritmética Hexadecimal**: Calcula cores em tempo real.
    - **Normalização de Brilho**: Se o brilho estiver em modo "suave", o script aplica um multiplicador de 0.3 nos canais R, G e B antes de enviar ao hardware, mantendo a consistência visual.
    - **Fonte da Verdade**: Sempre consulta o estado real do Kernel via `powerprofilesctl` antes de aplicar a cor.

2.  **g15-watcher.sh (O Monitor)**:
    - **Polling de Baixo Impacto**: Verifica o estado do sistema a cada 2 segundos. O impacto na CPU é virtualmente zero (<0.01%).
    - **Debounce**: Garante que o hardware só seja atualizado quando houver uma mudança real de estado, evitando chamadas desnecessárias ao barramento USB.

3.  **Systemd User Service**:
    - Gerencia o ciclo de vida do monitor. Garante que o processo seja reiniciado em caso de falha e que inicie automaticamente com a sessão gráfica.

---

## 🇺🇸 English

### 🚀 Functionality
Seamlessly syncs RGB keyboard colors with Linux power profiles (`power-profiles-daemon`).
- **Blue**: Power Saver Mode.
- **Green**: Balanced Mode.
- **Red**: Performance Mode.

### 🛠️ Technical Deep Dive
The solution is built on a three-layer architecture:

1.  **g15-sync.sh (The Logic Core)**:
    - **Hex Arithmetic**: Calculates RGB values on the fly.
    - **Brightness Normalization**: If "soft brightness" is active, it applies a 0.3 multiplier to R, G, and B channels before hardware transmission, ensuring visual consistency across profiles.
    - **Source of Truth**: Always queries the actual Kernel state via `powerprofilesctl` before painting the keyboard.

2.  **g15-watcher.sh (The Monitor)**:
    - **Low-Impact Polling**: Checks system state every 2 seconds. CPU impact is virtually zero (<0.01%).
    - **Debounce Logic**: Ensures hardware is only updated upon an actual state change, preventing redundant USB bus traffic.

3.  **Systemd User Service**:
    - Manages the process lifecycle. Ensures the monitor is restarted on failure and starts automatically with the graphical session.

---

### 📦 Installation / Instalação

1. **Requirements**: `openrgb`, `power-profiles-daemon`.
2. **Clone & Install**:
```bash
git clone https://github.com/YOUR_USERNAME/dell-g15-power-sync.git
cd dell-g15-power-sync
chmod +x install.sh
./install.sh
```

### 🛡️ Hardware Access (Udev)
The project includes a udev rule (`10-alienware.rules`) that allows the `openrgb` tool to access the Alienware LED Controller (USB IDs `187c:0550/0551`) without requiring root privileges. This makes the service safer and more integrated into the user session.

---

## Technical Flow / Fluxo Técnico
1. **Event**: User changes profile in KDE/GNOME menu.
2. **Detection**: `g15-watcher` notices the `powerprofilesctl` change.
3. **Processing**: `g15-sync` calculates the target RGB and brightness.
4. **Execution**: `openrgb` updates the 4-zone controller via USB.
5. **Final State**: Hardware LEDs reflect the actual System Power State.
