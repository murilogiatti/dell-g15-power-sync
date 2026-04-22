# Dell G15 Power & LED Sync (Linux)

Automatically synchronizes your keyboard backlight color with the system power profile on Dell G15 laptops. Optimized for **Dell G15** series (5510, 5511, 5515, 5520+) with 4-Zone RGB keyboards.

---

## 🇧🇷 Português

### 🚀 Funcionalidades
- **Sincronização de Cor**: Altera o RGB baseado no perfil (`power-profiles-daemon`).
- **Detecção de G-Mode**: Identifica se o Game Mode está ativo no hardware via driver `alienware-wmi`.
- **Monitor de Fans**: Exibe a rotação (RPM) das ventoinhas nas notificações de Performance.
- **Bilingue**: Notificações automáticas em PT-BR ou EN baseado no sistema.
- **Controle de Brilho**: Alterna entre 100% e 30% (suave) via software.

### 📋 Requisitos
- **OpenRGB**: Para controle do hardware.
- **alienware-wmi**: Driver do kernel para G-Mode (nativo em distros modernas).
- **lm_sensors**: Para leitura das ventoinhas (`sensors`).
- **libnotify**: Para notificações (`notify-send`).

---

## 🇺🇸 English

### 🚀 Features
- **Color Sync**: Changes RGB based on profile (`power-profiles-daemon`).
- **G-Mode Detection**: Identifies if Game Mode is active via `alienware-wmi` driver.
- **Fan Monitor**: Displays fan speed (RPM) in Performance notifications.
- **Bilingual**: Automatic PT-BR or EN notifications based on system locale.
- **Brightness Control**: Software-based toggle between 100% and 30% (soft).

### 📋 Requirements
- **OpenRGB**: For hardware control.
- **alienware-wmi**: Kernel driver for G-Mode (native in modern distros).
- **lm_sensors**: For fan speed reading (`sensors`).
- **libnotify**: For notifications (`notify-send`).

---

## 📦 Gerenciamento / Management

```bash
make install    # Instalar ou Atualizar / Install or Update
make uninstall  # Remover / Remove
```

---

## 💡 Dica de Produtividade / Productivity Tip

**PT:** É possível fixar os atalhos no seu Gerenciador de Tarefas e utilizar as teclas de atalho `Super+1` e `Super+2` para alternar rapidamente entre perfis e brilho, como na foto de exemplo:

**EN:** You can pin the shortcuts to your Task Manager and use `Super+1` and `Super+2` hotkeys to quickly switch between profiles and brightness, as shown in the example photo:

![Atalhos no Gerenciador de Tarefas](atalhos_gerenciador_tarefas_media.png)

---

### 🛠️ Detalhes Técnicos / Technical Details

1.  **G-Mode**:
    - **PT:** Detectado via `platform_profile` do ACPI ou Alienware WMI.
    - **EN:** Detected via ACPI or Alienware WMI `platform_profile`.
2.  **Performance Notification**:
    - **PT:** Exibe "G-Mode ON" e a maior RPM atual se o modo turbo estiver ativo.
    - **EN:** Displays "G-Mode ON" and the current max RPM if turbo mode is active.
3.  **Brightness**:
    - **PT:** Emula níveis de brilho via cálculos hexadecimais (0.3x), contornando limitações de ACPI.
    - **EN:** Emulates brightness levels via hexadecimal math (0.3x), bypassing ACPI limitations.
