# 💻 Dell G15 Power & LED Sync (v4)

<p align="center">
  <img src="https://img.shields.io/badge/Ubuntu-26.04-orange?style=for-the-badge&logo=ubuntu" />
  <img src="https://img.shields.io/badge/GNOME-50-blue?style=for-the-badge&logo=gnome" />
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Language-Bilingual-blue?style=for-the-badge" />
</p>

> **Transforme a iluminação do seu Dell G15 em uma extensão inteligente do seu sistema.**

---

## 🇧🇷 Português

### 💡 Por que este projeto existe?
Laptops Dell G15 são máquinas poderosas, mas no Linux, a integração do teclado RGB muitas vezes é esquecida. O **Dell G15 Power & LED Sync** resolve isso de forma elegante, eliminando a necessidade de softwares pesados ou ajustes manuais constantes. Ele faz com que o hardware "reaja" ao que você está fazendo.

### ✨ Funcionalidades Incríveis

*   **🎨 Sincronização Inteligente de Cores**: Seu teclado comunica visualmente o estado de energia do laptop.
    *   🔴 **Modo Performance**: O teclado incendeia em Vermelho, indicando que o hardware está pronto para força total.
    *   🟢 **Modo Equilibrado**: Um Verde suave para o uso diário e produtividade.
    *   🔵 **Modo Economia**: Azul profundo, sinalizando que o sistema está otimizando a bateria.
*   **🌙 Brilho Dinâmico (Smart Dimming)**: Chega de teclado ofuscando seus olhos no escuro. O script lê o brilho da sua tela em tempo real e ajusta a intensidade do teclado proporcionalmente em 3 zonas automáticas (30%, 70%, 100%).
*   **🚀 Performance "Zero-Impact"**: Escrito puramente em Bash, o daemon consome menos de 0,01% de CPU. Ele é independente, não depende de drivers proprietários pesados e usa caminhos nativos do kernel (`/sys/class/backlight`).
*   **🔔 Notificações Nativas**: Integra-se perfeitamente ao Centro de Notificações do GNOME para avisar quando o perfil e a cor foram alterados.

### 📦 Instalação Rápida
```bash
git clone https://github.com/murilogiatti/dell-g15-power-sync
cd dell-g15-power-sync
chmod +x install.sh
./install.sh
```

---

## 🇺🇸 English

### 💡 Why this project?
Dell G15 laptops are powerhouses, but on Linux, RGB integration is often overlooked. This project bridges that gap, making your keyboard backlight a smart extension of your OS. No more manual adjustments—your hardware finally "reacts" to your workflow.

### ✨ Key Features

*   **🎨 Intelligent Color Sync**: Your keyboard visually communicates the system's power state.
    *   🔴 **Performance Mode**: Fires up in Red, showing the system is ready for heavy tasks.
    *   🟢 **Balanced Mode**: A soothing Green for daily productivity.
    *   🔵 **Power Saver**: Deep Blue, signaling battery optimization is active.
*   **🌙 Smart Dynamic Brightness**: No more blinding lights in dark rooms. The script monitors your screen brightness in real-time and auto-dims the keyboard across 3 zones (30%, 70%, 100%).
*   **🚀 Zero-Impact Performance**: Pure Bash implementation. It consumes less than 0.01% CPU, bypassing heavy proprietary software by using native kernel paths (`/sys/class/backlight`).
*   **🔔 Native Notifications**: Seamlessly integrated with GNOME to keep you informed about profile and color shifts.

### 📦 Quick Start
```bash
git clone https://github.com/murilogiatti/dell-g15-power-sync
cd dell-g15-power-sync
chmod +x install.sh
./install.sh
```

---

## 🛠️ Tech Stack & Management / Gerenciamento
*   **Core**: Bash Scripting
*   **Engine**: OpenRGB (Hardware Control)
*   **Trigger**: Power-Profiles-Daemon (Native Linux Profiles)
*   **Monitoring**: Native Sysfs Backlight Interface

### 🔄 Auto-Update / Atualização Automática
O projeto agora inclui um mecanismo de atualização automática local via GitHub.
The project now includes a local auto-update mechanism via GitHub.
```bash
g15-update.sh
```

```bash
# Check service status / Ver status do serviço
systemctl --user status dell-g15-daemon.service

# Live logs / Logs em tempo real
journalctl --user -u dell-g15-daemon.service -f
```

---
<p align="center">
  Criado com ❤️ para a comunidade Linux por <b>Murilo Giatti</b>.
</p>
