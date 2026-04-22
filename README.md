# Dell G15 Power & LED Sync (Linux)

Automatically synchronizes your keyboard backlight color with the system power profile on Dell G15 laptops. Optimized for **Dell G15 5515** and similar models with 4-Zone RGB keyboards.

---

## 🇧🇷 Português

### 🚀 Funcionalidades
Este projeto sincroniza as cores do teclado RGB com os perfis de energia do sistema (`power-profiles-daemon`).
- **Azul (Power Saver)**: Modo economia de bateria.
- **Verde (Balanced)**: Equilíbrio para uso cotidiano.
- **Vermelho (Performance)**: Desempenho máximo (ativação do G-Mode).
- **Controle de Brilho**: Alterna entre 100% e 30% via software.

### 📋 Requisitos
- **OpenRGB**: Para comunicação com o hardware.
- **power-profiles-daemon**: Para ler o estado de energia do sistema.
- **libnotify**: Para notificações de sistema (`notify-send`).

### 📦 Gerenciamento

#### Instalação ou Atualização
```bash
make install
# OU
./install.sh
```

#### Desinstalação
```bash
make uninstall
# OU
./uninstall.sh
```

#### Atualizar do GitHub e Reinstalar
```bash
make update
```

---

## 🇺🇸 English

### 🚀 Features
Syncs RGB keyboard colors with Linux power profiles (`power-profiles-daemon`).
- **Blue (Power Saver)**: Battery saving mode.
- **Green (Balanced)**: Everyday balanced use.
- **Red (Performance)**: Maximum performance (G-Mode).
- **Brightness Control**: Toggle between 100% and 30% via software.

### 📋 Requirements
- **OpenRGB**: For hardware communication.
- **power-profiles-daemon**: To read system power states.
- **libnotify**: For system notifications (`notify-send`).

### 📦 Management

#### Installation or Update
```bash
make install
# OR
./install.sh
```

#### Uninstallation
```bash
make uninstall
# OR
./uninstall.sh
```

#### Update from GitHub and Reinstall
```bash
make update
```

---

## 💡 Dica de Produtividade / Productivity Tip

**PT:** É possível fixar os atalhos no seu Gerenciador de Tarefas e utilizar as teclas de atalho `Super+1` e `Super+2` para alternar rapidamente entre perfis e brilho, como na foto de exemplo:

**EN:** You can pin the shortcuts to your Task Manager and use `Super+1` and `Super+2` hotkeys to quickly switch between profiles and brightness, as shown in the example photo:

![Atalhos no Gerenciador de Tarefas](atalhos_gerenciador_tarefas_maior.png)

---

### 🛠️ Detalhes Técnicos / Technical Details

1.  **Hardware**:
    - **PT:** Identificado como *Alienware LED Controller* (ID `1`).
    - **EN:** Identified as *Alienware LED Controller* (ID `1`).
2.  **Sync**:
    - **PT:** `g15-watcher.sh` monitora o kernel a cada 2s.
    - **EN:** `g15-watcher.sh` monitors the kernel every 2s.
3.  **Brightness**:
    - **PT:** `kbd_toggle.sh` emula níveis de brilho via cálculos hexadecimais (0.3x), contornando limitações de ACPI.
    - **EN:** `kbd_toggle.sh` emulates brightness levels via hexadecimal math (0.3x), bypassing ACPI limitations.
