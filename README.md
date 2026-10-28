<div align="center"><img src="assets/banner.svg" alt="Dell G15 Ambient Sync" width="100%"/></div>

# Dell G15 Ambient Sync & Control Center

[Português](#português) · [English](#english)

## Português

Controla a iluminação de controladores Alienware AW-ELC USB `187c:0550` / `187c:0551` no Linux. O daemon usa somente a biblioteca padrão do Python 3. O launcher escolhe GTK4/Libadwaita no GNOME e PyQt6/QtQuick/Kirigami no KDE Plasma, importando somente o toolkit escolhido.

### Instalação somente no usuário

```bash
./bin/g15-tray --print-backend
./bin/g15-tray --check-dependencies
./install.sh
```

O instalador verifica os componentes existentes antes de interromper serviços. Não instala pacotes, não usa privilégios administrativos, não modifica `/usr`, `/etc`, regras udev ou a imagem do sistema. Os arquivos da aplicação ficam em `~/.local/bin`, `$XDG_CONFIG_HOME/systemd/user` e `$XDG_DATA_HOME` (com os padrões `~/.config` e `~/.local/share`). Requer Python 3 e systemd de usuário existentes.

**Kinoite, Silverblue e outras distribuições imutáveis:** utiliza exclusivamente o que já está disponível. Não utiliza layering, ambientes Python adicionais, runtimes baixados ou containers para suprir dependências. A presença de Qt ou GTK não garante a presença dos bindings Python. Se faltar a GUI, instale explicitamente somente o daemon:

```bash
./install.sh --daemon-only
```

Esse modo desativa o serviço gráfico anterior, preserva `config.json` e não instala atalhos gráficos. Se faltar Python ou acesso ao HID, o daemon também não poderá controlar o hardware. O instalador não concede permissões; as regras em `udev/` são apenas referência e não são aplicadas.

### Capacidades e requisitos existentes

| Função | Componentes/acesso necessários | Na ausência |
|---|---|---|
| Daemon RGB e brilho automático | Python 3, HID AW-ELC acessível, eventos Linux | Hardware indisponível; diagnóstico explícito |
| Painel GNOME | PyGObject, GTK4, Libadwaita, sessão gráfica | Usar daemon/CLI sem GUI |
| Painel KDE Plasma 6 | PyQt6 (Widgets, Network, Qml, Quick), QtQuick Controls/Layouts, Kirigami 6, sessão gráfica | Usar daemon/CLI sem GUI |
| Integração de tema | Integração de plataforma/portal já presente | Aparência conforme os componentes disponíveis |
| Atalhos Fn+F5/Fn+F9 | Leitura dos dispositivos evdev existentes | Atalhos físicos indisponíveis; comandos continuam disponíveis |
| Perfis de energia | Serviço compatível com PowerProfiles e `powerprofilesctl` ou `busctl` existentes | Seleção de perfil desabilitada |
| Sensores | Arquivos hwmon legíveis | `N/A`, não uma leitura falsa de zero |
| Bandeja | Host StatusNotifier compatível | Painel pode ser aberto por `--show` |
| Atualização | Rede HTTPS e diretórios de usuário graváveis | Versão instalada continua disponível |

Não há instalação automática de serviços, extensões ou dependências. No GNOME sem host de bandeja, o ícone pode não aparecer. Não há promessa de paridade visual ou de suporte a todas as versões de Ubuntu/Fedora. O backend KDE requer componentes Qt6/Kirigami6; ambientes Plasma5 não satisfazem esse requisito.

### Uso e diagnóstico

```bash
~/.local/bin/g15-tray --show
~/.local/bin/g15-tray --diagnose
~/.local/bin/g15-tray --backend qt --check-dependencies
~/.local/bin/g15-tray --backend gtk --show
~/.local/bin/g15-tray --headless --cycle-backlight
~/.local/bin/g15-tray --headless --toggle-gmode
```

`G15_UI_BACKEND=gtk|qt` permite seleção explícita. Falta de toolkit não provoca troca silenciosa para o outro. A opção `--headless` não importa bibliotecas gráficas; modifica a configuração e solicita o perfil de energia quando aplicável. Alterações de LEDs exigem daemon ativo e acesso ao HID. `--diagnose` consulta permissões, sensores e disponibilidade do serviço de energia, sem escrever no hardware ou alterar perfis. A verificação gráfica usa subprocesso isolado, sem iniciar monitores evdev, daemon ou atualizador.

### Comportamento implementado

- Brilho da tela em cinco faixas: 0–20 → 10%, 21–40 → 30%, 41–60 → 50%, 61–80 → 75%, 81–100 → 100%, com histerese de ±2%. `bl_power != 0` apaga os LEDs; a detecção depende do driver/compositor.
- Cor única ou quatro zonas, efeitos static, breathing, pulse, morph, spectrum e rainbow. O limite RGB padrão é 230 por canal.
- O daemon bloqueia em eventos netlink/inotify quando ocioso. A GUI consulta telemetria a cada três segundos; não se promete CPU zero para toda a aplicação.
- Zonas conhecidas dos IDs de plataforma `0C01`, `0E03`, `0E07`, `0E0A`; demais controladores usam a contagem reportada ou fallback. Isso não comprova todos os modelos G15.
- Gravação de boot com resposta HID, estado pendente/em execução/concluído e identificação própria da solicitação. Prazo de 30 segundos; timeout significa ausência de confirmação no prazo, não prova de falha física. A resposta HID não equivale a leitura independente da EEPROM após reinicialização.
- Modo G solicita performance e restaura o perfil anterior; falhas são reportadas. Isso não garante controle direto de ventoinhas ou equivalência ao Game Shift do firmware.
- Atualizador baixa um único SHA completo, valida Python, prepara arquivos e substitui cada destino com recuperação de falhas. Não modifica o checkout Git. Instalações com alterações locais não publicadas não tentam atualizar pelo GitHub; reinstale após publicar o commit para habilitar atualizações remotas. Falhas de download, aplicação, recuperação, registro da versão e enfileiramento do reinício são diferenciadas. A recuperação em memória não resiste a SIGKILL/queda de energia como uma transação global. O reinício é enfileirado sem bloquear a própria GUI; conclusão pode ser consultada em `systemctl --user status`.

### Validação e limites

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
bash -n install.sh uninstall.sh
```

Os testes usam arquivos temporários e hardware/serviços simulados. Incluem normalização de JSON, rollback após substituição parcial, falha de recuperação, recriação real de watches no mesmo caminho, preservação de alterações durante gravação e seleção isolada dos toolkits. O teste Qt/QML é pulado explicitamente quando PyQt6 não existe. O CI possui uma etapa Qt dedicada; a configuração de CI não significa que tenha sido executada localmente.

Integração visual em KDE real, Ubuntu/Fedora em suas diferentes edições, permissões nas imagens imutáveis e operações físicas HID/EEPROM precisam de validação em cada ambiente. Não se presume que bindings ou permissões estejam incluídos numa imagem de distribuição.

Desinstalação: `./uninstall.sh`. Remove arquivos de usuário e preserva a configuração e as regras do sistema.

## English

Linux control for Alienware AW-ELC `187c:0550` / `187c:0551`. The hardware daemon uses Python's standard library; GNOME uses GTK4/Libadwaita and KDE Plasma 6 uses PyQt6/QtQuick/Kirigami6, with isolated imports.

Installation is user-only and never installs dependencies or changes `/usr`, `/etc`, udev rules or the system image, on either traditional or immutable distributions. Run `./bin/g15-tray --check-dependencies` before `./install.sh`. If graphical components are absent, use `./install.sh --daemon-only`. Existing Python, user systemd and HID permissions are still required. No layering, downloaded runtimes or containers are used as dependency workarounds.

Use `--show` for the panel, `--diagnose` for optional capabilities, `--print-backend` or `--backend gtk|qt` for explicit selection. `--headless --cycle-backlight` and `--headless --toggle-gmode` operate without importing either toolkit. Missing dependencies never trigger a silent toolkit switch.

Unavailable sensors show `N/A`; unavailable power-profile support disables its selector. Hotkeys require existing evdev read access. A tray host is optional for opening the panel. Theme integration depends on the platform plugins/portals already available. Qt6 does not imply the Python bindings are present; Plasma5 is outside the Qt6/Kirigami6 backend requirement.

Updates pin all downloads to one commit, stage and validate payloads, and recover from partial replacement errors without changing the Git checkout. This is not a global crash-safe transaction. Boot writes use correlated pending/running/completed feedback and a 30-second deadline. A missing confirmation is reported as a timeout, not as proven hardware failure.

Automated tests run using temporary user data and mocked hardware/services. The QML smoke test explicitly skips when PyQt6 is absent. Actual visual integration on KDE and GNOME, immutable images and physical HID/EEPROM behavior require testing on those systems; full distribution compatibility and feature parity are not claimed. See the Portuguese capability table and validation notes above.
