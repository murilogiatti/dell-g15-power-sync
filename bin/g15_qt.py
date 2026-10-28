#!/usr/bin/env python3
"""
Dell G15 KDE Plasma Interface (`g15_qt.py`).
Uses Qt 6 (`PyQt6`) + KDE Kirigami (`org.kde.kirigami`) + `QSystemTrayIcon`.
Strictly isolated from GTK/Libadwaita: never imports `gi`, `Gtk`, or `Adw`.
Follows KDE Plasma themes, color schemes (Breeze / Breeze Dark / custom palettes),
fonts, icons, and accessibility automatically via the Plasma `kde` QPA platform theme.
"""

import json
import copy
import os
import signal
import sys
import threading
import time

# Strictly import Qt6 modules only
from PyQt6.QtCore import (
    QByteArray,
    QLockFile,
    QStandardPaths,
    QFileSystemWatcher,
    QObject,
    QSocketNotifier,
    Qt,
    QTimer,
    QUrl,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QAction, QActionGroup, QColor, QIcon
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtQuick import QQuickWindow
from PyQt6.QtWidgets import QApplication, QColorDialog, QMenu, QSystemTrayIcon

import g15_core as core

from PyQt6.QtNetwork import QAbstractSocket, QLocalServer, QLocalSocket

HAS_QT_NETWORK = True

SINGLE_INSTANCE_KEY = "io.github.murilogiatti.DellG15Control.qt"


def _build_kirigami_qml():
    """
    Returns the Kirigami 6 / QtQuick Controls 2 QML source for the KDE Control Center.
    Uses Kirigami.ApplicationWindow, Kirigami.ScrollablePage, Kirigami.FormLayout,
    and Kirigami.AbstractCard so the window natively follows Plasma's Breeze/custom
    color scheme, fonts, spacing, and accessibility settings.
    """
    return """
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: rootWin
    title: "Dell G15 Control Center"
    width: 700
    height: 780
    minimumWidth: 560
    minimumHeight: 540
    visible: false

    onClosing: function(close) {
        close.accepted = false
        rootWin.visible = false
    }

    Connections {
        target: backend
        function onShowWindowRequested() {
            rootWin.visible = true
            rootWin.raise()
            rootWin.requestActivate()
        }
        function onToastMessage(msg) {
            rootWin.showPassiveNotification(msg, "short")
        }
    }

    pageStack.initialPage: Kirigami.ScrollablePage {
        id: mainPage
        title: "Dell G15 Control Center"

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing

            // --- Group 1: Backlight & Brightness (Fn+F5) ---
            Kirigami.Heading {
                level: 3
                text: backend.tr("Iluminação e Brilho (Tecla Fn+F5)", "Backlight and Brightness (Fn+F5 Key)")
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                opacity: 0.75
                text: backend.tr(
                    "Sincronize automaticamente com a tela, ajuste manualmente ou use Fn+F5 para ciclar os modos.",
                    "Automatically sync with screen, adjust manually, or press Fn+F5 to cycle modes."
                )
            }

            Kirigami.AbstractCard {
                Layout.fillWidth: true
                contentItem: ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing

                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Brilho Automático (Ambient Sync)", "Automatic Brightness (Ambient Sync)")
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Ajusta a intensidade dos LEDs em tempo real conforme o brilho da tela",
                                    "Adjusts keyboard LED intensity in real time as screen brightness changes"
                                )
                            }
                        }
                        QQC2.Switch {
                            checked: backend.syncScreen
                            onToggled: backend.setSyncScreen(checked)
                        }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    RowLayout {
                        Layout.fillWidth: true
                        enabled: !backend.syncScreen
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Intensidade Manual do Teclado", "Manual Keyboard Intensity") + " (" + backend.manualBrightness + "%)"
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Deslize ou use a roda do mouse (±5%) para definir o brilho fixo (0% a 100%)",
                                    "Slide or scroll mouse wheel (±5%) to set fixed brightness (0% to 100%)"
                                )
                            }
                        }
                        QQC2.Slider {
                            id: manualSlider
                            Layout.preferredWidth: 220
                            from: 0
                            to: 100
                            stepSize: 5
                            snapMode: QQC2.Slider.SnapAlways
                            value: backend.manualBrightness
                            onMoved: backend.setManualBrightness(Math.round(value))
                            WheelHandler {
                                onWheel: function(event) {
                                    if (!manualSlider.enabled) return
                                    var step = event.angleDelta.y > 0 ? 5 : -5
                                    var next = Math.max(0, Math.min(100, backend.manualBrightness + step))
                                    backend.setManualBrightness(next)
                                    event.accepted = true
                                }
                            }
                        }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Proteção do Limitador de Energia (Cap 230)", "Power Limiter Protection (Cap 230)")
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Limita o pico RGB em #E6E6E6 para evitar quedas de brilho no controlador",
                                    "Caps RGB peak at #E6E6E6 to prevent controller power-drop dimming"
                                )
                            }
                        }
                        QQC2.Switch {
                            checked: backend.powerCap
                            onToggled: backend.setPowerCap(checked)
                        }
                    }
                }
            }

            // --- Group 2: RGB Colors & Zones ---
            Kirigami.Heading {
                level: 3
                text: backend.tr("Cores RGB e Zonas do Teclado", "RGB Colors and Keyboard Zones")
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                opacity: 0.75
                text: backend.tr(
                    "Use uma cor única para o teclado inteiro ou personalize cada uma das 4 regiões.",
                    "Use a single color for the whole keyboard or customize each of the 4 regions."
                )
            }

            Kirigami.AbstractCard {
                Layout.fillWidth: true
                contentItem: ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing

                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Separar em 4 Zonas Independentes", "Split into 4 Independent Zones")
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Permite escolher cores diferentes para WASD, Centro-Esq, Centro-Dir e NumPad",
                                    "Allows choosing different colors for WASD, Center-Left, Center-Right and NumPad"
                                )
                            }
                        }
                        QQC2.Switch {
                            checked: backend.perZone
                            onToggled: backend.setPerZone(checked)
                        }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    // Unified Color Picker Row (visible when !perZone)
                    RowLayout {
                        Layout.fillWidth: true
                        visible: !backend.perZone
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Cor do Teclado Inteiro", "Whole Keyboard Color")
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Clique no botão de cor ao lado para escolher uma cor personalizada para todas as teclas",
                                    "Click the color button to pick a custom RGB color for all keys"
                                )
                            }
                        }
                        QQC2.Button {
                            text: "#" + backend.zoneColors1[0]
                            onClicked: backend.pickUnifiedColor(false)
                            contentItem: RowLayout {
                                spacing: 6
                                Rectangle {
                                    width: 18
                                    height: 18
                                    radius: 9
                                    color: "#" + backend.zoneColors1[0]
                                    border.width: 1
                                    border.color: Qt.rgba(0.5, 0.5, 0.5, 0.6)
                                }
                                QQC2.Label { text: "#" + backend.zoneColors1[0] }
                            }
                        }
                        QQC2.Button {
                            visible: backend.mode === "morph"
                            text: "#" + backend.zoneColors2[0]
                            onClicked: backend.pickUnifiedColor(true)
                            contentItem: RowLayout {
                                spacing: 6
                                Rectangle {
                                    width: 18
                                    height: 18
                                    radius: 9
                                    color: "#" + backend.zoneColors2[0]
                                    border.width: 1
                                    border.color: Qt.rgba(0.5, 0.5, 0.5, 0.6)
                                }
                                QQC2.Label { text: "#" + backend.zoneColors2[0] }
                            }
                        }
                    }

                    // 4 Independent Zone Pickers (visible when perZone)
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: backend.perZone
                        spacing: Kirigami.Units.smallSpacing

                        QQC2.Label {
                            opacity: 0.75
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            text: backend.tr(
                                "Clique no seletor de cada região do teclado para alterar sua cor individual:",
                                "Click each keyboard region's picker to customize its individual color:"
                            )
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing
                            Repeater {
                                model: 4
                                delegate: Kirigami.AbstractCard {
                                    Layout.fillWidth: true
                                    contentItem: ColumnLayout {
                                        spacing: 6
                                        QQC2.Label {
                                            Layout.alignment: Qt.AlignHCenter
                                            font.bold: true
                                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                                            text: backend.zoneTitle(index)
                                        }
                                        QQC2.Button {
                                            Layout.alignment: Qt.AlignHCenter
                                            onClicked: backend.pickZoneColor(index, false)
                                            contentItem: RowLayout {
                                                spacing: 4
                                                Rectangle {
                                                    width: 16
                                                    height: 16
                                                    radius: 8
                                                    color: "#" + backend.zoneColors1[index]
                                                    border.width: 1
                                                    border.color: Qt.rgba(0.5, 0.5, 0.5, 0.6)
                                                }
                                                QQC2.Label { text: "#" + backend.zoneColors1[index] }
                                            }
                                        }
                                        QQC2.Button {
                                            Layout.alignment: Qt.AlignHCenter
                                            visible: backend.mode === "morph"
                                            onClicked: backend.pickZoneColor(index, true)
                                            contentItem: RowLayout {
                                                spacing: 4
                                                Rectangle {
                                                    width: 16
                                                    height: 16
                                                    radius: 8
                                                    color: "#" + backend.zoneColors2[index]
                                                    border.width: 1
                                                    border.color: Qt.rgba(0.5, 0.5, 0.5, 0.6)
                                                }
                                                QQC2.Label { text: "#" + backend.zoneColors2[index] }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    // 12 Color Presets Grid
                    QQC2.Label {
                        opacity: 0.75
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        text: backend.tr(
                            "Cores Pré-Selecionadas (clique em qualquer opção para aplicar no teclado):",
                            "Pre-Selected Colors (click any preset to apply to the keyboard):"
                        )
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 4
                        rowSpacing: 6
                        columnSpacing: 6

                        Repeater {
                            model: backend.colorPresets
                            delegate: QQC2.Button {
                                Layout.fillWidth: true
                                onClicked: backend.applyQuickColor(modelData.hex)
                                QQC2.ToolTip.visible: hovered
                                QQC2.ToolTip.text: modelData.label + " (#" + modelData.hex + ")"
                                contentItem: RowLayout {
                                    spacing: 6
                                    Rectangle {
                                        width: 14
                                        height: 14
                                        radius: 7
                                        color: "#" + modelData.hex
                                        border.width: 1
                                        border.color: Qt.rgba(0.5, 0.5, 0.5, 0.55)
                                    }
                                    QQC2.Label {
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                                        text: modelData.label
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // --- Group 3: Hardware Effects & Onboard Memory ---
            Kirigami.Heading {
                level: 3
                text: backend.tr("Efeitos de Hardware e Memória", "Hardware Effects and Memory")
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                opacity: 0.75
                text: backend.tr(
                    "Animações executadas pelo próprio chip do teclado (zero uso de processador).",
                    "Animations executed directly by the keyboard chip (zero CPU usage)."
                )
            }

            Kirigami.AbstractCard {
                Layout.fillWidth: true
                contentItem: ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing

                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Efeito de Iluminação", "Lighting Effect")
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Escolha entre cor estática, respiração, pulso, transição (morph) ou arco-íris",
                                    "Choose between static color, breathing, pulse, two-color morph or rainbow"
                                )
                            }
                        }
                        QQC2.ComboBox {
                            Layout.preferredWidth: 260
                            model: backend.effectLabels
                            currentIndex: backend.modeIndex
                            onActivated: function(idx) { backend.setModeByIndex(idx) }
                        }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    RowLayout {
                        Layout.fillWidth: true
                        enabled: backend.mode !== "static"
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Velocidade da Animação (%)", "Animation Speed (%)") + " (" + backend.speed + "%)"
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Use a roda do mouse (±5%) para ajustar (10% = bem lento e suave, 100% = rápido)",
                                    "Use mouse wheel (±5%) to adjust (10% = very slow and smooth, 100% = fast)"
                                )
                            }
                        }
                        QQC2.Slider {
                            id: speedSlider
                            Layout.preferredWidth: 220
                            from: 10
                            to: 100
                            stepSize: 5
                            snapMode: QQC2.Slider.SnapAlways
                            value: backend.speed
                            onMoved: backend.setSpeed(Math.round(value))
                            WheelHandler {
                                onWheel: function(event) {
                                    if (!speedSlider.enabled) return
                                    var step = event.angleDelta.y > 0 ? 5 : -5
                                    var next = Math.max(10, Math.min(100, backend.speed + step))
                                    backend.setSpeed(next)
                                    event.accepted = true
                                }
                            }
                        }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Memória Interna do Teclado (Boot)", "Onboard Keyboard Memory (Boot)")
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Grava a cor e efeito atuais no chip do teclado para ligar já configurado",
                                    "Saves current color and effect to the keyboard chip so it powers on configured"
                                )
                            }
                        }
                        QQC2.Button {
                            text: backend.tr("💾 Salvar no Teclado", "💾 Save to Keyboard")
                            onClicked: backend.triggerSaveBoot()
                        }
                    }
                }
            }

            // --- Group 4: G-Mode (Fn+F9), Power Profile, Telemetry & Updates ---
            Kirigami.Heading {
                level: 3
                text: backend.tr("Modo G (Fn+F9), Energia e Sensores", "G-Mode (Fn+F9), Power and Sensors")
            }

            Kirigami.AbstractCard {
                Layout.fillWidth: true
                contentItem: ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing

                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("🚀 Modo G / Game Shift (Tecla Fn+F9)", "🚀 G-Mode / Game Shift (Fn+F9 Key)")
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Ativa Alto Desempenho e aplica Vermelho Puro mantendo o brilho atual; restaura suas cores ao desligar",
                                    "Activates High Performance and Pure Red keeping current brightness; restores your colors when disabled"
                                )
                            }
                        }
                        QQC2.Switch {
                            checked: backend.gMode
                            onToggled: backend.setGMode(checked)
                        }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Perfil Térmico e de Energia", "Thermal and Power Profile")
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Alterna entre Economia de bateria, Equilibrado ou Alto Desempenho (G-Mode)",
                                    "Switches between Power Saver, Balanced or High Performance (G-Mode)"
                                )
                            }
                        }
                        QQC2.ComboBox {
                            Layout.preferredWidth: 260
                            model: backend.powerLabels
                            enabled: backend.powerAvailable
                            currentIndex: backend.powerProfileIndex
                            onActivated: function(idx) { backend.setPowerProfileByIndex(idx) }
                        }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Sensores Internos (Ao Vivo)", "Internal Sensors (Live)")
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.tr(
                                    "Temperaturas de CPU, GPU, SSD NVMe e rotação das ventoinhas (RPM)",
                                    "CPU, GPU, NVMe SSD temperatures and cooling fan speeds (RPM)"
                                )
                            }
                        }
                        QQC2.Label {
                            font.family: "monospace"
                            text: backend.telemetryDetailed
                        }
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            QQC2.Label {
                                font.bold: true
                                text: backend.tr("Atualizações do Aplicativo", "Application Updates")
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                opacity: 0.7
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                text: backend.updateSubtitle
                            }
                        }
                        QQC2.Button {
                            enabled: !backend.updateBusy
                            text: backend.updateButtonLabel
                            onClicked: backend.onUpdateButtonClicked()
                        }
                    }
                }
            }
        }
    }
}
"""


class G15TrayIcon(QSystemTrayIcon):
    """QSystemTrayIcon subclass that supports mouse-wheel brightness stepping on KDE Plasma."""

    wheelStepped = pyqtSignal(int)

    def event(self, ev):
        if ev.type() == ev.Type.Wheel:
            delta = ev.angleDelta().y()
            if delta != 0:
                self.wheelStepped.emit(1 if delta > 0 else -1)
                ev.accept()
                return True
        return super().event(ev)


class G15QtController(QObject):
    _powerFinished = pyqtSignal(object, str, bool)
    _pollFinished = pyqtSignal(object, object, str, int)
    configChanged = pyqtSignal()
    telemetryChanged = pyqtSignal()
    updateStateChanged = pyqtSignal()
    showWindowRequested = pyqtSignal()
    toastMessage = pyqtSignal(str)
    _updateCheckFinished = pyqtSignal(str, str, bool, str)
    _selfUpdateFinished = pyqtSignal(str, str)

    def __init__(self, app, start_hidden=True):
        super().__init__()
        self.app = app
        self.start_hidden = start_hidden
        self.cfg = core.load_config()
        self.telemetry = core.read_telemetry()
        self.active_power_profile = None
        self.local_commit, self.repo_dir = core.read_local_version()
        self.latest_commit = self.local_commit
        self.latest_commit_msg = ""
        self.update_available = False
        self._checking_update = False
        self._updating_app = False
        self._notified_commit = ""
        self._power_busy = False
        self._power_generation = 0
        self._poll_busy = False
        self._daemon_label = core.daemon_status_label()
        self._pending_boot_seq = 0
        self._last_gmode_ts = 0.0
        self._last_backlight_ts = 0.0
        self._pending_scancode = 0
        self._evdev_fds = []
        self._evdev_notifiers = []

        self._boot_timer = QTimer(self)
        self._boot_timer.setSingleShot(True)
        self._boot_timer.timeout.connect(self._on_save_boot_timeout)

        self._updateCheckFinished.connect(self._on_update_check_done)
        self._selfUpdateFinished.connect(self._on_self_update_done)

        self._powerFinished.connect(self._on_power_done)
        self._pollFinished.connect(self._on_poll_done)
        self._setup_tray_icon()
        self._setup_config_watcher()
        self._setup_hotkey_monitors()

        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.timeout.connect(self._on_telemetry_tick)
        self._telemetry_timer.start(3000)

        QTimer.singleShot(12000, lambda: self.check_for_updates_async(manual=False))
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(
            lambda: self.check_for_updates_async(manual=False)
        )
        self._update_timer.start(21600 * 1000)

    # --- QML Properties & Invokables ---
    @pyqtSlot(str, str, result=str)
    def tr(self, pt_str, en_str):
        return core.tr(pt_str, en_str)

    @pyqtProperty(bool, notify=configChanged)
    def syncScreen(self):
        return bool(self.cfg.get("sync_screen", True))

    @pyqtProperty(int, notify=configChanged)
    def manualBrightness(self):
        return int(self.cfg.get("manual_brightness", 100))

    @pyqtProperty(bool, notify=configChanged)
    def powerCap(self):
        return bool(self.cfg.get("power_cap", True))

    @pyqtProperty(bool, notify=configChanged)
    def perZone(self):
        return bool(self.cfg.get("per_zone", False))

    @pyqtProperty(str, notify=configChanged)
    def mode(self):
        return str(self.cfg.get("mode", "static")).lower()

    @pyqtProperty(int, notify=configChanged)
    def modeIndex(self):
        m = self.mode
        return next(
            (i for i, (k, _pt, _en) in enumerate(core.EFFECT_MODES) if k == m), 0
        )

    @pyqtProperty(int, notify=configChanged)
    def speed(self):
        return int(self.cfg.get("speed", 40))

    @pyqtProperty(bool, notify=configChanged)
    def gMode(self):
        return bool(self.cfg.get("g_mode", False))

    @pyqtProperty(list, notify=configChanged)
    def zoneColors1(self):
        return list(self.cfg.get("zones_rgb", core.DEFAULT_CONFIG["zones_rgb"]))

    @pyqtProperty(list, notify=configChanged)
    def zoneColors2(self):
        return list(self.cfg.get("zones_rgb2", core.DEFAULT_CONFIG["zones_rgb2"]))

    @pyqtProperty(list, constant=True)
    def colorPresets(self):
        return [
            {"code": code, "hex": hex_val, "label": core.tr(lbl_pt, lbl_en)}
            for code, hex_val, lbl_pt, lbl_en in core.COLOR_PRESETS
        ]

    @pyqtProperty(list, constant=True)
    def effectLabels(self):
        return [core.tr(pt, en) for _k, pt, en in core.EFFECT_MODES]

    @pyqtProperty(list, constant=True)
    def powerLabels(self):
        return [core.tr(pt, en) for _k, pt, en in core.POWER_PROFILES]

    @pyqtProperty(bool, notify=telemetryChanged)
    def powerAvailable(self):
        return self.active_power_profile is not None

    @pyqtProperty(int, notify=telemetryChanged)
    def powerProfileIndex(self):
        return next(
            (
                i
                for i, (k, _pt, _en) in enumerate(core.POWER_PROFILES)
                if k == self.active_power_profile
            ),
            1,
        )

    @pyqtProperty(str, notify=telemetryChanged)
    def telemetryDetailed(self):
        return core.format_detailed_telemetry_label(self.telemetry) + "\n" + self._daemon_label

    @pyqtProperty(str, notify=updateStateChanged)
    def updateSubtitle(self):
        notice = core.local_build_update_notice(self.local_commit)
        if notice:
            return notice
        short_local = (
            self.local_commit[:7]
            if self.local_commit and self.local_commit != "unknown"
            else "local"
        )
        if self._updating_app:
            return core.tr(
                "Baixando e aplicando atualização oficial do GitHub...",
                "Downloading and applying official update from GitHub...",
            )
        if self._checking_update:
            return core.tr(
                "Consultando repositório oficial no GitHub...",
                "Checking official GitHub repository...",
            )
        if self.update_available:
            short_new = self.latest_commit[:7] if self.latest_commit else "new"
            msg = self.latest_commit_msg or ""
            return core.tr(
                f"Nova versão disponível ({short_new}): {msg}",
                f"New version available ({short_new}): {msg}",
            )
        return core.tr(
            f"Versão instalada: #{short_local} — Verifica automaticamente novas versões no GitHub",
            f"Installed version: #{short_local} — Automatically checks for new versions on GitHub",
        )

    @pyqtProperty(str, notify=updateStateChanged)
    def updateButtonLabel(self):
        if self._updating_app:
            return core.tr("⏳ Atualizando...", "⏳ Updating...")
        if self._checking_update:
            return core.tr("⏳ Verificando...", "⏳ Checking...")
        if self.update_available:
            return core.tr("🔄 Instalar Atualização", "🔄 Install Update")
        return core.tr("🔍 Verificar Agora", "🔍 Check Now")

    @pyqtProperty(bool, notify=updateStateChanged)
    def updateBusy(self):
        return bool(self._checking_update or self._updating_app)

    @pyqtSlot(int, result=str)
    def zoneColor1(self, idx):
        arr = self.cfg.get("zones_rgb", core.DEFAULT_CONFIG["zones_rgb"])
        return arr[idx % len(arr)]

    @pyqtSlot(int, result=str)
    def zoneColor2(self, idx):
        arr = self.cfg.get("zones_rgb2", core.DEFAULT_CONFIG["zones_rgb2"])
        return arr[idx % len(arr)]

    @pyqtSlot(int, result=str)
    def zoneTitle(self, idx):
        titles = (
            core.tr("Zona 1 (WASD)", "Zone 1 (WASD)"),
            core.tr("Zona 2 (Centro-Esq)", "Zone 2 (Center-L)"),
            core.tr("Zona 3 (Centro-Dir)", "Zone 3 (Center-R)"),
            core.tr("Zona 4 (NumPad)", "Zone 4 (NumPad)"),
        )
        return titles[idx % 4]

    @pyqtSlot(bool)
    def setSyncScreen(self, active):
        self.cfg["sync_screen"] = bool(active)
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        core.save_config(self.cfg)
        self._refresh_all()

    @pyqtSlot(int)
    def setManualBrightness(self, val):
        clamped = max(0, min(100, int(val)))
        if self.cfg.get("manual_brightness") != clamped or self.cfg.get("sync_screen"):
            self.cfg["manual_brightness"] = clamped
            self.cfg["sync_screen"] = False
            self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
            core.save_config(self.cfg)
            self._refresh_all()

    @pyqtSlot(bool)
    def setPowerCap(self, active):
        self.cfg["power_cap"] = bool(active)
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        core.save_config(self.cfg)
        self._refresh_all()

    @pyqtSlot(bool)
    def setPerZone(self, active):
        self.cfg["per_zone"] = bool(active)
        if not self.cfg["per_zone"]:
            c0 = self.cfg["zones_rgb"][0]
            self.cfg["zones_rgb"] = [c0] * 4
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        core.save_config(self.cfg)
        self._refresh_all()

    @pyqtSlot(bool)
    def pickUnifiedColor(self, is_secondary):
        key = "zones_rgb2" if is_secondary else "zones_rgb"
        curr_hex = self.cfg.get(key, ["E6E6E6"])[0]
        chosen = QColorDialog.getColor(
            QColor(f"#{curr_hex}"),
            None,
            core.tr("Selecionar Cor do Teclado", "Select Keyboard Color"),
        )
        if not chosen.isValid():
            return
        hex_val = chosen.name().lstrip("#").upper()
        self.cfg[key] = [hex_val] * 4
        if not is_secondary and self.cfg.get("mode") in ("spectrum", "rainbow"):
            self.cfg["mode"] = "static"
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        core.save_config(self.cfg)
        self._refresh_all()

    @pyqtSlot(int, bool)
    def pickZoneColor(self, zone_idx, is_secondary):
        key = "zones_rgb2" if is_secondary else "zones_rgb"
        curr_hex = self.cfg[key][zone_idx % 4]
        chosen = QColorDialog.getColor(
            QColor(f"#{curr_hex}"),
            None,
            f"{self.zoneTitle(zone_idx)}",
        )
        if not chosen.isValid():
            return
        hex_val = chosen.name().lstrip("#").upper()
        self.cfg[key][zone_idx % 4] = hex_val
        if not is_secondary and self.cfg.get("mode") in ("spectrum", "rainbow"):
            self.cfg["mode"] = "static"
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        core.save_config(self.cfg)
        self._refresh_all()

    @pyqtSlot(str)
    def applyQuickColor(self, hex_val):
        self.cfg["per_zone"] = False
        self.cfg["zones_rgb"] = [str(hex_val).lstrip("#").upper()] * 4
        if self.cfg.get("mode") in ("spectrum", "rainbow"):
            self.cfg["mode"] = "static"
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        core.save_config(self.cfg)
        self._refresh_all()

    @pyqtSlot(int)
    def setModeByIndex(self, idx):
        if 0 <= idx < len(core.EFFECT_MODES):
            self.cfg["mode"] = core.EFFECT_MODES[idx][0]
            self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
            core.save_config(self.cfg)
            self._refresh_all()

    @pyqtSlot(int)
    def setSpeed(self, val):
        clamped = max(10, min(100, int(val)))
        if self.cfg.get("speed") != clamped:
            self.cfg["speed"] = clamped
            self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
            core.save_config(self.cfg)
            self._refresh_all()

    @pyqtSlot()
    def triggerSaveBoot(self):
        self._boot_timer.stop()
        next_seq = core.request_boot_save(self.cfg)
        self._pending_boot_seq = next_seq
        self._boot_timer.start(core.BOOT_SAVE_TIMEOUT_SEC * 1000)

    @pyqtSlot(bool)
    def setGMode(self, active):
        self.toggle_g_mode(target_state=bool(active), notify=True)

    @pyqtSlot(int)
    def setPowerProfileByIndex(self, idx):
        if 0 <= idx < len(core.POWER_PROFILES):
            prof_id = core.POWER_PROFILES[idx][0]
            self._apply_power_profile(prof_id)

    @pyqtSlot()
    def onUpdateButtonClicked(self):
        if self.update_available:
            self.perform_self_update_async()
        else:
            self.check_for_updates_async(manual=True)

    # --- Shared Business Actions ---
    def send_osd_notification(self, title, body):
        if hasattr(self, "tray") and self.tray:
            self.tray.showMessage(
                title,
                body,
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )

    def _queue_power_action(self, kind, target, notify):
        if self._power_busy:
            return
        self._power_busy = True
        self._power_generation += 1
        cfg = copy.deepcopy(self.cfg)
        def worker():
            result, error = None, ""
            try:
                result = core.run_power_action(cfg, kind, target)
            except Exception as exc:
                error = str(exc)
            self._powerFinished.emit(result, error, notify)
        threading.Thread(target=worker, daemon=True).start()

    def _on_power_done(self, result, error, notify):
        self._power_busy = False
        self.cfg = core.load_config()
        if error:
            self.send_osd_notification(core.tr("Falha no perfil de energia", "Power profile failed"), error)
        elif result:
            changed, self.active_power_profile, title, body = result
            if changed and notify:
                self.send_osd_notification(title, body)
        self._refresh_all()
        return False

    def toggle_g_mode(self, target_state=None, notify=True):
        self._queue_power_action("gmode", target_state, notify)

    def cycle_backlight_mode(self, notify=True):
        title, body = core.apply_backlight_cycle(self.cfg)
        if notify:
            self.send_osd_notification(title, body)
        self._refresh_all()

    def _step_brightness(self, direction):
        _new_val, title, body = core.apply_brightness_step(self.cfg, direction)
        self.send_osd_notification(title, body)
        self._refresh_all()

    def _apply_power_profile(self, prof_id):
        self._queue_power_action("profile", prof_id, True)

    def present_control_window(self):
        self.showWindowRequested.emit()

    # --- KDE System Tray Indicator (StatusNotifierItem via Qt6 QPA) ---
    def _setup_tray_icon(self):
        icon_svg = os.path.join(core.ASSETS_DIR, "tray-icon.svg")
        icon_png = os.path.join(core.ASSETS_DIR, "tray-icon.png")
        if os.path.exists(icon_svg):
            icon = QIcon(icon_svg)
        elif os.path.exists(icon_png):
            icon = QIcon(icon_png)
        else:
            icon = QIcon.fromTheme("input-keyboard-symbolic", QIcon.fromTheme("input-keyboard"))

        self.tray = G15TrayIcon(icon, self)
        self.tray.setToolTip(f"Dell G15 Control — {core.format_telemetry_label(self.telemetry)}")
        self.tray_menu = QMenu()
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.wheelStepped.connect(self._step_brightness)
        self._rebuild_tray_menu()
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.present_control_window()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self.cycle_backlight_mode(notify=True)

    def _rebuild_tray_menu(self):
        self.tray_menu.clear()

        act_telemetry = QAction(core.format_telemetry_label(self.telemetry), self.tray_menu)
        act_telemetry.setEnabled(False)
        self.tray_menu.addAction(act_telemetry)

        act_open = QAction(
            core.tr("🎛️ Abrir Painel de Controle...", "🎛️ Open Control Panel..."),
            self.tray_menu,
        )
        act_open.triggered.connect(self.present_control_window)
        self.tray_menu.addAction(act_open)

        if self.update_available:
            short_sha = self.latest_commit[:7] if self.latest_commit else "new"
            act_upd_banner = QAction(
                core.tr(
                    f"🔄 Atualização Disponível ({short_sha}) — Instalar Agora",
                    f"🔄 Update Available ({short_sha}) — Install Now",
                ),
                self.tray_menu,
            )
            act_upd_banner.triggered.connect(self.perform_self_update_async)
            self.tray_menu.addAction(act_upd_banner)

        act_gmode = QAction(
            core.tr("🚀 Modo G / Game Shift (Fn+F9)", "🚀 G-Mode / Game Shift (Fn+F9)"),
            self.tray_menu,
        )
        act_gmode.setCheckable(True)
        act_gmode.setChecked(bool(self.cfg.get("g_mode", False)))
        act_gmode.triggered.connect(lambda _c: self.toggle_g_mode(notify=True))
        self.tray_menu.addAction(act_gmode)

        self.tray_menu.addSeparator()

        sync_on = bool(self.cfg.get("sync_screen", True))
        manual_val = int(self.cfg.get("manual_brightness", 100))
        bright_group = QActionGroup(self.tray_menu)
        bright_group.setExclusive(True)

        act_sync = QAction(
            core.tr(
                "🔄 Brilho Automático (Ambient Sync)",
                "🔄 Automatic Brightness (Ambient Sync)",
            ),
            bright_group,
        )
        act_sync.setCheckable(True)
        act_sync.setChecked(sync_on)
        act_sync.triggered.connect(lambda: self.setSyncScreen(True))
        self.tray_menu.addAction(act_sync)

        for step in (100, 75, 50, 30, 10, 0):
            if step == 0:
                lbl = core.tr("🌑 Desligar LEDs (0%)", "🌑 Turn Off LEDs (0%)")
            else:
                lbl = core.tr(f"🔆 Brilho Fixo: {step}%", f"🔆 Fixed Brightness: {step}%")
            act_step = QAction(lbl, bright_group)
            act_step.setCheckable(True)
            act_step.setChecked((not sync_on) and (manual_val == step))
            act_step.triggered.connect(lambda _c=False, s=step: self.setManualBrightness(s))
            self.tray_menu.addAction(act_step)

        self.tray_menu.addSeparator()

        # Quick Colors Submenu
        color_menu = self.tray_menu.addMenu(core.tr("🎨 Cores Rápidas", "🎨 Quick Colors"))
        color_group = QActionGroup(color_menu)
        color_group.setExclusive(True)
        cur_hex = str(self.cfg.get("zones_rgb", ["E6E6E6"])[0]).upper()
        cur_per_zone = bool(self.cfg.get("per_zone", False))
        for _code, hex_val, lbl_pt, lbl_en in core.COLOR_PRESETS:
            act_c = QAction(f"{core.tr(lbl_pt, lbl_en)} (#{hex_val})", color_group)
            act_c.setCheckable(True)
            act_c.setChecked((not cur_per_zone) and (cur_hex == hex_val))
            act_c.triggered.connect(lambda _c=False, h=hex_val: self.applyQuickColor(h))
            color_menu.addAction(act_c)

        # Effects Submenu
        fx_menu = self.tray_menu.addMenu(core.tr("✨ Efeitos do Teclado", "✨ Keyboard Effects"))
        fx_group = QActionGroup(fx_menu)
        fx_group.setExclusive(True)
        cur_mode = self.mode
        for idx, (m_key, lbl_pt, lbl_en) in enumerate(core.EFFECT_MODES):
            act_fx = QAction(core.tr(lbl_pt, lbl_en), fx_group)
            act_fx.setCheckable(True)
            act_fx.setChecked(cur_mode == m_key)
            act_fx.triggered.connect(lambda _c=False, i=idx: self.setModeByIndex(i))
            fx_menu.addAction(act_fx)

        # Power Profiles Submenu
        pwr_menu = self.tray_menu.addMenu(core.tr("⚡ Perfil de Energia", "⚡ Power Profile"))
        pwr_group = QActionGroup(pwr_menu)
        pwr_group.setExclusive(True)
        pwr_menu.setEnabled(self.active_power_profile is not None)
        for prof_id, lbl_pt, lbl_en in core.POWER_PROFILES:
            act_p = QAction(core.tr(lbl_pt, lbl_en), pwr_group)
            act_p.setCheckable(True)
            act_p.setChecked(self.active_power_profile == prof_id)
            act_p.triggered.connect(lambda _c=False, p=prof_id: self._apply_power_profile(p))
            pwr_menu.addAction(act_p)

        self.tray_menu.addSeparator()

        act_boot = QAction(
            core.tr(
                "💾 Salvar na Memória do Teclado (Boot)",
                "💾 Save to Keyboard Memory (Boot)",
            ),
            self.tray_menu,
        )
        act_boot.triggered.connect(self.triggerSaveBoot)
        self.tray_menu.addAction(act_boot)

        if self.update_available:
            upd_lbl = core.tr(
                f"🔄 Instalar Atualização ({self.latest_commit[:7]})",
                f"🔄 Install Update ({self.latest_commit[:7]})",
            )
            upd_fn = self.perform_self_update_async
        else:
            upd_lbl = core.tr("🔍 Verificar Atualizações...", "🔍 Check for Updates...")
            upd_fn = lambda: self.check_for_updates_async(manual=True)

        act_upd = QAction(upd_lbl, self.tray_menu)
        act_upd.triggered.connect(upd_fn)
        self.tray_menu.addAction(act_upd)

    # --- File Watcher & Evdev Hotkey Monitors ---
    def _setup_config_watcher(self):
        os.makedirs(core.CONFIG_DIR, exist_ok=True)
        if not os.path.exists(core.CONFIG_PATH):
            core.save_config(self.cfg)
        self._fs_watcher = QFileSystemWatcher([core.CONFIG_DIR, core.CONFIG_PATH], self)
        self._fs_watcher.fileChanged.connect(self._on_config_fs_changed)
        self._fs_watcher.directoryChanged.connect(self._on_config_fs_changed)

    def _on_config_fs_changed(self, _path):
        if os.path.exists(core.CONFIG_PATH) and core.CONFIG_PATH not in self._fs_watcher.files():
            self._fs_watcher.addPath(core.CONFIG_PATH)
        new_cfg = core.load_config()
        if new_cfg != self.cfg:
            self.cfg = new_cfg
            self._check_save_boot_feedback()
            self._refresh_all()

    def _check_save_boot_feedback(self):
        state, title, body, toast_msg = core.evaluate_boot_save_feedback(
            self.cfg, self._pending_boot_seq
        )
        if state == "pending":
            return
        if state == "running":
            return
        self._pending_boot_seq = 0
        self._boot_timer.stop()
        self.send_osd_notification(title, body)
        self.toastMessage.emit(toast_msg)

    def _on_save_boot_timeout(self):
        if not self._pending_boot_seq:
            return
        self._pending_boot_seq = 0
        self.send_osd_notification(
            core.tr("⚠️ Sem Resposta do Daemon", "⚠️ No Response from Daemon"),
            core.tr(
                "O serviço dell-g15-daemon não confirmou a gravação no teclado.",
                "The dell-g15-daemon service did not confirm the keyboard write.",
            ),
        )
        self.toastMessage.emit(
            core.tr(
                "Tempo esgotado aguardando confirmação do daemon.",
                "Timed out waiting for daemon confirmation.",
            )
        )

    def _setup_hotkey_monitors(self):
        for dev_node in core.discover_evdev_hotkey_nodes():
            try:
                fd = os.open(dev_node, os.O_RDONLY | os.O_NONBLOCK)
                self._evdev_fds.append(fd)
                notifier = QSocketNotifier(fd, QSocketNotifier.Type.Read, self)
                notifier.activated.connect(lambda *_args, sock_fd=fd: self._on_evdev_readable(sock_fd))
                self._evdev_notifiers.append(notifier)
            except OSError:
                continue

    def _close_evdev(self, fd):
        for notifier in self._evdev_notifiers:
            if int(notifier.socket()) == fd:
                notifier.setEnabled(False)
        if fd in self._evdev_fds:
            self._evdev_fds.remove(fd)
            os.close(fd)

    def close(self):
        for fd in list(self._evdev_fds):
            self._close_evdev(fd)

    def _on_evdev_readable(self, fd):
        pkt_size = core.INPUT_EVENT_STRUCT.size
        while True:
            try:
                raw = os.read(fd, pkt_size * 16)
                if not raw:
                    self._close_evdev(fd)
                    return
            except BlockingIOError:
                break
            except OSError:
                self._close_evdev(fd)
                return

            for offset in range(0, len(raw) - pkt_size + 1, pkt_size):
                _sec, _usec, ev_type, ev_code, ev_value = core.INPUT_EVENT_STRUCT.unpack_from(
                    raw, offset
                )
                self._process_input_event(ev_type, ev_code, ev_value)

    def _process_input_event(self, ev_type, ev_code, ev_value):
        if ev_type == core.EV_MSC and ev_code == core.MSC_SCAN:
            self._pending_scancode = ev_value
            return
        if ev_type != core.EV_KEY:
            return
        scan = self._pending_scancode
        self._pending_scancode = 0
        if ev_value != 1:
            return

        now = time.monotonic()
        if ev_code in core.GMODE_KEYCODES or scan in core.GMODE_SCANCODES:
            if now - self._last_gmode_ts > 0.25:
                self._last_gmode_ts = now
                self.toggle_g_mode(notify=True)
            return

        if ev_code in core.BACKLIGHT_KEYCODES or scan in core.BACKLIGHT_SCANCODES:
            if now - self._last_backlight_ts > 0.20:
                self._last_backlight_ts = now
                self.cycle_backlight_mode(notify=True)

    def _on_telemetry_tick(self):
        if self._poll_busy or self._power_busy:
            return True
        self._poll_busy = True
        generation = self._power_generation
        def worker():
            data = core.read_telemetry()
            profile = core.get_power_profile()
            label = core.daemon_status_label()
            self._pollFinished.emit(data, profile, label, generation)
        threading.Thread(target=worker, daemon=True).start()
        return True

    def _on_poll_done(self, data, profile, label, generation):
        self._poll_busy = False
        if generation != self._power_generation or self._power_busy:
            return False
        self.telemetry = data
        self.active_power_profile = profile
        self._daemon_label = label
        self.tray.setToolTip(f"{label} • {core.format_telemetry_label(data)}")
        if not self.tray_menu.isVisible():
            self._rebuild_tray_menu()
        self.telemetryChanged.emit()
        return False

    def _refresh_all(self):
        self._rebuild_tray_menu()
        self.configChanged.emit()
        self.telemetryChanged.emit()
        self.updateStateChanged.emit()

    # --- Updates ---
    def check_for_updates_async(self, manual=False):
        notice = core.local_build_update_notice(self.local_commit)
        if notice:
            if manual:
                self.send_osd_notification(core.tr("Versão local", "Local build"), notice)
            return

        if self._checking_update or self._updating_app:
            return
        self._checking_update = True
        self.updateStateChanged.emit()

        def worker():
            remote_sha = ""
            commit_msg = ""
            err_msg = ""
            try:
                remote_sha, commit_msg = core.fetch_latest_github_commit()
            except Exception as exc:
                err_msg = str(exc)
            self._updateCheckFinished.emit(remote_sha, commit_msg, manual, err_msg)

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_check_done(self, remote_sha, commit_msg, manual, err_msg):
        self._checking_update = False
        self.local_commit, self.repo_dir = core.read_local_version()

        if not remote_sha:
            self.updateStateChanged.emit()
            if manual:
                self.send_osd_notification(
                    core.tr("⚠️ Erro ao Verificar Atualizações", "⚠️ Update Check Failed"),
                    core.tr(
                        f"Não foi possível conectar ao GitHub: {err_msg}",
                        f"Could not reach GitHub: {err_msg}",
                    ),
                )
            return

        if not core.is_commit_same_or_ahead(self.local_commit, remote_sha, self.repo_dir):
            self.update_available = True
            self.latest_commit = remote_sha
            self.latest_commit_msg = commit_msg
            self._refresh_all()
            if manual or self._notified_commit != remote_sha:
                self._notified_commit = remote_sha
                self.send_osd_notification(
                    core.tr("🔄 Atualização Disponível!", "🔄 Update Available!"),
                    core.tr(
                        f"Nova versão ({remote_sha[:7]}): {commit_msg}. Abra o menu ou painel para instalar em 1 clique.",
                        f"New version ({remote_sha[:7]}): {commit_msg}. Open tray or panel to install in 1 click.",
                    ),
                )
        else:
            self.update_available = False
            self.latest_commit = self.local_commit
            self._refresh_all()
            if manual:
                short_sha = self.local_commit[:7]
                self.send_osd_notification(
                    core.tr("✅ Aplicativo Atualizado", "✅ Application Up to Date"),
                    core.tr(
                        f"Você já está na versão mais recente (#{short_sha}).",
                        f"You are already running the latest version (#{short_sha}).",
                    ),
                )
                self.toastMessage.emit(
                    core.tr(
                        f"Você já está na versão mais recente (#{short_sha})!",
                        f"You are already on the latest version (#{short_sha})!",
                    )
                )

    def perform_self_update_async(self):
        notice = core.local_build_update_notice(self.local_commit)
        if notice:
            self.send_osd_notification(core.tr("Versão local", "Local build"), notice)
            return

        if self._updating_app:
            return
        self._updating_app = True
        self.updateStateChanged.emit()
        self.send_osd_notification(
            core.tr("⏳ Atualizando Dell G15 Control...", "⏳ Updating Dell G15 Control..."),
            core.tr(
                "Baixando arquivos mais recentes do GitHub...",
                "Downloading latest files from GitHub...",
            ),
        )

        def worker():
            err_msg = ""
            target_sha = self.latest_commit
            try:
                if not target_sha or target_sha == "unknown":
                    target_sha, _msg = core.fetch_latest_github_commit()
                target_sha = core.stage_and_apply_update(
                    target_sha,
                    files_map=core.UPDATE_FILES_MAP,
                    repo_dir=self.repo_dir,
                )
            except Exception as exc:
                err_msg = str(exc)
            self._selfUpdateFinished.emit(target_sha, err_msg)

        threading.Thread(target=worker, daemon=True).start()

    def _on_self_update_done(self, target_sha, err_msg):
        self._updating_app = False
        if err_msg:
            self.updateStateChanged.emit()
            self.send_osd_notification(
                core.tr("❌ Falha na Atualização", "❌ Update Failed"),
                core.tr(f"Erro ao atualizar: {err_msg}", f"Error updating: {err_msg}"),
            )
            return

        self.local_commit = target_sha or self.local_commit
        self.update_available = False
        self._refresh_all()
        short_sha = self.local_commit[:7] if self.local_commit else "new"
        self.send_osd_notification(
            core.tr("✅ Atualização Concluída!", "✅ Update Complete!"),
            core.tr(
                f"Versão #{short_sha} instalada! Reiniciando serviços automaticamente...",
                f"Version #{short_sha} installed! Automatically restarting services...",
            ),
        )
        ok, detail = core.restart_systemd_services()
        if not ok:
            self.send_osd_notification(
                core.tr("Falha ao reiniciar serviços", "Service restart failed"), detail
            )

    def handle_cli_args(self, args):
        if "--toggle-gmode" in args:
            self.toggle_g_mode(notify=True)
        elif "--cycle-backlight" in args:
            self.cycle_backlight_mode(notify=True)
        elif "--check-update" in args:
            self.check_for_updates_async(manual=True)
        elif "--self-update" in args:
            self.perform_self_update_async()
        elif "--show" in args or not self.start_hidden:
            self.present_control_window()


def _send_to_existing_qt_instance(args):
    if not HAS_QT_NETWORK:
        return False
    sock = QLocalSocket()
    sock.connectToServer(SINGLE_INSTANCE_KEY)
    if not sock.waitForConnected(250):
        return False
    payload = json.dumps(args).encode("utf-8") + b"\n"
    sock.write(payload)
    sock.flush()
    sock.waitForBytesWritten(250)
    sock.disconnectFromServer()
    return True


def run_qt_app(argv):
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    app = QApplication(argv)
    app.setApplicationName("Dell G15 Control Center")
    app.setDesktopFileName("io.github.murilogiatti.DellG15Control")
    app.setQuitOnLastWindowClosed(False)

    icon_svg = os.path.join(core.ASSETS_DIR, "logo.svg")
    if os.path.exists(icon_svg):
        app.setWindowIcon(QIcon(icon_svg))

    cli_args = argv[1:]
    if _send_to_existing_qt_instance(cli_args or ["--show"]):
        return 0

    runtime = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.RuntimeLocation)
    startup_lock = QLockFile(os.path.join(runtime, "dell-g15-startup.lock"))
    if not startup_lock.tryLock(2000):
        raise RuntimeError("Another control-center instance is starting")
    if _send_to_existing_qt_instance(cli_args or ["--show"]):
        startup_lock.unlock()
        return 0
    server = QLocalServer(app)
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    if not server.listen(SINGLE_INSTANCE_KEY):
        if _send_to_existing_qt_instance(cli_args or ["--show"]):
            return 0
        # Only recover a stale endpoint; a concurrent startup may already own it.
        if server.serverError() == QAbstractSocket.SocketError.AddressInUseError:
            QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
        if not server.listen(SINGLE_INSTANCE_KEY):
            raise RuntimeError(server.errorString())

    start_hidden = "--show" not in cli_args
    controller = G15QtController(app, start_hidden=start_hidden)
    app.aboutToQuit.connect(controller.close)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    engine.loadData(QByteArray(_build_kirigami_qml().encode("utf-8")), QUrl("qrc:/DellG15Control.qml"))
    if not engine.rootObjects():
        controller.close()
        raise RuntimeError(core.format_missing_backend_instructions(
            "qt", reason="missing_qml_module", detail="Failed loading control-center QML"))

    def on_new_connection():
        while server.hasPendingConnections():
            conn = server.nextPendingConnection()
            buf = bytearray()
            def receive(conn=conn, buf=buf):
                buf.extend(bytes(conn.readAll()))
                if len(buf) > 65536:
                    conn.abort()
                    return
                if b"\n" not in buf:
                    return
                try:
                    args = json.loads(bytes(buf).split(b"\n", 1)[0])
                    if isinstance(args, list) and all(isinstance(a, str) for a in args):
                        controller.handle_cli_args(args)
                except (ValueError, TypeError):
                    pass
                conn.disconnectFromServer()
            conn.readyRead.connect(receive)
            conn.disconnected.connect(conn.deleteLater)
            receive()
    server.newConnection.connect(on_new_connection)
    on_new_connection()

    if cli_args:
        controller.handle_cli_args(cli_args)

    startup_lock.unlock()
    return app.exec()
