# Dell G15 Power & LED Sync (Linux)

Automatically synchronizes your keyboard backlight color with the system power profile and screen brightness on Dell G15 laptops. Optimized for **Dell G15** series (5510, 5511, 5515, 5520+) with 4-Zone RGB keyboards.

---

## 🇧🇷 Português

### 🚀 Funcionalidades
- **Sincronização de Cor**: Altera o RGB baseado no perfil ativo (`performance`, `balanced`, `power-saver`).
- **Brilho Dinâmico Inteligente**: Sincroniza o brilho do teclado com a tela em 3 níveis automáticos.
- **Detecção de G-Mode**: Identifica se o Game Mode está ativo via hardware.
- **Monitor de Fans**: Exibe a rotação (RPM) das ventoinhas nas notificações.
- **Daemon Integrado**: Um único serviço gerencia tudo de forma estável e sem conflitos.

### 📊 Lógica de Funcionamento

| Componente | Regra / Comportamento |
| :--- | :--- |
| **Perfil Performance** | LED **Vermelho** (`FF0000`) |
| **Perfil Balanced** | LED **Verde** (`00FF00`) |
| **Perfil Power Saver** | LED **Azul** (`0000FF`) |
| **Brilho da Tela 0-30%** | Teclado em **30%** (Garante visibilidade) |
| **Brilho da Tela 31-70%** | Teclado em **70%** |
| **Brilho da Tela 71-100%** | Teclado em **100%** |

### 🛠️ Gerenciamento (Systemd)
O sistema roda como um serviço de usuário. Comandos úteis:
```bash
systemctl --user status dell-g15-daemon.service  # Ver status
systemctl --user restart dell-g15-daemon.service # Reiniciar
systemctl --user stop dell-g15-daemon.service    # Parar
journalctl --user -u dell-g15-daemon.service -f  # Ver logs em tempo real
```

---

## 🇺🇸 English

### 🚀 Features
- **Color Sync**: Changes RGB based on active profile (`performance`, `balanced`, `power-saver`).
- **Smart Dynamic Brightness**: Syncs keyboard backlight with screen in 3 automatic levels.
- **G-Mode Detection**: Identifies if Game Mode is active via hardware.
- **Fan Monitor**: Displays fan speed (RPM) in notifications.
- **Integrated Daemon**: A single service manages everything stably without conflicts.

### 📊 System Logic

| Component | Rule / Behavior |
| :--- | :--- |
| **Performance Profile** | **Red** LED (`FF0000`) |
| **Balanced Profile** | **Green** LED (`00FF00`) |
| **Power Saver Profile** | **Blue** LED (`0000FF`) |
| **Screen Brightness 0-30%** | Keyboard at **30%** (Ensures visibility) |
| **Screen Brightness 31-70%** | Keyboard at **70%** |
| **Screen Brightness 71-100%** | Keyboard at **100%** |

### 🛠️ Management (Systemd)
The system runs as a user service. Useful commands:
```bash
systemctl --user status dell-g15-daemon.service  # Check status
systemctl --user restart dell-g15-daemon.service # Restart
systemctl --user stop dell-g15-daemon.service    # Stop
journalctl --user -u dell-g15-daemon.service -f  # Real-time logs
```

---

## 📋 Requisitos / Requirements
- **OpenRGB**: Hardware control.
- **brightnessctl**: Screen brightness reading.
- **power-profiles-daemon**: Power profile management.
- **lm_sensors**: Fan speed reading (`sensors`).

## 📦 Instalação / Installation

**PT: Opção 1 (Via Makefile):**
```bash
make install    # Instalar ou Atualizar
make uninstall  # Remover
```

**PT: Opção 2 (Script Direto):**
```bash
chmod +x install.sh
./install.sh
```

---

**EN: Option 1 (Via Makefile):**
```bash
make install    # Install or Update
make uninstall  # Remove
```

**EN: Option 2 (Direct Script):**
```bash
chmod +x install.sh
./install.sh
```

---
*Configured with hardware stability in mind: 2s polling interval and flicker-free logic.*
