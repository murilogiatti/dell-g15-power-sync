#!/usr/bin/env python3
"""
Dell G15 Control Center — Shared Toolkit-Agnostic Core Module (`g15_core`).
Zero GUI toolkit imports (never imports `gi`, `Gtk`, `Adw`, `PyQt6`, or `PySide6`).
Data-Oriented Design: flat lookup tables for presets, effects, brightness tiers,
hotkeys, hardware telemetry, power profiles, atomic config, diagnostics, and self-updater.
"""

import base64
import glob
import json
import os
import re
import struct
import subprocess
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

# --- Configuration & Asset Paths ---
CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "dell-g15"
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DATA_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), "dell-g15"
)
REPO_ASSETS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets")
)
ASSETS_DIR = DATA_DIR if os.path.isdir(DATA_DIR) else REPO_ASSETS_DIR
VERSION_FILE = os.path.join(DATA_DIR, "version.json")

GITHUB_REPO = "murilogiatti/dell-g15-power-sync"
GITHUB_API_COMMITS_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RAW_REPO_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}"

UPDATE_FILES_MAP = (
    ("bin/g15-daemon", os.path.expanduser("~/.local/bin/g15-daemon"), 0o755),
    ("bin/g15-tray", os.path.expanduser("~/.local/bin/g15-tray"), 0o755),
    ("bin/g15_install.py", os.path.expanduser("~/.local/bin/g15_install.py"), 0o644),
    ("bin/g15_config.py", os.path.expanduser("~/.local/bin/g15_config.py"), 0o644),
    ("bin/g15_core.py", os.path.expanduser("~/.local/bin/g15_core.py"), 0o644),
    ("bin/g15_gtk.py", os.path.expanduser("~/.local/bin/g15_gtk.py"), 0o644),
    ("bin/g15_qt.py", os.path.expanduser("~/.local/bin/g15_qt.py"), 0o644),
    ("assets/banner.svg", os.path.join(DATA_DIR, "banner.svg"), 0o644),
    ("assets/logo.svg", os.path.join(DATA_DIR, "logo.svg"), 0o644),
    ("assets/logo.png", os.path.join(DATA_DIR, "logo.png"), 0o644),
    ("assets/tray-icon.svg", os.path.join(DATA_DIR, "tray-icon.svg"), 0o644),
    ("assets/tray-icon.png", os.path.join(DATA_DIR, "tray-icon.png"), 0o644),
    (
        "assets/logo.svg",
        os.path.join(os.path.dirname(DATA_DIR), "icons/hicolor/scalable/apps/io.github.murilogiatti.DellG15Control.svg"),
        0o644,
    ),
    (
        "assets/logo.png",
        os.path.join(os.path.dirname(DATA_DIR), "icons/hicolor/256x256/apps/io.github.murilogiatti.DellG15Control.png"),
        0o644,
    ),
    (
        "assets/logo.svg",
        os.path.join(os.path.dirname(DATA_DIR), "icons/hicolor/scalable/apps/dell-g15-control.svg"),
        0o644,
    ),
    (
        "assets/logo.png",
        os.path.join(os.path.dirname(DATA_DIR), "icons/hicolor/256x256/apps/dell-g15-control.png"),
        0o644,
    ),
    (
        "assets/tray-icon.svg",
        os.path.join(os.path.dirname(DATA_DIR), "icons/hicolor/scalable/status/tray-icon.svg"),
        0o644,
    ),
    (
        "assets/tray-icon.png",
        os.path.join(os.path.dirname(DATA_DIR), "icons/hicolor/64x64/status/tray-icon.png"),
        0o644,
    ),
    (
        "systemd/dell-g15-daemon.service",
        os.path.join(os.path.dirname(CONFIG_DIR), "systemd/user/dell-g15-daemon.service"),
        0o644,
    ),
    (
        "systemd/dell-g15-tray.service",
        os.path.join(os.path.dirname(CONFIG_DIR), "systemd/user/dell-g15-tray.service"),
        0o644,
    ),
)

VALID_MODES = ("static", "breathing", "pulse", "morph", "spectrum", "rainbow")

# Maximum 25-zone spectrum EEPROM write is 106 HID packets (~5.3s of ioctl delays alone).
# Use a bounded 30-second budget including controller discovery and ioctl overhead.
BOOT_SAVE_TIMEOUT_SEC = 30



# --- Linux evdev Input Constants (Fn+F9 G-Mode & Fn+F5 Backlight Hotkeys) ---
INPUT_EVENT_STRUCT = struct.Struct("llHHi")
EV_KEY = 0x01
EV_MSC = 0x04
MSC_SCAN = 0x04

GMODE_SCANCODES = (0x68, 0x12000C)
GMODE_KEYCODES = (701, 594, 595)  # KEY_PERFORMANCE / G-Mode

BACKLIGHT_SCANCODES = (
    0x69,
    0x95,
    0x10001E,
    0x10001F,
    0x100020,
    0x100021,
    0x100022,
    0x100851,
    0x100852,
)
BACKLIGHT_KEYCODES = (188, 228, 229, 230, 659)  # KEY_F18 (Dell G15 Fn+F5) / KBDILLUM / MACRO4

# --- Data-Oriented Lookup Tables ---
BRIGHTNESS_STEPS = (0, 10, 30, 50, 75, 100)

# Primary + extended pre-selected color palette: (id_code, hex_rgb, label_pt, label_en)
COLOR_PRESETS = (
    ("white", "E6E6E6", "Branco Puro", "Pure White"),
    ("ice", "80D8FF", "Azul Gelo", "Ice Blue"),
    ("cyan", "00E5FF", "Ciano Alienware", "Alienware Cyan"),
    ("blue", "2979FF", "Azul Cobalto", "Cobalt Blue"),
    ("teal", "1DE9B6", "Turquesa", "Turquoise"),
    ("green", "00E676", "Verde Matrix", "Matrix Green"),
    ("gold", "FFD600", "Ouro Solar", "Solar Gold"),
    ("amber", "FFB366", "Âmbar Conforto", "Warm Amber"),
    ("orange", "FF6D00", "Laranja", "Orange"),
    ("red", "FF2200", "Vermelho G15", "G15 Red"),
    ("pink", "F50057", "Magenta", "Magenta"),
    ("purple", "B388FF", "Roxo Neon", "Neon Purple"),
)

# (mode_key, label_pt, label_en)
EFFECT_MODES = (
    ("static", "Estático (Cor Fixa)", "Static (Solid Color)"),
    ("breathing", "Respiração (Fade Suave)", "Breathing (Smooth Fade)"),
    ("pulse", "Pulso (Piscada Rápida)", "Pulse (Quick Flash)"),
    ("morph", "Transição entre 2 Cores (Morph)", "Two-Color Transition (Morph)"),
    ("spectrum", "Ciclo Contínuo de Cores (Spectrum)", "Continuous Color Cycle (Spectrum)"),
    ("rainbow", "Ondas Arco-Íris por Zona (Rainbow)", "Per-Zone Rainbow Wave"),
)

# (profile_id, label_pt, label_en)
POWER_PROFILES = (
    ("power-saver", "🌱 Economia de Energia (Silencioso)", "🌱 Power Saver (Quiet)"),
    ("balanced", "⚖️ Equilibrado (Padrão)", "⚖️ Balanced (Default)"),
    ("performance", "🚀 Alto Desempenho (G-Mode)", "🚀 High Performance (G-Mode)"),
)

IS_PT = os.environ.get("LANG", "").lower().startswith("pt")


def tr(pt_str, en_str):
    return pt_str if IS_PT else en_str


# --- Immutable System Detection ---
def is_immutable_system(root_prefix="/", os_release_path="/etc/os-release"):
    """
    Returns True on ostree/immutable Linux distributions (Fedora Silverblue,
    Fedora Kinoite, Universal Blue, MicroOS, etc.).
    """
    if os.path.exists(os.path.join(root_prefix, "run/ostree-booted")):
        return True
    if os.path.exists(os.path.join(root_prefix, "ostree")):
        return True
    try:
        if os.path.exists(os_release_path):
            with open(os_release_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
            for marker in ("variant_id=silverblue", "variant_id=kinoite", "ostree", "atomic"):
                if marker in content:
                    return True
    except OSError:
        pass
    return False


# --- Desktop & Backend Resolution ---
def detect_desktop_backend(env=None):
    """
    Resolves the native UI backend ('gtk' or 'qt') from environment variables.
    Handles composite XDG_CURRENT_DESKTOP strings such as:
    - 'ubuntu:GNOME', 'GNOME', 'GNOME-Classic:GNOME' -> 'gtk'
    - 'KDE', 'ubuntu:KDE', 'plasma' -> 'qt'
    """
    environ = env if env is not None else os.environ
    explicit = str(environ.get("G15_UI_BACKEND", "")).strip().lower()
    if explicit in ("gtk", "gnome", "adw", "libadwaita"):
        return "gtk"
    if explicit in ("qt", "kde", "plasma", "kirigami"):
        return "qt"

    raw_xdg = str(environ.get("XDG_CURRENT_DESKTOP", "")).lower()
    tokens = [t.strip() for t in raw_xdg.replace(";", ":").split(":") if t.strip()]
    for tok in tokens:
        if tok in ("kde", "plasma") or "kde" in tok or "plasma" in tok:
            return "qt"
    for tok in tokens:
        if (
            tok in ("gnome", "ubuntu", "unity", "budgie", "cinnamon", "pantheon", "xfce", "mate")
            or "gnome" in tok
        ):
            return "gtk"

    session = str(environ.get("DESKTOP_SESSION", "")).lower()
    if "kde" in session or "plasma" in session:
        return "qt"
    if "gnome" in session or "ubuntu" in session:
        return "gtk"

    if str(environ.get("KDE_FULL_SESSION", "")).lower() in ("true", "1"):
        return "qt"

    return "gtk"


def parse_backend_override(argv, env=None):
    """
    Parses CLI arguments for `--backend gtk|qt` or `--backend=gtk|qt`
    and returns (backend_name, remaining_argv).
    Raises ValueError if an unsupported backend name is given.
    """
    remaining = [argv[0]] if argv else ["g15-tray"]
    explicit_backend = None
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--backend":
            if i + 1 >= len(argv):
                raise ValueError(
                    tr(
                        "O argumento --backend requer um valor: 'gtk' ou 'qt'.",
                        "The --backend argument requires a value: 'gtk' or 'qt'.",
                    )
                )
            explicit_backend = argv[i + 1].strip().lower()
            i += 2
            continue
        if arg.startswith("--backend="):
            explicit_backend = arg.split("=", 1)[1].strip().lower()
            i += 1
            continue
        remaining.append(arg)
        i += 1

    if explicit_backend is not None:
        if explicit_backend in ("gtk", "gnome", "adw", "libadwaita"):
            return "gtk", remaining
        if explicit_backend in ("qt", "kde", "plasma", "kirigami"):
            return "qt", remaining
        raise ValueError(
            tr(
                f"Backend desconhecido '{explicit_backend}'. Valores válidos: 'gtk' ou 'qt'.",
                f"Unknown backend '{explicit_backend}'. Valid values: 'gtk' or 'qt'.",
            )
        )

    return detect_desktop_backend(env=env), remaining


def format_missing_backend_instructions(backend, reason="missing_library", detail="", immutable=None):
    """Describe missing capabilities without proposing changes to the host image."""
    label = "GTK4/Libadwaita/PyGObject" if backend == "gtk" else "PyQt6/QtQuick/Kirigami6"
    reasons = {
        "missing_display": tr("Sessão gráfica indisponível", "Graphical session unavailable"),
        "missing_library": tr("Biblioteca ou binding ausente", "Library or binding missing"),
        "missing_qml_module": tr("Componente QML indisponível", "QML component unavailable"),
    }
    message = reasons.get(reason, reason) + f" ({label}).\n"
    message += tr(
        "Nenhum componente será instalado. Utilize apenas os componentes existentes.\n"
        "Alternativa sem GUI: ./install.sh --daemon-only\n"
        "CLI: g15-tray --headless --cycle-backlight ou --headless --toggle-gmode.\n"
        "O daemon ainda exige Python 3 e permissões HID já disponíveis.",
        "No components will be installed. Only existing system components are used.\n"
        "Without GUI: ./install.sh --daemon-only\n"
        "CLI: g15-tray --headless --cycle-backlight or --headless --toggle-gmode.\n"
        "The daemon still requires existing Python 3 and HID permissions.",
    )
    if detail:
        message += "\n" + detail
    return message


def _check_backend_dependencies(backend, require_display=False, env=None):
    """
    Side-effect-free dependency diagnostic for `backend` ('gtk' or 'qt').
    Does NOT start keyboard/evdev monitors, hardware I/O, network requests, or services.
    Distinguishes:
      - 'ok'
      - 'missing_display'
      - 'missing_library'
      - 'missing_qml_module'
    Returns (ok: bool, status_code: str, message: str).
    """
    environ = env if env is not None else os.environ
    has_display = bool(environ.get("WAYLAND_DISPLAY") or environ.get("DISPLAY"))
    if require_display and not has_display:
        msg = format_missing_backend_instructions(
            backend, reason="missing_display", detail="WAYLAND_DISPLAY and DISPLAY are unset"
        )
        return False, "missing_display", msg

    if backend == "gtk":
        probe_code = "\n".join(
            [
                "import sys",
                "try:",
                "    import gi",
                "    gi.require_version('Gtk', '4.0')",
                "    gi.require_version('Adw', '1')",
                "    from gi.repository import Gtk, Adw, Gio, GLib, Pango",
                "    assert all(hasattr(Gtk, name) for name in ('ColorDialog', 'ColorDialogButton')),'GTK ColorDialog API unavailable'",
                "    assert hasattr(Gtk.CssProvider, 'load_from_string'),'GTK CSS API unavailable'",
                "    assert all(hasattr(Adw, name) for name in ('SwitchRow', 'ToolbarView')),'Libadwaita controls unavailable'",
                "except Exception as exc:",
                "    print(f'MISSING_LIB:{exc}')",
                "    sys.exit(10)",
                "sys.exit(0)",
            ]
        )
        proc = subprocess.run(
            [sys.executable, "-c", probe_code],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode != 0:
            detail = (proc.stdout or proc.stderr or "").strip()
            return (
                False,
                "missing_library",
                format_missing_backend_instructions(
                    "gtk", reason="missing_library", detail=detail
                ),
            )
        return True, "ok", "OK (GTK 4.0 + Libadwaita 1)"

    if backend == "qt":
        # Verify both Python PyQt6 bindings AND actual QML module loading (including org.kde.kirigami)
        # using offscreen QPA if no display is active, without starting any services or hardware I/O.
        probe_code = "\n".join(
            [
                "import os, sys",
                "if not (os.environ.get('WAYLAND_DISPLAY') or os.environ.get('DISPLAY')):",
                "    os.environ['QT_QPA_PLATFORM'] = 'offscreen'",
                "try:",
                "    from PyQt6.QtCore import QByteArray, QObject, QUrl",
                "    from PyQt6.QtGui import QGuiApplication",
                "    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon",
                "    from PyQt6.QtQml import QQmlEngine, QQmlComponent",
                "    from PyQt6.QtQuick import QQuickWindow",
                "    from PyQt6.QtNetwork import QLocalServer, QLocalSocket",
                "except Exception as exc:",
                "    print(f'MISSING_LIB:{exc}')",
                "    sys.exit(10)",
                "app = QGuiApplication.instance() or QGuiApplication([])",
                "engine = QQmlEngine()",
                "qml_probe = b'''",
                "import QtQml",
                "import QtQuick",
                "import QtQuick.Layouts",
                "import QtQuick.Controls as QQC2",
                "import org.kde.kirigami as Kirigami",
                "QtObject {}",
                "'''",
                "comp = QQmlComponent(engine)",
                "comp.setData(QByteArray(qml_probe), QUrl('qrc:/probe.qml'))",
                "if comp.isError():",
                "    errs = '; '.join(e.toString() for e in comp.errors())",
                "    print(f'MISSING_QML:{errs}')",
                "    sys.exit(11)",
                "sys.exit(0)",
            ]
        )
        proc = subprocess.run(
            [sys.executable, "-c", probe_code],
            capture_output=True,
            text=True,
            timeout=8,
        )
        out = (proc.stdout or proc.stderr or "").strip()
        if proc.returncode == 10:
            return (
                False,
                "missing_library",
                format_missing_backend_instructions(
                    "qt", reason="missing_library", detail=out
                ),
            )
        if proc.returncode != 0:
            return (
                False,
                "missing_qml_module",
                format_missing_backend_instructions(
                    "qt", reason="missing_qml_module", detail=out
                ),
            )
        return True, "ok", "OK (PyQt6 + QtQuick + org.kde.kirigami)"

    return (
        False,
        "unknown_backend",
        f"Unknown backend: {backend}",
    )


def check_backend_dependencies(backend, require_display=False, env=None):
    try:
        return _check_backend_dependencies(backend, require_display, env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, "probe_failed", str(exc)


def probe_system_capabilities():
    """
    Side-effect-free probe of optional hardware/system capabilities:
      - hidraw_access: 'ok' | 'permission_denied' | 'device_not_found'
      - evdev_hotkeys: 'ok' | 'permission_denied' | 'device_not_found'
      - power_profiles: bool
      - sensors: dict of available sensors
      - immutable: bool
    """
    hid_status = "device_not_found"
    for sys_path in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        uevent_path = os.path.join(sys_path, "device", "uevent")
        try:
            with open(uevent_path, "r", encoding="utf-8") as f:
                content = f.read().upper()
            if "187C:00000550" in content or "187C:00000551" in content:
                dev_node = os.path.join("/dev", os.path.basename(sys_path))
                if os.access(dev_node, os.R_OK | os.W_OK):
                    hid_status = "ok"
                else:
                    hid_status = "permission_denied"
                break
        except OSError:
            continue

    evdev_nodes = discover_evdev_hotkey_nodes()
    if not evdev_nodes:
        evdev_status = "device_not_found"
    elif any(os.access(n, os.R_OK) for n in evdev_nodes):
        evdev_status = "ok"
    else:
        evdev_status = "permission_denied"

    return {
        "immutable": is_immutable_system(),
        "hidraw_access": hid_status,
        "evdev_hotkeys": evdev_status,
        "power_profiles_available": is_power_profiles_available(),
        "telemetry": read_telemetry(),
    }


# --- Config Sanitization & Atomic Persistence ---
# Shared configuration contains no graphical imports.
from g15_config import DEFAULT_CONFIG, VALID_MODES, normalize_config, config_lock
import g15_config as config_store


def load_config(path=None):
    return config_store.load_config(path or CONFIG_PATH)


def save_config(cfg, path=None):
    return config_store.save_config(cfg, path or CONFIG_PATH)


def update_config_preserving_concurrent_edits(mutator_fn, path=None):
    return config_store.update_config(mutator_fn, path or CONFIG_PATH)


def read_local_version(version_file=None):
    vfile = version_file or VERSION_FILE
    commit = "unknown"
    repo_dir = ""
    try:
        if os.path.exists(vfile):
            with open(vfile, "r", encoding="utf-8") as f:
                data = json.load(f)
                commit = str(data.get("commit", "unknown")).strip()
                repo_dir = str(data.get("repo_dir", "")).strip()
    except (OSError, ValueError):
        pass

    return commit, repo_dir


def write_local_version(commit, repo_dir="", version_file=None):
    vfile = version_file or VERSION_FILE
    os.makedirs(os.path.dirname(vfile), exist_ok=True)
    payload = {"commit": commit, "repo_dir": repo_dir}
    tmp_path = f"{vfile}.tmp.{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    os.replace(tmp_path, vfile)


def local_build_update_notice(commit):
    if re.fullmatch(r"[0-9a-fA-F]{40}", str(commit or "")):
        return ""
    return tr(
        "Esta instalação contém alterações locais ainda não publicadas. "
        "A atualização pelo GitHub ficará disponível após publicar e instalar uma versão correspondente. "
        "Para reaplicar os arquivos locais, execute ./install.sh no repositório.",
        "This installation contains unpublished local changes. "
        "GitHub updates require publishing and installing a matching version first. "
        "To reinstall local files, run ./install.sh from the repository.",
    )


def fetch_latest_github_commit():
    """Resolve an approved non-prerelease GitHub release tag to an immutable SHA."""
    base = f"https://api.github.com/repos/{GITHUB_REPO}"
    def request(path):
        req = urllib.request.Request(base + path, headers={"User-Agent": "Dell-G15-Control-Center/2.0", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=8) as response:
            return json.load(response)
    try:
        release = request("/releases/latest")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(tr("Nenhuma versão estável publicada ainda", "No stable release published yet")) from exc
        raise
    if release.get("draft") or release.get("prerelease") or not release.get("tag_name"):
        raise ValueError("Invalid stable release metadata")
    tag = urllib.parse.quote(release["tag_name"], safe="")
    commit = request("/commits/" + tag)
    sha = str(commit.get("sha", ""))
    if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        raise ValueError("Release did not resolve to a complete SHA")
    return sha, str(release.get("name") or release["tag_name"])


def is_commit_same_or_ahead(local_commit, remote_sha, repo_dir=""):
    if not remote_sha:
        return True
    if remote_sha == local_commit:
        return True
    if repo_dir and os.path.isdir(repo_dir) and local_commit and local_commit != "unknown":
        try:
            rc = subprocess.call(
                [
                    "git",
                    "-C",
                    repo_dir,
                    "merge-base",
                    "--is-ancestor",
                    remote_sha,
                    local_commit,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            if rc == 0:
                return True
        except Exception:
            pass
    return False


class UpdateError(RuntimeError):
    """Structured update error exposing the exact failure stage and any rollback errors."""

    def __init__(self, stage, message, rollback_errors=None):
        super().__init__(message)
        self.stage = stage
        self.rollback_errors = list(rollback_errors or [])


def stage_and_apply_update(
    target_sha,
    files_map=UPDATE_FILES_MAP,
    fetcher=None,
    repo_dir="",
    version_file=None,
    replace_fn=None,
):
    """
    Downloads all unique repository files pinned to `target_sha`, validates payloads
    (including Python syntax compilation for scripts/modules), stages every destination
    file as a sibling `.staged.<pid>.<idx>` file, and swaps each file into place with
    best-effort user-space rollback if an error occurs mid-swap.

    Note: Individual `os.replace` swaps with in-process rollback protect against network,
    validation, and filesystem errors during execution, but do not constitute an OS-level
    atomic transaction across abrupt process kill (SIGKILL) or power loss.
    Never modifies the development git checkout.
    """
    clean_sha = str(target_sha or "").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", clean_sha):
        raise UpdateError("download", "Missing target commit SHA for update")

    def _default_fetch(url):
        req = urllib.request.Request(
            url, headers={"User-Agent": "Dell-G15-Control-Center/1.0"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.read()

    fetch_fn = fetcher or _default_fetch
    do_replace = replace_fn or os.replace

    # Stage 1: Download & validate all unique relative paths from the exact commit SHA
    payload_cache = {}
    try:
        for rel_path, _dest_path, _mode in files_map:
            if rel_path in payload_cache:
                continue
            url = f"{GITHUB_RAW_REPO_URL}/{clean_sha}/{rel_path}"
            try:
                content = fetch_fn(url)
            except Exception as exc:
                raise RuntimeError(f"{rel_path} @ {clean_sha[:7]}: {exc}") from exc
            if not content:
                raise ValueError(f"Downloaded empty file for {rel_path}")
            if rel_path.startswith("bin/"):
                compile(content.decode("utf-8"), rel_path, "exec")
            payload_cache[rel_path] = content
    except Exception as exc:
        raise UpdateError("download", f"Download/validation failed: {exc}") from exc

    vfile = version_file or VERSION_FILE
    old_version = None
    if os.path.exists(vfile):
        with open(vfile, "rb") as stream:
            old_version = stream.read()
    # Stage 2: Write all staged files next to their destinations before replacing any target
    pid = os.getpid()
    staged_entries = []
    staged_paths = []
    backups = []
    try:
        for idx, (rel_path, dest_path, mode) in enumerate(files_map):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            staged_path = f"{dest_path}.staged.{pid}.{idx}"
            staged_paths.append(staged_path)
            with open(staged_path, "wb") as f:
                f.write(payload_cache[rel_path])
            os.chmod(staged_path, mode)
            prev_bytes = None
            prev_mode = mode
            if os.path.exists(dest_path):
                with open(dest_path, "rb") as bf:
                    prev_bytes = bf.read()
                prev_mode = os.stat(dest_path).st_mode & 0o777
            staged_entries.append((staged_path, dest_path, prev_bytes, prev_mode))

        # Retain one previous version on disk before applying the new one.
        snapshot = [(dest, old, mode) for _tmp, dest, old, mode in staged_entries]
        snapshot.append((vfile, old_version, 0o600))
        write_update_backup(snapshot, vfile)
        # Stage 3: Swap all staged files into place, rolling back on any error
        for staged_path, dest_path, prev_bytes, prev_mode in staged_entries:
            do_replace(staged_path, dest_path)
            backups.append((dest_path, prev_bytes, prev_mode))
    except Exception as apply_exc:
        rollback_errors = []
        for dest_path, prev_bytes, prev_mode in reversed(backups):
            try:
                if prev_bytes is None:
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                else:
                    rb_tmp = f"{dest_path}.rollback.{pid}"
                    with open(rb_tmp, "wb") as rf:
                        rf.write(prev_bytes)
                    os.chmod(rb_tmp, prev_mode)
                    os.replace(rb_tmp, dest_path)
            except Exception as rb_exc:
                rollback_errors.append(f"{dest_path}: {rb_exc}")

        for staged_path in staged_paths:
            if os.path.exists(staged_path):
                try:
                    os.remove(staged_path)
                except OSError:
                    pass

        if rollback_errors:
            raise UpdateError(
                "rollback",
                f"Apply failed ({apply_exc}) and rollback encountered errors: {'; '.join(rollback_errors)}",
                rollback_errors=rollback_errors,
            ) from apply_exc
        raise UpdateError("apply", f"Failed applying update (rolled back cleanly): {apply_exc}") from apply_exc

    # Stage 4: Record installed version in user data dir (never touches development git checkout)
    try:
        write_local_version(clean_sha, repo_dir, version_file=version_file)
    except Exception as ver_exc:
        raise UpdateError(
            "version_record",
            f"Files updated to {clean_sha[:7]}, but failed recording version.json: {ver_exc}",
        ) from ver_exc

    return clean_sha


def write_update_backup(entries, version_file):
    path = os.path.join(os.path.dirname(version_file), "update-rollback.json")
    config_store.write_json(path, [{"path": str(dest), "mode": mode,
        "data": None if content is None else base64.b64encode(content).decode("ascii")}
        for dest, content, mode in entries])


def restore_previous_update(version_file=None, files_map=None):
    """Explicit rollback; destinations are restricted to the installed application manifest."""
    vfile = version_file or VERSION_FILE
    path = os.path.join(os.path.dirname(vfile), "update-rollback.json")
    allowed = {str(dest) for _rel, dest, _mode in (files_map or UPDATE_FILES_MAP)} | {str(vfile)}
    if files_map is None:
        allowed.add(os.path.join(os.path.dirname(DATA_DIR), "applications/io.github.murilogiatti.DellG15Control.desktop"))
    with config_lock(path):
        with open(path, encoding="utf-8") as stream:
            records = json.load(stream)
        if not isinstance(records, list) or any(not isinstance(r, dict) or r.get("path") not in allowed for r in records):
            raise ValueError("Invalid rollback destinations")
        if len({r["path"] for r in records}) != len(records):
            raise ValueError("Duplicate rollback destinations")
        decoded = []
        for record in records:
            if type(record.get("mode")) is not int or not 0 <= record["mode"] <= 0o777:
                raise ValueError("Invalid rollback permissions")
            if "data" not in record or (record["data"] is not None and not isinstance(record["data"], str)):
                raise ValueError("Invalid rollback payload")
            try:
                content = None if record["data"] is None else base64.b64decode(record["data"], validate=True)
            except ValueError as exc:
                raise ValueError("Invalid rollback payload encoding") from exc
            decoded.append((record, content))
        prepared, previous, applied = [], [], []
        import tempfile
        try:
            for record, content in decoded:
                dest = record["path"]
                old = None
                if os.path.exists(dest):
                    with open(dest, "rb") as stream:
                        old = stream.read()
                previous.append((dest, old, os.stat(dest).st_mode & 0o777 if old is not None else 0o600))
                tmp = None
                if content is not None:
                    fd, tmp = tempfile.mkstemp(prefix=".g15-rollback-", dir=os.path.dirname(dest))
                    prepared.append((dest, tmp))
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(content)
                    os.chmod(tmp, int(record["mode"]) & 0o777)
                else:
                    prepared.append((dest, None))
            for dest, tmp in prepared:
                if tmp is None:
                    if os.path.exists(dest): os.unlink(dest)
                else:
                    os.replace(tmp, dest)
                applied.append(dest)
        except Exception as apply_error:
            recovery_errors = []
            for dest, content, mode in reversed(previous[:len(applied)]):
                tmp = None
                try:
                    if content is None:
                        if os.path.exists(dest): os.unlink(dest)
                    else:
                        fd, tmp = tempfile.mkstemp(prefix=".g15-recover-", dir=os.path.dirname(dest))
                        with os.fdopen(fd, "wb") as stream: stream.write(content)
                        os.chmod(tmp, mode)
                        os.replace(tmp, dest)
                except Exception as recovery_error:
                    recovery_errors.append(f"{dest}: {recovery_error}; retained recovery file: {tmp}")
            if recovery_errors:
                raise UpdateError("rollback", f"Restore failed ({apply_error}); recovery errors: {'; '.join(recovery_errors)}",
                                  rollback_errors=recovery_errors) from apply_error
            raise
        finally:
            for _dest, tmp in prepared:
                if tmp and os.path.exists(tmp): os.unlink(tmp)
        write_update_backup(previous, vfile)
    return read_local_version(vfile)[0]


def restart_systemd_services():
    """Queue restart without waiting for the service containing this process to stop."""
    units = ["dell-g15-daemon.service", "dell-g15-tray.service"]
    try:
        for args in (["daemon-reload"], ["--no-block", "restart", *units]):
            result = subprocess.run(["systemctl", "--user", *args],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode:
                return False, result.stderr.strip() or f"systemctl {args}: {result.returncode}"
        return True, "Restart queued; check systemctl --user status for completion."
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)


# --- Flat Hardware Telemetry Reader (/sys/class/hwmon) ---
def daemon_status_label():
    try:
        with open(os.path.join(CONFIG_DIR, "daemon-status.json"), encoding="utf-8") as stream:
            status = json.load(stream)
        if not isinstance(status, dict) or type(status.get("pid")) is not int or status["pid"] <= 0:
            raise ValueError("Invalid daemon status")
        os.kill(status["pid"], 0)
        if status.get("hardware_ok"):
            return tr("Daemon ativo • Controlador OK", "Daemon active • Controller OK")
        return tr("Daemon ativo • Controlador indisponível ou aplicação falhou", "Daemon active • Controller unavailable or write failed")
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return tr("Daemon indisponível ou sem diagnóstico", "Daemon unavailable or no status")


def read_telemetry(hwmon_root="/sys/class/hwmon"):
    """
    Returns flat dict: cpu_c, gpu_c, nvme_c, fan1_rpm, fan2_rpm.
    Values are integer readings or `None` when a sensor is absent/unreadable
    (never reports `0` as a fake temperature or fan reading when the sensor is missing).
    """
    data = {
        "cpu_c": None,
        "gpu_c": None,
        "nvme_c": None,
        "fan1_rpm": None,
        "fan2_rpm": None,
    }
    for hw_dir in sorted(glob.glob(os.path.join(hwmon_root, "hwmon*"))):
        try:
            with open(os.path.join(hw_dir, "name"), "r", encoding="utf-8") as f:
                name = f.read().strip()
        except OSError:
            continue

        if name in ("k10temp", "coretemp") and data["cpu_c"] is None:
            try:
                with open(os.path.join(hw_dir, "temp1_input"), "r", encoding="utf-8") as f:
                    data["cpu_c"] = int(f.read().strip()) // 1000
            except (OSError, ValueError):
                pass
        elif name in ("amdgpu", "nouveau") and data["gpu_c"] is None:
            try:
                with open(os.path.join(hw_dir, "temp1_input"), "r", encoding="utf-8") as f:
                    data["gpu_c"] = int(f.read().strip()) // 1000
            except (OSError, ValueError):
                pass
        elif name == "nvme" and data["nvme_c"] is None:
            try:
                with open(os.path.join(hw_dir, "temp1_input"), "r", encoding="utf-8") as f:
                    data["nvme_c"] = int(f.read().strip()) // 1000
            except (OSError, ValueError):
                pass
        elif name in ("alienware_wmi", "dell_smm", "dell_ddv"):
            for idx, key in ((1, "fan1_rpm"), (2, "fan2_rpm")):
                if data[key] is not None:
                    continue
                try:
                    with open(
                        os.path.join(hw_dir, f"fan{idx}_input"), "r", encoding="utf-8"
                    ) as f:
                        val = int(f.read().strip())
                        if val >= 0:
                            data[key] = val
                except (OSError, ValueError):
                    pass
    return data


def _fmt_temp(val):
    return f"{val}°C" if val is not None else "N/A"


def _fmt_fans(f1, f2):
    if f1 is None and f2 is None:
        return "N/A"
    v1 = str(f1) if f1 is not None else "N/A"
    v2 = str(f2) if f2 is not None else "N/A"
    return f"{v1}/{v2} RPM"


def format_telemetry_label(t):
    cpu_s = _fmt_temp(t.get("cpu_c"))
    gpu_s = _fmt_temp(t.get("gpu_c"))
    fans_s = _fmt_fans(t.get("fan1_rpm"), t.get("fan2_rpm"))
    return f"🌡️ CPU {cpu_s} • GPU {gpu_s} • 💨 {fans_s}"


def format_detailed_telemetry_label(t):
    cpu_s = _fmt_temp(t.get("cpu_c"))
    gpu_s = _fmt_temp(t.get("gpu_c"))
    nvme_s = _fmt_temp(t.get("nvme_c"))
    fans_s = _fmt_fans(t.get("fan1_rpm"), t.get("fan2_rpm"))
    return f"CPU {cpu_s} • GPU {gpu_s} • NVMe {nvme_s} • {fans_s}"


# --- Toolkit-Agnostic Power Profile Management ---
def _read_power_profile_raw():
    try:
        out = subprocess.check_output(
            ["powerprofilesctl", "get"],
            stderr=subprocess.DEVNULL,
            timeout=1.5,
        )
        prof = out.decode("utf-8").strip()
        if prof in ("power-saver", "balanced", "performance"):
            return prof
    except Exception:
        pass
    try:
        out = subprocess.check_output(
            [
                "busctl",
                "--system",
                "get-property",
                "org.freedesktop.UPower.PowerProfiles",
                "/org/freedesktop/UPower/PowerProfiles",
                "org.freedesktop.UPower.PowerProfiles",
                "ActiveProfile",
            ],
            stderr=subprocess.DEVNULL,
            timeout=1.5,
        ).decode("utf-8")
        for p in ("power-saver", "balanced", "performance"):
            if f'"{p}"' in out:
                return p
    except Exception:
        pass
    return None


def is_power_profiles_available():
    return _read_power_profile_raw() is not None


def get_power_profile():
    return _read_power_profile_raw()


def set_power_profile(profile_name):
    if profile_name not in ("power-saver", "balanced", "performance"):
        return False
    try:
        rc = subprocess.call(
            ["powerprofilesctl", "set", profile_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
        if rc == 0:
            return True
    except Exception:
        pass
    try:
        rc = subprocess.call(
            [
                "busctl",
                "--system",
                "set-property",
                "org.freedesktop.UPower.PowerProfiles",
                "/org/freedesktop/UPower/PowerProfiles",
                "org.freedesktop.UPower.PowerProfiles",
                "ActiveProfile",
                "s",
                profile_name,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
        return rc == 0
    except Exception:
        return False


# --- Shared Business Logic Transitions (G-Mode, Backlight Cycle, Brightness Step, Boot Save) ---
def apply_g_mode_transition(
    cfg,
    target_state=None,
    get_profile_fn=None,
    set_profile_fn=None,
    save_fn=None,
):
    """
    Executes the G-Mode state transition on `cfg` in-place.
    Returns (changed: bool, active_profile: str, notif_title: str, notif_body: str).
    """
    get_prof = get_profile_fn or get_power_profile
    set_prof = set_profile_fn or set_power_profile
    persist = save_fn or save_config

    cur_gmode = bool(cfg.get("g_mode", False))
    new_gmode = (not cur_gmode) if target_state is None else bool(target_state)
    if new_gmode == cur_gmode:
        return False, get_prof(), "", ""

    if new_gmode:
        prev_profile = get_prof()
        cfg["pre_gmode"] = {
            "mode": cfg.get("mode", "static"),
            "per_zone": cfg.get("per_zone", False),
            "zones_rgb": list(cfg.get("zones_rgb", DEFAULT_CONFIG["zones_rgb"])),
            "power_profile": prev_profile,
        }
        cfg["g_mode"] = True
        cfg["mode"] = "static"
        cfg["per_zone"] = False
        cfg["zones_rgb"] = ["FF0000"] * 4
        cfg["force_seq"] = int(cfg.get("force_seq", 0)) + 1
        persist(cfg)

        prof_ok = set_prof("performance")
        active_prof = "performance" if prof_ok else prev_profile
        title = tr("🚀 Modo G Ativado (Game Shift)", "🚀 G-Mode Enabled (Game Shift)")
        if prof_ok:
            body = tr(
                "Perfil em Alto Desempenho • Teclado em Vermelho Puro",
                "High Performance profile active • Keyboard set to Pure Red",
            )
        else:
            body = tr(
                "Teclado em Vermelho Puro • Perfil Alto Desempenho indisponível neste sistema",
                "Keyboard set to Pure Red • High Performance profile unavailable on this system",
            )
        return True, active_prof, title, body

    pre = cfg.get("pre_gmode")
    prev_profile = "balanced"
    if isinstance(pre, dict):
        cfg["mode"] = str(pre.get("mode", "static"))
        cfg["per_zone"] = bool(pre.get("per_zone", False))
        if isinstance(pre.get("zones_rgb"), list) and len(pre["zones_rgb"]) == 4:
            cfg["zones_rgb"] = list(pre["zones_rgb"])
        saved_prof = pre.get("power_profile")
        if isinstance(saved_prof, str) and saved_prof in (
            "power-saver",
            "balanced",
            "performance",
        ):
            prev_profile = saved_prof
    else:
        cfg["zones_rgb"] = ["E6E6E6"] * 4

    cfg["g_mode"] = False
    cfg["pre_gmode"] = None
    cfg["force_seq"] = int(cfg.get("force_seq", 0)) + 1
    persist(cfg)

    prof_ok = set_prof(prev_profile)
    active_prof = prev_profile if prof_ok else get_prof()
    title = tr("⚖️ Modo G Desativado", "⚖️ G-Mode Disabled")
    if prof_ok:
        body = tr(
            f"Perfil {prev_profile} restaurado • Cores originais ativas",
            f"Profile {prev_profile} restored • Original keyboard colors active",
        )
    else:
        body = tr(
            "Cores originais restauradas • Falha ao restaurar perfil de energia",
            "Original keyboard colors restored • Failed to restore power profile",
        )
    return True, active_prof, title, body


def run_power_action(cfg, kind, target=None):
    """Blocking worker operation; callers dispatch it away from their GUI thread."""
    if kind == "gmode":
        return apply_g_mode_transition(cfg, target)
    ok = set_power_profile(target)
    if ok and target != "performance" and cfg.get("g_mode"):
        cfg["g_mode"] = False
        save_config(cfg)
    return True, get_power_profile(), tr("Perfil de energia", "Power profile"), (
        tr("Perfil aplicado: ", "Profile applied: ") + str(target) if ok
        else tr("Não foi possível aplicar o perfil solicitado", "Could not apply requested profile"))


def apply_backlight_cycle(cfg, save_fn=None):
    """
    Cycles backlight state: Sync -> 100% -> 50% -> 0% -> Sync.
    Returns (notif_title, notif_body).
    """
    persist = save_fn or save_config
    sync_on = bool(cfg.get("sync_screen", True))
    manual_val = int(cfg.get("manual_brightness", 100))

    if sync_on:
        cfg["sync_screen"] = False
        cfg["manual_brightness"] = 100
        title = tr("🔆 Teclado: Brilho Fixo 100%", "🔆 Keyboard: Fixed Brightness 100%")
        body = tr("Iluminação máxima constante ativada", "Constant maximum illumination active")
    elif manual_val > 50:
        cfg["sync_screen"] = False
        cfg["manual_brightness"] = 50
        title = tr("🔅 Teclado: Brilho Fixo 50%", "🔅 Keyboard: Fixed Brightness 50%")
        body = tr("Iluminação intermediária (50%) ativada", "Medium illumination (50%) active")
    elif manual_val > 0:
        cfg["sync_screen"] = False
        cfg["manual_brightness"] = 0
        title = tr("🌑 Teclado: LEDs Desligados (0%)", "🌑 Keyboard: LEDs Off (0%)")
        body = tr("Iluminação do teclado desativada", "Keyboard backlight turned off")
    else:
        cfg["sync_screen"] = True
        cfg["manual_brightness"] = 100
        title = tr(
            "🔄 Teclado: Brilho Automático (Ambient Sync)",
            "🔄 Keyboard: Auto Brightness (Ambient Sync)",
        )
        body = tr(
            "Sincronizado automaticamente com o brilho da tela",
            "Automatically synchronized with screen brightness",
        )

    cfg["force_seq"] = int(cfg.get("force_seq", 0)) + 1
    persist(cfg)
    return title, body


def apply_brightness_step(cfg, direction, save_fn=None):
    """
    Steps manual brightness along BRIGHTNESS_STEPS (+1 or -1).
    Returns (new_val, notif_title, notif_body).
    """
    persist = save_fn or save_config
    curr = int(cfg.get("manual_brightness", 100))
    nearest_idx = min(
        range(len(BRIGHTNESS_STEPS)),
        key=lambda i: abs(BRIGHTNESS_STEPS[i] - curr),
    )
    new_idx = max(0, min(len(BRIGHTNESS_STEPS) - 1, nearest_idx + direction))
    new_val = BRIGHTNESS_STEPS[new_idx]
    cfg["sync_screen"] = False
    cfg["manual_brightness"] = new_val
    cfg["force_seq"] = int(cfg.get("force_seq", 0)) + 1
    persist(cfg)
    title = tr(f"🔆 Brilho do Teclado: {new_val}%", f"🔆 Keyboard Brightness: {new_val}%")
    body = tr("Ajustado via barra superior", "Adjusted via top bar")
    return new_val, title, body


def request_boot_save(cfg, save_fn=None):
    """
    Prepares and saves a boot memory write request in `cfg`.
    Returns the expected `force_seq` integer to match against `save_boot_status`.
    """
    persist = save_fn or save_config
    next_seq = max(time.time_ns(), int(cfg.get("save_boot_seq", 0)) + 1)
    cfg["save_boot"] = True
    cfg["save_boot_status"] = None
    cfg["save_boot_seq"] = next_seq
    cfg["force_seq"] = int(cfg.get("force_seq", 0)) + 1
    persist(cfg)
    return next_seq


def evaluate_boot_save_feedback(cfg, pending_seq):
    """
    Checks `cfg["save_boot_status"]` against `pending_seq`.
    Distinguishes:
      - 'pending': no status yet or stale status from an older request (seq != pending_seq)
      - 'running': daemon acknowledged request and is currently writing packets to EEPROM
      - 'success': daemon finished writing all packets and verified HID response
      - 'failed': daemon encountered a HID/device error
    Returns (state_str, notif_title, notif_body, toast_msg).
    """
    if not pending_seq:
        return "pending", "", "", ""
    status = cfg.get("save_boot_status")
    if not isinstance(status, dict):
        return "pending", "", "", ""
    if int(status.get("seq", 0)) != pending_seq:
        return "pending", "", "", ""

    st = str(status.get("state", "done")).strip().lower()
    if st == "running":
        return (
            "running",
            "",
            "",
            tr(
                "Gravando perfil na memória do teclado (aguarde)...",
                "Writing profile to keyboard memory (please wait)...",
            ),
        )

    ok = bool(status.get("ok", False))
    if ok:
        return (
            "success",
            tr("💾 Memória do Teclado (Boot)", "💾 Keyboard Memory (Boot)"),
            tr(
                "Perfil gravado no chip do teclado (slot 0x0061)!",
                "Profile saved to keyboard controller (slot 0x0061)!",
            ),
            tr(
                "Perfil gravado na memória interna do teclado (slot 0x0061)!",
                "Profile saved to onboard keyboard memory (slot 0x0061)!",
            ),
        )
    return (
        "failed",
        tr("❌ Falha ao Gravar no Teclado", "❌ Failed to Save to Keyboard"),
        tr(
            "Não foi possível gravar no controlador HID (verifique o serviço/dispositivo).",
            "Could not write to the HID controller (check daemon/device).",
        ),
        tr(
            "Falha ao gravar na memória do teclado (dispositivo indisponível).",
            "Failed to write to keyboard memory (device unavailable).",
        ),
    )


def discover_evdev_hotkey_nodes():
    """Returns a list of `/dev/input/event*` paths matching Dell/Alienware keyboards."""
    target_names = ("at translated set 2 keyboard", "dell wmi hotkeys", "alienware")
    nodes = []
    for sys_name_path in sorted(glob.glob("/sys/class/input/event*/device/name")):
        try:
            with open(sys_name_path, "r", encoding="utf-8") as f:
                dev_name = f.read().strip().lower()
        except OSError:
            continue
        if any(t in dev_name for t in target_names):
            event_basename = sys_name_path.split("/")[4]
            nodes.append(f"/dev/input/{event_basename}")
    return nodes
