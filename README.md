# Dell G15 Power & LED Sync (v4)

[Português] | [English]

---

## 🇧🇷 Português

Este projeto automatiza a sincronização do hardware do **Dell G15** com o sistema operacional, otimizado para **Ubuntu 26.04+ (GNOME 50+)**.

### 🚀 Funcionalidades
- **Sincronização de Cor**: 🔴 Desempenho, 🟢 Equilibrado, 🔵 Economia.
- **Brilho Dinâmico**: Sincroniza o teclado com a tela (3 níveis automáticos).
- **Leve e Nativo**: Sem dependências pesadas, integrado ao systemd.

### 📦 Instalação
```bash
chmod +x install.sh
./install.sh
```

---

## 🇺🇸 English

This project automates **Dell G15** hardware synchronization with the OS, optimized for **Ubuntu 26.04+ (GNOME 50+)**.

### 🚀 Features
- **Color Sync**: 🔴 Performance, 🟢 Balanced, 🔵 Power Saver.
- **Dynamic Brightness**: Syncs keyboard backlight with the screen (3 automatic levels).
- **Lightweight & Native**: No heavy dependencies, systemd integrated.

### 📦 Installation
```bash
chmod +x install.sh
./install.sh
```

---

## 🛠️ Management / Gerenciamento
```bash
# Status
systemctl --user status dell-g15-daemon.service

# Logs
journalctl --user -u dell-g15-daemon.service -f
```
