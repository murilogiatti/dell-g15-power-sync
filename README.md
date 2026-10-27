<div align="center">
  <h1>🌌 Dell G15 Ambient Sync</h1>
  <p><i>Zero-dependency, event-driven keyboard backlight synchronizer for Dell G15 laptops on Linux.</i></p>
  <p><i>Sincronizador de iluminação de teclado orientado a eventos e sem dependências externas para Dell G15 no Linux.</i></p>

  [![CI](https://github.com/murilogiatti/dell-g15-power-sync/actions/workflows/test.yml/badge.svg)](https://github.com/murilogiatti/dell-g15-power-sync/actions/workflows/test.yml)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  ![Platform: Linux](https://img.shields.io/badge/Platform-Linux-blue.svg)

  <p>
    <a href="#english">🇺🇸 English (EN-US)</a> • <a href="#português">🇧🇷 Português (PT-BR)</a>
  </p>
</div>

---

<h2 id="english">🇺🇸 English (EN-US)</h2>

### Overview
**Dell G15 Ambient Sync** is an ultra-lightweight background daemon that automatically synchronizes your Dell G15 keyboard backlight intensity with your screen brightness.

Built from scratch with a clean **Data-Oriented Design (DOD)** architecture, it eliminates polling loops (`sleep`) and heavy third-party CLI tools (`openrgb`):
- **Direct USB HID Communication (No OpenRGB Required)**: Talks directly to the Alienware AW-ELC controller (`187c:0550` / `187c:0551`) via Linux `/dev/hidraw*` (`HIDIOCSFEATURE` ioctls) using only the Python 3 standard library. Automatically queries the controller's firmware zone table (`0x20 0x02`) to support all Dell G15 variants (`5511`, `5515`, `5520`, `5525`, `5530`, `5535`).
- **100% Event-Driven (Zero Polling)**: Listens directly to Linux kernel `AF_NETLINK` (`NETLINK_KOBJECT_UEVENT`) and `inotify` sysfs events. Consumes **0% CPU** while idle and reacts instantaneously with a **150ms debounce** when you adjust screen brightness.
- **Ready for Standard & Immutable Distros**: Works out of the box on **Ubuntu / Debian** and **Fedora Workstation / Kinoite / Silverblue (Atomic)** without `rpm-ostree` package layering, Flatpaks, or `pip` packages.

### ✨ Features
- **Calibrated Pure White (`#E6E6E6`)**: Locks the keyboard to a clean white capped at `230` (`#E6E6E6`) instead of `#FFFFFF` to prevent the hardware power limiter from dropping brightness.
- **Smart 5-Tier Sync + Hysteresis (±2%)**: Tracks `amdgpu_bl*` screen brightness with a ±2% deadband to prevent boundary flicker:
  - 🌑 **Screen Off (DPMS)** ➔ **0% Keyboard** *(Hardware Dimmer `0x26` at 100% — LEDs off)*
  - 🌙 **0–20% Screen** ➔ **10% Keyboard** (`#171717` — *Safe minimum floor while screen is active*)
  - 🌘 **21–40% Screen** ➔ **30% Keyboard** (`#454545`)
  - 🌗 **41–60% Screen** ➔ **50% Keyboard** (`#737373`)
  - 🌔 **61–80% Screen** ➔ **75% Keyboard** (`#ACACAC`)
  - 🌕 **81–100% Screen** ➔ **100% Keyboard** (`#E6E6E6`)
- **Suspend/Resume Auto-Recovery**: Detects `hidraw` USB re-enumeration upon waking from sleep and automatically restores your keyboard lighting.

### 🚀 Installation & Upgrade
The installer automatically cleans up any legacy services or scripts from older versions before installing:
```bash
git clone https://github.com/murilogiatti/dell-g15-power-sync.git
cd dell-g15-power-sync
./install.sh
```

### 🗑️ Uninstallation
```bash
./uninstall.sh
```

---

<h2 id="português">🇧🇷 Português (PT-BR)</h2>

### Visão Geral
O **Dell G15 Ambient Sync** é um daemon ultraleve em segundo plano que sincroniza automaticamente a intensidade dos LEDs do teclado do Dell G15 com o brilho da tela.

Construído do zero com arquitetura **Data-Oriented Design (DOD)**, ele elimina loops de polling (`sleep`) e a dependência de ferramentas externas pesadas (`openrgb`):
- **Comunicação USB HID Direta (Sem OpenRGB)**: Conversa diretamente com o controlador Alienware AW-ELC (`187c:0550` / `187c:0551`) via `/dev/hidraw*` (`ioctl HIDIOCSFEATURE`) usando apenas a biblioteca padrão do Python 3. Consulta automaticamente a tabela de zonas do firmware (`0x20 0x02`), suportando todas as variantes do Dell G15 (`5511`, `5515`, `5520`, `5525`, `5530`, `5535`).
- **100% Orientado a Eventos (Zero Polling)**: Escuta diretamente eventos `AF_NETLINK` (`NETLINK_KOBJECT_UEVENT`) e `inotify` do kernel Linux. Consome **0% de CPU** em repouso e reage instantaneamente com **debounce de 150ms** ao alterar o brilho da tela.
- **Compatível com Distros Tradicionais e Imutáveis**: Funciona nativamente no **Ubuntu / Debian** e no **Fedora Workstation / Kinoite / Silverblue (Atomic)** sem necessidade de *package layering* (`rpm-ostree`), Flatpaks ou pacotes `pip`.

### ✨ Funcionalidades
- **Branco Puro Calibrado (`#E6E6E6`)**: Mantém o teclado em branco estável limitado ao pico `230` (`#E6E6E6`) em vez de `#FFFFFF`, evitando quedas de luminosidade pelo limitador de energia do hardware.
- **Sincronização em 5 Níveis + Histerese (±2%)**: Acompanha o brilho da tela (`amdgpu_bl*`) com banda morta de ±2% nas fronteiras para evitar oscilações:
  - 🌑 **Tela Desligada (DPMS)** ➔ **0% Teclado** *(Dimmer de Hardware `0x26` em 100% — LEDs apagados)*
  - 🌙 **0–20% Tela** ➔ **10% Teclado** (`#171717` — *Piso mínimo seguro com a tela ligada*)
  - 🌘 **21–40% Tela** ➔ **30% Teclado** (`#454545`)
  - 🌗 **41–60% Tela** ➔ **50% Teclado** (`#737373`)
  - 🌔 **61–80% Tela** ➔ **75% Teclado** (`#ACACAC`)
  - 🌕 **81–100% Tela** ➔ **100% Teclado** (`#E6E6E6`)
- **Recuperação Automática Pós-Suspensão**: Detecta a reconexão USB `hidraw` ao acordar o notebook e reaplica o brilho calibrado automaticamente.

### 🚀 Instalação e Atualização
O instalador remove automaticamente quaisquer scripts ou serviços de versões antigas antes de instalar:
```bash
git clone https://github.com/murilogiatti/dell-g15-power-sync.git
cd dell-g15-power-sync
./install.sh
```

### 🗑️ Desinstalação
```bash
./uninstall.sh
```
