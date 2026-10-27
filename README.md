<div align="center">
  <h1>🌌 Dell G15 Ambient Sync</h1>
  <p><i>Zero-dependency, event-driven keyboard backlight synchronizer for Dell G15 laptops on Linux.</i></p>

  [![CI](https://github.com/murilogiatti/dell-g15-power-sync/actions/workflows/test.yml/badge.svg)](https://github.com/murilogiatti/dell-g15-power-sync/actions/workflows/test.yml)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  ![Platform: Linux](https://img.shields.io/badge/Platform-Linux-blue.svg)

  <p>
    <a href="#english">English</a> • <a href="#português">Português</a>
  </p>
</div>

---

<h2 id="english">🇬🇧 English</h2>

### Why This Exists
Traditional scripts for the Dell G15 rely on `while true; sleep 2` polling loops and spawn the heavy `openrgb` CLI on every change—loading 40+ shared libraries and sending 34 redundant USB packets due to an unmapped zone count quirk on G15 controllers (`187c:0550` / `187c:0551`).

**Dell G15 Ambient Sync** is built from scratch with a clean, **Data-Oriented** architecture:
- **Zero External Dependencies (No OpenRGB Required)**: Talks directly to the Alienware AW-ELC USB controller via Linux `/dev/hidraw*` (`HIDIOCSFEATURE` ioctls) using only the native Python 3 standard library. Updates all 4 keyboard zones in a single batch (~240ms instead of 3–19s).
- **100% Event-Driven (Zero Polling)**: Listens directly to the Linux kernel's `AF_NETLINK` (`NETLINK_KOBJECT_UEVENT`) socket. Uses **0% CPU** and spawns zero child processes while idle, reacting instantaneously with a 150ms debounce when you adjust screen brightness.
- **Immutable Distro Ready**: Works out of the box on **Fedora Kinoite / Silverblue (Atomic)** and **Ubuntu / Debian** without `rpm-ostree` package layering, Flatpaks, or `pip`.

### ✨ Features
- **Calibrated Pure White (`#E6E6E6`)**: Caps peak white at `230` (`#E6E6E6`) instead of `#FFFFFF` to prevent the hardware power limiter from dropping brightness.
- **Smart 5-Tier Sync + True Screen-Off**: Tracks `amdgpu_bl*` brightness with **±2% hysteresis** (preventing boundary flicker) and uses the native hardware dimmer (`0x26`) to cleanly turn off the LEDs when your screen blanks:
  - 🌑 **Screen Off / 0%** ➔ **0% Keyboard** *(Hardware Dim 100% — LEDs off)*
  - 🌙 **1–20% Screen** ➔ **10% Keyboard** (`#171717`)
  - 🌘 **21–40% Screen** ➔ **30% Keyboard** (`#454545`)
  - 🌗 **41–60% Screen** ➔ **50% Keyboard** (`#737373`)
  - 🌔 **61–80% Screen** ➔ **75% Keyboard** (`#ACACAC`)
  - 🌕 **81–100% Screen** ➔ **100% Keyboard** (`#E6E6E6`)
- **Suspend/Resume Auto-Recovery**: Automatically detects USB `hidraw` re-enumeration on wake and restores your keyboard lighting.

### 🚀 Installation & Upgrade
Running `./install.sh` automatically purges any legacy files/timers from older versions before installing:
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

<h2 id="português">🇧🇷 Português</h2>

### Por Que Este Projeto Existe
Scripts tradicionais para o Dell G15 usam loops de polling (`while true; sleep 2`) e invocam o binário pesado do `openrgb` a cada mudança — carregando mais de 40 bibliotecas dinâmicas e enviando 34 pacotes USB redundantes por conta de um bug de contagem de zonas nos controladores do G15 (`187c:0550` / `187c:0551`).

O **Dell G15 Ambient Sync** foi construído do zero com uma arquitetura limpa e orientada a dados (**DOD**):
- **Zero Dependências Externas (Sem OpenRGB)**: Comunica-se diretamente com o controlador USB Alienware AW-ELC via `/dev/hidraw*` (`ioctl HIDIOCSFEATURE`) usando apenas a biblioteca padrão do Python 3. Atualiza as 4 zonas do teclado em um único lote (~240ms em vez de 3–19s).
- **100% Orientado a Eventos (Zero Polling)**: Escuta diretamente o socket `AF_NETLINK` (`NETLINK_KOBJECT_UEVENT`) do kernel Linux. Consome **0% de CPU** e não cria processos filhos em repouso, reagindo instantaneamente (com debounce de 150ms) ao ajustar o brilho da tela.
- **Pronto para Distros Imutáveis**: Funciona nativamente no **Fedora Kinoite / Silverblue (Atomic)** e no **Ubuntu / Debian** sem precisar de *package layering* (`rpm-ostree`), Flatpaks ou `pip`.

### ✨ Funcionalidades
- **Branco Puro Calibrado (`#E6E6E6`)**: Limita o pico de branco em `230` (`#E6E6E6`) em vez de `#FFFFFF`, evitando quedas de tensão pelo limitador de energia do hardware.
- **Sincronização em 5 Níveis + Desligamento Real**: Monitora o brilho da tela (`amdgpu_bl*`) com **histerese de ±2%** (evitando efeito pisca-pisca nas fronteiras) e usa o dimmer nativo de hardware (`0x26`) para apagar os LEDs com segurança quando o monitor desliga:
  - 🌑 **Tela Apagada / 0%** ➔ **0% Teclado** *(Dimmer de Hardware em 100% — LEDs apagados)*
  - 🌙 **1–20% Tela** ➔ **10% Teclado** (`#171717`)
  - 🌘 **21–40% Tela** ➔ **30% Teclado** (`#454545`)
  - 🌗 **41–60% Tela** ➔ **50% Teclado** (`#737373`)
  - 🌔 **61–80% Tela** ➔ **75% Teclado** (`#ACACAC`)
  - 🌕 **81–100% Tela** ➔ **100% Teclado** (`#E6E6E6`)
- **Recuperação Automática Pós-Suspensão**: Detecta a reconexão USB `hidraw` ao acordar o notebook e restaura a iluminação automaticamente.

### 🚀 Instalação e Atualização
O comando `./install.sh` limpa automaticamente quaisquer arquivos ou serviços de versões antigas antes de instalar:
```bash
git clone https://github.com/murilogiatti/dell-g15-power-sync.git
cd dell-g15-power-sync
./install.sh
```

### 🗑️ Desinstalação
```bash
./uninstall.sh
```
