<div align="center">
  <h1>🌌 Dell G15 Ambient Sync</h1>
  <p><i>A minimalist, elegant, and intelligent keyboard backlight synchronizer for Dell G15 laptops on Linux.</i></p>
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Platform: Linux](https://img.shields.io/badge/Platform-Linux-blue.svg)]()
  
  <p>
    <a href="#english">English</a> • <a href="#português">Português</a>
  </p>
</div>

---

<h2 id="english">🇬🇧 English</h2>

### The Concept
Why manually adjust your keyboard backlight when your system can do it for you? 
**Dell G15 Ambient Sync** is a lightweight, invisible daemon designed to seamlessly bridge your screen's brightness with your keyboard's illumination. 

It keeps your aesthetic clean and consistent by locking the LED color to a pristine, pure white (`#FFFFFF`) and dynamically scaling its intensity across 5 carefully tuned levels based on your monitor's brightness. 

*No bloated GUIs. No annoying popups. Just pure ambient harmony.*

### ✨ Features
- **Pure White Aesthetic**: Locks the keyboard to 100% white (`FFFFFF`) for a clean, professional look.
- **Dynamic 5-Tier Sync**: Intelligently tracks your `amdgpu_bl2` screen brightness and maps it to five safe, visible zones:
  - 🌙 0-20% Screen ➔ **10% Keyboard** *(Safe minimum to prevent controller lockups)*
  - 🌘 21-40% Screen ➔ **30% Keyboard**
  - 🌗 41-60% Screen ➔ **50% Keyboard**
  - 🌔 61-80% Screen ➔ **75% Keyboard**
  - 🌕 81-100% Screen ➔ **100% Keyboard**
- **Zero Distractions**: Operates completely silently in the background as a user-level Systemd service.

### 🛠️ Prerequisites
- `openrgb` (must be installed and successfully detecting your Dell G Series LED Controller).
- Supported environment: Ubuntu/Debian-based distributions (tested on Ubuntu 26.04).

### 🚀 Installation
```bash
git clone https://github.com/murilo/dell-g15-power-sync.git
cd dell-g15-power-sync
./install.sh
```
*Note: The installer will prompt for `sudo` to configure Udev rules for OpenRGB hardware access.*

### 🔄 Migrating from Legacy Versions
If you used the older version of this script (the one with colored power profiles and desktop notifications), simply run the update script to cleanly purge the legacy files before installing the new minimalist version:
```bash
./update.sh
```

### 🗑️ Uninstallation
To completely remove the daemon and all its services:
```bash
./uninstall.sh
```

---

<h2 id="português">🇧🇷 Português</h2>

### O Conceito
Por que ajustar manualmente a luz do seu teclado quando o seu sistema pode fazer isso por você?
O **Dell G15 Ambient Sync** é um daemon levíssimo e invisível, criado para sincronizar perfeitamente o brilho da sua tela com a iluminação do teclado.

Ele mantém sua estética limpa e consistente, fixando a cor dos LEDs em um branco puro (`#FFFFFF`) e ajustando dinamicamente a intensidade em 5 níveis cuidadosamente calibrados, acompanhando o brilho do seu monitor.

*Sem interfaces pesadas. Sem notificações irritantes. Apenas harmonia de ambiente.*

### ✨ Funcionalidades
- **Estética Branco Puro**: Trava o teclado em 100% branco (`FFFFFF`) para um visual limpo e profissional.
- **Sincronização Dinâmica em 5 Níveis**: Acompanha de forma inteligente o brilho da tela (`amdgpu_bl2`) e mapeia para cinco zonas seguras:
  - 🌙 0-20% Tela ➔ **10% Teclado** *(Mínimo seguro para evitar travamentos do controlador)*
  - 🌘 21-40% Tela ➔ **30% Teclado**
  - 🌗 41-60% Tela ➔ **50% Teclado**
  - 🌔 61-80% Tela ➔ **75% Teclado**
  - 🌕 81-100% Tela ➔ **100% Teclado**
- **Zero Distrações**: Opera de forma totalmente silenciosa no plano de fundo como um serviço Systemd local.

### 🛠️ Pré-requisitos
- `openrgb` (deve estar instalado e detectando com sucesso o Controlador de LED Dell G Series).
- Ambiente suportado: Distribuições baseadas em Ubuntu/Debian (testado no Ubuntu 26.04).

### 🚀 Instalação
```bash
git clone https://github.com/murilo/dell-g15-power-sync.git
cd dell-g15-power-sync
./install.sh
```
*Nota: O instalador solicitará `sudo` para configurar as regras do Udev e garantir o acesso do OpenRGB ao hardware.*

### 🔄 Atualizando da Versão Antiga (Legada)
Se você utilizava a versão mais antiga deste script (aquela com perfis de energia coloridos e notificações na área de trabalho), basta rodar o script de atualização para limpar completamente os arquivos antigos antes de instalar a nova versão minimalista:
```bash
./update.sh
```

### 🗑️ Desinstalação
Para remover completamente o daemon e todos os seus serviços:
```bash
./uninstall.sh
```
