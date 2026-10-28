#!/usr/bin/env python3
"""
Dell G15 GNOME Interface (`g15_gtk.py`).
Uses GTK 4.0 + Libadwaita 1 (`Adw.Application`, `Adw.PreferencesPage`, `Adw.StyleManager`).
Strictly isolated from Qt: never imports PyQt6 or PySide6.
All business logic, telemetry, config, and atomic updater come from `g15_core`.
"""

import copy
import os
import signal
import sys
import threading
import time
import warnings

import gi

warnings.filterwarnings("ignore", category=DeprecationWarning)
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

import g15_core as core  # noqa: E402

# Re-export core symbols for compatibility
ASSETS_DIR = core.ASSETS_DIR
BRIGHTNESS_STEPS = core.BRIGHTNESS_STEPS
COLOR_PRESETS = core.COLOR_PRESETS
CONFIG_DIR = core.CONFIG_DIR
CONFIG_PATH = core.CONFIG_PATH
DEFAULT_CONFIG = core.DEFAULT_CONFIG
EFFECT_MODES = core.EFFECT_MODES
POWER_PROFILES = core.POWER_PROFILES
UPDATE_FILES_MAP = core.UPDATE_FILES_MAP
get_power_profile = core.get_power_profile
load_config = core.load_config
normalize_config = core.normalize_config
read_local_version = core.read_local_version
read_telemetry = core.read_telemetry
save_config = core.save_config
set_power_profile = core.set_power_profile
stage_and_apply_update = core.stage_and_apply_update
tr = core.tr
write_local_version = core.write_local_version


def hex_to_rgba(hex_str):
    clean = str(hex_str).lstrip("#").strip()
    rgba = Gdk.RGBA()
    if not rgba.parse(f"#{clean}"):
        rgba.parse("#E6E6E6")
    return rgba


def rgba_to_hex(rgba):
    r = max(0, min(255, int(round(rgba.red * 255))))
    g = max(0, min(255, int(round(rgba.green * 255))))
    b = max(0, min(255, int(round(rgba.blue * 255))))
    return f"{r:02X}{g:02X}{b:02X}"


# --- StatusNotifierItem + Dbusmenu XML Specifications ---
SNI_NODE_INFO = Gio.DBusNodeInfo.new_for_xml(
    """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="i" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconAccessibleDesc" type="s" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="AttentionAccessibleDesc" type="s" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="XAyatanaLabel" type="s" access="read"/>
    <property name="XAyatanaLabelGuide" type="s" access="read"/>
    <property name="XAyatanaOrderingIndex" type="u" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <method name="Activate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/>
      <arg name="orientation" type="s" direction="in"/>
    </method>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewStatus">
      <arg name="status" type="s"/>
    </signal>
    <signal name="NewToolTip"/>
    <signal name="XAyatanaNewLabel">
      <arg name="label" type="s"/>
      <arg name="guide" type="s"/>
    </signal>
  </interface>
</node>
"""
)

DBUSMENU_NODE_INFO = Gio.DBusNodeInfo.new_for_xml(
    """
<node>
  <interface name="com.canonical.dbusmenu">
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
    <method name="GetLayout">
      <arg type="i" name="parentId" direction="in"/>
      <arg type="i" name="recursionDepth" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="u" name="revision" direction="out"/>
      <arg type="(ia{sv}av)" name="layout" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="a(ia{sv})" name="properties" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="name" direction="in"/>
      <arg type="v" name="value" direction="out"/>
    </method>
    <method name="Event">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="eventId" direction="in"/>
      <arg type="v" name="data" direction="in"/>
      <arg type="u" name="timestamp" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg type="a(isvu)" name="events" direction="in"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg type="i" name="id" direction="in"/>
      <arg type="b" name="needUpdate" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="ai" name="updatesNeeded" direction="out"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <signal name="ItemsPropertiesUpdated">
      <arg type="a(ia{sv})" name="updatedProps"/>
      <arg type="a(ias)" name="removedProps"/>
    </signal>
    <signal name="LayoutUpdated">
      <arg type="u" name="revision"/>
      <arg type="i" name="parent"/>
    </signal>
  </interface>
</node>
"""
)

SNI_PATH = "/org/ayatana/NotificationItem/dell_g15"
MENU_PATH = "/org/ayatana/NotificationItem/dell_g15/Menu"

SWATCH_CSS = """
.g15-preset-btn {
    padding: 5px 8px;
    border-radius: 8px;
}
.g15-dot {
    min-width: 14px;
    min-height: 14px;
    border-radius: 99px;
    border: 1px solid rgba(128, 128, 128, 0.45);
}
"""


class G15ControlApp(Adw.Application):
    def __init__(self, start_hidden=True):
        super().__init__(
            application_id="io.github.murilogiatti.DellG15Control",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.start_hidden = start_hidden
        self.cfg = load_config()
        self.telemetry = read_telemetry()
        self.active_power_profile = None
        self.menu_revision = 1
        self.menu_actions = {}
        self.menu_items_flat = {}
        self.menu_nodes = {}
        self.window = None
        self._updating_ui = False
        self._sni_reg_id = 0
        self._menu_reg_id = 0
        self._watcher_sub_id = 0
        self._bus = None
        self._last_notif_id = 0
        self._last_gmode_ts = 0.0
        self._last_backlight_ts = 0.0
        self._pending_scancode = 0
        self._evdev_fds = []
        self.local_commit, self.repo_dir = read_local_version()
        self.latest_commit = self.local_commit
        self.latest_commit_msg = ""
        self.update_available = False
        self._checking_update = False
        self._updating_app = False
        self._notified_commit = ""
        self._gnome_settings = None
        self._portal_sub_id = 0
        self._power_busy = False
        self._power_generation = 0
        self._poll_busy = False
        self._daemon_label = core.daemon_status_label()
        self._pending_boot_seq = 0
        self._boot_timeout_id = 0

    def _setup_theme_sync(self):
        """
        Follows GNOME/Ubuntu appearance preferences (light/dark color-scheme, high-contrast,
        system fonts, and icon theme) via Adw.StyleManager, XDG Desktop Portal, and GSettings.
        """
        style_mgr = Adw.StyleManager.get_default()
        style_mgr.set_color_scheme(Adw.ColorScheme.DEFAULT)

        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self._portal_sub_id = bus.signal_subscribe(
                "org.freedesktop.portal.Desktop",
                "org.freedesktop.portal.Settings",
                "SettingChanged",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.appearance",
                Gio.DBusSignalFlags.NONE,
                self._on_portal_setting_changed,
            )
        except Exception:
            pass

        try:
            schema_src = Gio.SettingsSchemaSource.get_default()
            if schema_src and schema_src.lookup("org.gnome.desktop.interface", True):
                self._gnome_settings = Gio.Settings.new("org.gnome.desktop.interface")
                self._gnome_settings.connect(
                    "changed::color-scheme", self._apply_system_color_scheme
                )
                self._gnome_settings.connect(
                    "changed::gtk-theme", self._apply_system_color_scheme
                )
        except Exception:
            pass

        self._apply_system_color_scheme()

    def _on_portal_setting_changed(self, _conn, _sender, _path, _iface, _sig, params):
        try:
            namespace, key, val = params.unpack()
            if namespace == "org.freedesktop.appearance" and key == "color-scheme":
                while isinstance(val, GLib.Variant):
                    val = val.unpack()
                style_mgr = Adw.StyleManager.get_default()
                if val == 1:
                    style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
                elif val == 2:
                    style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
                else:
                    self._apply_system_color_scheme()
        except Exception:
            pass

    def _apply_system_color_scheme(self, *_args):
        style_mgr = Adw.StyleManager.get_default()
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            res = bus.call_sync(
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.Settings",
                "Read",
                GLib.Variant("(ss)", ("org.freedesktop.appearance", "color-scheme")),
                GLib.VariantType("(v)"),
                Gio.DBusCallFlags.NONE,
                500,
                None,
            )
            val = res.unpack()[0]
            while isinstance(val, GLib.Variant):
                val = val.unpack()
            if val == 1:
                style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
                return
            if val == 2:
                style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
                return
        except Exception:
            pass

        if self._gnome_settings:
            try:
                cs = self._gnome_settings.get_string("color-scheme").lower()
                gtk_theme = self._gnome_settings.get_string("gtk-theme").lower()
                if cs == "prefer-dark" or (cs == "default" and "dark" in gtk_theme):
                    style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
                elif cs == "prefer-light" or cs == "default":
                    style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
                else:
                    style_mgr.set_color_scheme(Adw.ColorScheme.DEFAULT)
                return
            except Exception:
                pass

        style_mgr.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def do_startup(self):
        Adw.Application.do_startup(self)
        Gtk.Window.set_default_icon_name("io.github.murilogiatti.DellG15Control")
        self._setup_theme_sync()
        display = Gdk.Display.get_default()
        if display:
            icon_theme = Gtk.IconTheme.get_for_display(display)
            if os.path.isdir(ASSETS_DIR):
                icon_theme.add_search_path(ASSETS_DIR)
            css_prov = Gtk.CssProvider()
            rule_lines = [SWATCH_CSS]
            for code, hex_val, _pt, _en in COLOR_PRESETS:
                rule_lines.append(
                    f".dot-{code} {{ background: #{hex_val}; }}"
                )
            css_prov.load_from_string("\n".join(rule_lines))
            Gtk.StyleContext.add_provider_for_display(
                display, css_prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        self.hold()
        self._rebuild_menu_model()
        self._setup_dbus_tray()
        self._setup_config_monitor()
        self._setup_hotkey_monitors()
        GLib.timeout_add_seconds(3, self._on_telemetry_tick)
        GLib.timeout_add_seconds(12, self._initial_update_check)
        GLib.timeout_add_seconds(21600, self._periodic_update_check)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
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
        else:
            self.start_hidden = False
        return 0

    def do_activate(self):
        self.present_control_window()

    def send_osd_notification(self, title, body):
        if not self._bus:
            return
        icon_path = os.path.join(ASSETS_DIR, "logo.png")
        icon = icon_path if os.path.exists(icon_path) else "input-keyboard"
        try:
            res = self._bus.call_sync(
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications",
                "Notify",
                GLib.Variant(
                    "(susssasa{sv}i)",
                    (
                        "Dell G15 Control",
                        int(self._last_notif_id),
                        icon,
                        title,
                        body,
                        [],
                        {"transient": GLib.Variant("b", True)},
                        2500,
                    ),
                ),
                GLib.VariantType("(u)"),
                Gio.DBusCallFlags.NONE,
                1000,
                None,
            )
            self._last_notif_id = res.unpack()[0]
        except Exception:
            pass

    # --- Evdev Hotkey Monitors (Fn+F9 G-Mode & Fn+F5 Backlight) ---
    def _setup_hotkey_monitors(self):
        for dev_node in core.discover_evdev_hotkey_nodes():
            try:
                fd = os.open(dev_node, os.O_RDONLY | os.O_NONBLOCK)
                self._evdev_fds.append(fd)
                GLib.io_add_watch(
                    fd,
                    GLib.IO_IN | GLib.IO_ERR | GLib.IO_HUP,
                    self._on_evdev_readable,
                )
            except OSError:
                continue

    def _close_evdev(self, fd):
        if fd in self._evdev_fds:
            self._evdev_fds.remove(fd)
            os.close(fd)

    def do_shutdown(self):
        for fd in list(self._evdev_fds):
            self._close_evdev(fd)
        if hasattr(self, "_cfg_monitor"):
            self._cfg_monitor.cancel()
        Adw.Application.do_shutdown(self)

    def _on_evdev_readable(self, fd, condition):
        if condition & (GLib.IO_ERR | GLib.IO_HUP):
            self._close_evdev(fd)
            return False
        pkt_size = core.INPUT_EVENT_STRUCT.size
        while True:
            try:
                raw = os.read(fd, pkt_size * 16)
                if not raw:
                    self._close_evdev(fd)
                    return False
            except BlockingIOError:
                break
            except OSError:
                self._close_evdev(fd)
                return False

            for offset in range(0, len(raw) - pkt_size + 1, pkt_size):
                _sec, _usec, ev_type, ev_code, ev_value = core.INPUT_EVENT_STRUCT.unpack_from(
                    raw, offset
                )
                self._process_input_event(ev_type, ev_code, ev_value)
        return True

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

    # --- Shared Business Actions Delegated to g15_core ---
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
            GLib.idle_add(self._on_power_done, result, error, notify)
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
        self._notify_menu_updated()
        self._sync_window_from_config()
        self._update_window_telemetry()
        return False

    def toggle_g_mode(self, target_state=None, notify=True):
        self._queue_power_action("gmode", target_state, notify)

    def cycle_backlight_mode(self, notify=True):
        title, body = core.apply_backlight_cycle(
            self.cfg, save_fn=lambda c: save_config(c)
        )
        if notify:
            self.send_osd_notification(title, body)
        self._notify_menu_updated()
        self._sync_window_from_config()

    def _step_brightness(self, direction):
        _new_val, title, body = core.apply_brightness_step(
            self.cfg, direction, save_fn=lambda c: save_config(c)
        )
        self.send_osd_notification(title, body)
        self._notify_menu_updated()
        self._sync_window_from_config()

    # --- File Monitor for External Config Changes ---
    def _setup_config_monitor(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if not os.path.exists(CONFIG_PATH):
            save_config(self.cfg)
        gfile = Gio.File.new_for_path(CONFIG_DIR)
        self._cfg_monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
        self._cfg_monitor.connect("changed", self._on_config_file_changed)

    def _on_config_file_changed(self, _monitor, _file, _other, event_type):
        if event_type in (
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CREATED,
            Gio.FileMonitorEvent.CHANGED,
            Gio.FileMonitorEvent.MOVED_IN,
            Gio.FileMonitorEvent.RENAMED,
        ):
            new_cfg = load_config()
            if new_cfg != self.cfg:
                self.cfg = new_cfg
                self._check_save_boot_feedback()
                self._notify_menu_updated()
                self._sync_window_from_config()

    def _check_save_boot_feedback(self):
        state, title, body, toast_msg = core.evaluate_boot_save_feedback(
            self.cfg, self._pending_boot_seq
        )
        if state == "pending":
            return
        if state == "running":
            return
        self._pending_boot_seq = 0
        if self._boot_timeout_id:
            GLib.source_remove(self._boot_timeout_id)
            self._boot_timeout_id = 0
        self.send_osd_notification(title, body)
        if self.window and hasattr(self, "_toast_overlay"):
            self._toast_overlay.add_toast(Adw.Toast.new(toast_msg))

    def _on_save_boot_timeout(self, expected_seq):
        if self._pending_boot_seq != expected_seq:
            return False
        self._boot_timeout_id = 0
        self._pending_boot_seq = 0
        self.send_osd_notification(
            tr("⚠️ Sem Resposta do Daemon", "⚠️ No Response from Daemon"),
            tr(
                "O serviço dell-g15-daemon não confirmou a gravação no teclado.",
                "The dell-g15-daemon service did not confirm the keyboard write.",
            ),
        )
        if self.window and hasattr(self, "_toast_overlay"):
            toast = Adw.Toast.new(
                tr(
                    "Tempo esgotado aguardando confirmação do daemon.",
                    "Timed out waiting for daemon confirmation.",
                )
            )
            self._toast_overlay.add_toast(toast)
        return False

    def _on_telemetry_tick(self):
        if self._poll_busy or self._power_busy:
            return True
        self._poll_busy = True
        generation = self._power_generation
        def worker():
            data = core.read_telemetry()
            profile = core.get_power_profile()
            label = core.daemon_status_label()
            GLib.idle_add(self._on_poll_done, data, profile, label, generation)
        threading.Thread(target=worker, daemon=True).start()
        return True

    def _on_poll_done(self, data, profile, label, generation):
        self._poll_busy = False
        if generation != self._power_generation or self._power_busy:
            return False
        self.telemetry = data
        self.active_power_profile = profile
        self._daemon_label = label
        self._update_window_telemetry()
        self._notify_menu_updated()
        return False

    def _emit_item_prop_updated(self, item_id, changed_props):
        if not self._bus:
            return
        try:
            self._bus.emit_signal(
                None,
                MENU_PATH,
                "com.canonical.dbusmenu",
                "ItemsPropertiesUpdated",
                GLib.Variant("(a(ia{sv})a(ias))", ([(item_id, changed_props)], [])),
            )
        except Exception:
            pass

    # --- StatusNotifierItem & Dbusmenu Implementation ---
    def _setup_dbus_tray(self):
        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._sni_reg_id = self._bus.register_object(
            SNI_PATH,
            SNI_NODE_INFO.interfaces[0],
            self._on_sni_method_call,
            self._on_sni_get_property,
            None,
        )
        self._menu_reg_id = self._bus.register_object(
            MENU_PATH,
            DBUSMENU_NODE_INFO.interfaces[0],
            self._on_menu_method_call,
            self._on_menu_get_property,
            None,
        )
        self._watcher_sub_id = self._bus.signal_subscribe(
            "org.kde.StatusNotifierWatcher",
            "org.kde.StatusNotifierWatcher",
            None,
            "/StatusNotifierWatcher",
            None,
            Gio.DBusSignalFlags.NONE,
            lambda *_a: self._register_with_watcher(),
        )
        Gio.bus_watch_name_on_connection(
            self._bus,
            "org.kde.StatusNotifierWatcher",
            Gio.BusNameWatcherFlags.NONE,
            lambda *_a: self._register_with_watcher(),
            None,
        )
        self._register_with_watcher()

    def _register_with_watcher(self):
        if not self._bus:
            return
        try:
            self._bus.call_sync(
                "org.kde.StatusNotifierWatcher",
                "/StatusNotifierWatcher",
                "org.kde.StatusNotifierWatcher",
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (SNI_PATH,)),
                None,
                Gio.DBusCallFlags.NONE,
                1000,
                None,
            )
        except Exception:
            pass

    def _current_icon_name(self):
        custom_svg = os.path.join(ASSETS_DIR, "tray-icon.svg")
        if os.path.exists(custom_svg):
            return "tray-icon"
        return "input-keyboard-symbolic"

    def _on_sni_get_property(self, _conn, _sender, _path, _iface, prop):
        if prop == "Category":
            return GLib.Variant("s", "Hardware")
        if prop == "Id":
            return GLib.Variant("s", "dell-g15-power-sync")
        if prop == "Title":
            return GLib.Variant("s", "Dell G15 Control")
        if prop == "Status":
            return GLib.Variant("s", "Active")
        if prop == "WindowId":
            return GLib.Variant("i", 0)
        if prop == "IconName":
            return GLib.Variant("s", self._current_icon_name())
        if prop == "IconAccessibleDesc":
            return GLib.Variant("s", "Dell G15 Control")
        if prop == "IconThemePath":
            return GLib.Variant("s", ASSETS_DIR if os.path.isdir(ASSETS_DIR) else "")
        if prop in ("AttentionIconName", "AttentionAccessibleDesc", "XAyatanaLabel", "XAyatanaLabelGuide"):
            return GLib.Variant("s", "")
        if prop == "XAyatanaOrderingIndex":
            return GLib.Variant("u", 0)
        if prop == "Menu":
            return GLib.Variant("o", MENU_PATH)
        if prop == "ItemIsMenu":
            return GLib.Variant("b", True)
        if prop == "ToolTip":
            sub = core.format_telemetry_label(self.telemetry)
            return GLib.Variant(
                "(sa(iiay)ss)",
                (self._current_icon_name(), [], "Dell G15 Control", sub),
            )
        return None

    def _on_sni_method_call(self, _conn, _sender, _path, _iface, method, params, invocation):
        if method == "Activate":
            self.present_control_window()
            invocation.return_value(None)
        elif method == "SecondaryActivate":
            self.cycle_backlight_mode(notify=True)
            invocation.return_value(None)
        elif method == "ContextMenu":
            invocation.return_value(None)
        elif method == "Scroll":
            delta, _orientation = params.unpack()
            self._step_brightness(1 if delta > 0 else -1)
            invocation.return_value(None)
        else:
            invocation.return_value(None)

    # --- Dynamic Dbusmenu Model & Subtree Serializer ---
    def _rebuild_menu_model(self):
        self.menu_actions.clear()
        self.menu_items_flat.clear()
        self.menu_nodes.clear()
        root_children_ids = []

        def register_node(item_id, props, action=None, child_ids=None):
            p = {"enabled": GLib.Variant("b", True), "visible": GLib.Variant("b", True)}
            p.update(props)
            if action is not None:
                self.menu_actions[item_id] = action
            c_ids = list(child_ids or [])
            if c_ids:
                p["children-display"] = GLib.Variant("s", "submenu")
            self.menu_items_flat[item_id] = p
            self.menu_nodes[item_id] = (item_id, p, c_ids)
            return item_id

        def register_sep(item_id):
            return register_node(item_id, {"type": GLib.Variant("s", "separator")})

        # 1. Telemetry Header
        root_children_ids.append(
            register_node(
                1,
                {
                    "label": GLib.Variant("s", core.format_telemetry_label(self.telemetry)),
                    "enabled": GLib.Variant("b", False),
                },
            )
        )

        # 2. Open Control Panel Window
        root_children_ids.append(
            register_node(
                2,
                {
                    "label": GLib.Variant(
                        "s",
                        tr("🎛️ Abrir Painel de Controle...", "🎛️ Open Control Panel..."),
                    )
                },
                action=self.present_control_window,
            )
        )

        # 2b. Prominent Update Banner in Tray if an update is available
        if self.update_available:
            short_sha = self.latest_commit[:7] if self.latest_commit else "new"
            root_children_ids.append(
                register_node(
                    5,
                    {
                        "label": GLib.Variant(
                            "s",
                            tr(
                                f"🔄 Atualização Disponível ({short_sha}) — Instalar Agora",
                                f"🔄 Update Available ({short_sha}) — Install Now",
                            ),
                        )
                    },
                    action=self.perform_self_update_async,
                )
            )

        # 3. Quick G-Mode (Fn+F9) Toggle in Tray
        gmode_active = bool(self.cfg.get("g_mode", False))
        root_children_ids.append(
            register_node(
                4,
                {
                    "label": GLib.Variant(
                        "s",
                        tr("🚀 Modo G / Game Shift (Fn+F9)", "🚀 G-Mode / Game Shift (Fn+F9)"),
                    ),
                    "toggle-type": GLib.Variant("s", "checkmark"),
                    "toggle-state": GLib.Variant("i", 1 if gmode_active else 0),
                },
                action=lambda: self.toggle_g_mode(notify=True),
            )
        )
        root_children_ids.append(register_sep(3))

        # 4. Ambient Sync + Manual Brightness Radio Group
        sync_on = bool(self.cfg.get("sync_screen", True))
        manual_val = int(self.cfg.get("manual_brightness", 100))

        root_children_ids.append(
            register_node(
                10,
                {
                    "label": GLib.Variant(
                        "s",
                        tr(
                            "🔄 Brilho Automático (Ambient Sync)",
                            "🔄 Automatic Brightness (Ambient Sync)",
                        ),
                    ),
                    "toggle-type": GLib.Variant("s", "radio"),
                    "toggle-state": GLib.Variant("i", 1 if sync_on else 0),
                },
                action=lambda: self._set_sync_or_manual(True, manual_val),
            )
        )

        for idx, step in enumerate((100, 75, 50, 30, 10, 0)):
            item_id = 11 + idx
            if step == 0:
                lbl = tr("🌑 Desligar LEDs (0%)", "🌑 Turn Off LEDs (0%)")
            else:
                lbl = tr(f"🔆 Brilho Fixo: {step}%", f"🔆 Fixed Brightness: {step}%")
            checked = (not sync_on) and (manual_val == step)
            root_children_ids.append(
                register_node(
                    item_id,
                    {
                        "label": GLib.Variant("s", lbl),
                        "toggle-type": GLib.Variant("s", "radio"),
                        "toggle-state": GLib.Variant("i", 1 if checked else 0),
                    },
                    action=lambda s=step: self._set_sync_or_manual(False, s),
                )
            )

        root_children_ids.append(register_sep(20))

        # 5. Quick Color Presets Submenu
        cur_hex = str(self.cfg.get("zones_rgb", ["E6E6E6"])[0]).upper()
        cur_per_zone = bool(self.cfg.get("per_zone", False))
        color_child_ids = []
        for idx, (_code, hex_val, lbl_pt, lbl_en) in enumerate(COLOR_PRESETS):
            cid = 100 + idx
            is_sel = (not cur_per_zone) and (cur_hex == hex_val)
            color_child_ids.append(
                register_node(
                    cid,
                    {
                        "label": GLib.Variant("s", f"{tr(lbl_pt, lbl_en)} (#{hex_val})"),
                        "toggle-type": GLib.Variant("s", "radio"),
                        "toggle-state": GLib.Variant("i", 1 if is_sel else 0),
                    },
                    action=lambda h=hex_val: self._apply_quick_color(h),
                )
            )
        root_children_ids.append(
            register_node(
                30,
                {"label": GLib.Variant("s", tr("🎨 Cores Rápidas", "🎨 Quick Colors"))},
                child_ids=color_child_ids,
            )
        )

        # 6. Hardware Effects Submenu
        cur_mode = str(self.cfg.get("mode", "static")).lower()
        effect_child_ids = []
        for idx, (m_key, lbl_pt, lbl_en) in enumerate(EFFECT_MODES):
            eid = 41 + idx
            effect_child_ids.append(
                register_node(
                    eid,
                    {
                        "label": GLib.Variant("s", tr(lbl_pt, lbl_en)),
                        "toggle-type": GLib.Variant("s", "radio"),
                        "toggle-state": GLib.Variant("i", 1 if cur_mode == m_key else 0),
                    },
                    action=lambda m=m_key: self._apply_quick_mode(m),
                )
            )
        root_children_ids.append(
            register_node(
                40,
                {"label": GLib.Variant("s", tr("✨ Efeitos do Teclado", "✨ Keyboard Effects"))},
                child_ids=effect_child_ids,
            )
        )

        # 7. Power Profiles Submenu
        power_child_ids = []
        for idx, (prof_id, lbl_pt, lbl_en) in enumerate(POWER_PROFILES):
            pid = 51 + idx
            power_child_ids.append(
                register_node(
                    pid,
                    {
                        "label": GLib.Variant("s", tr(lbl_pt, lbl_en)),
                        "enabled": GLib.Variant("b", self.active_power_profile is not None),
                        "toggle-type": GLib.Variant("s", "radio"),
                        "toggle-state": GLib.Variant(
                            "i", 1 if self.active_power_profile == prof_id else 0
                        ),
                    },
                    action=lambda p=prof_id: self._apply_power_profile(p),
                )
            )
        root_children_ids.append(
            register_node(
                50,
                {"label": GLib.Variant("s", tr("⚡ Perfil de Energia", "⚡ Power Profile"))},
                child_ids=power_child_ids,
            )
        )

        root_children_ids.append(register_sep(60))

        # 8. Save to Keyboard Boot Memory (EEPROM 0x0061)
        root_children_ids.append(
            register_node(
                61,
                {
                    "label": GLib.Variant(
                        "s",
                        tr(
                            "💾 Salvar na Memória do Teclado (Boot)",
                            "💾 Save to Keyboard Memory (Boot)",
                        ),
                    )
                },
                action=self._trigger_save_boot,
            )
        )

        # 9. Check / Install Updates directly from Tray
        if self.update_available:
            upd_lbl = tr(
                f"🔄 Instalar Atualização ({self.latest_commit[:7]})",
                f"🔄 Install Update ({self.latest_commit[:7]})",
            )
            upd_act = self.perform_self_update_async
        else:
            upd_lbl = tr(
                "🔍 Verificar Atualizações...",
                "🔍 Check for Updates...",
            )
            upd_act = lambda: self.check_for_updates_async(manual=True)

        root_children_ids.append(
            register_node(
                62,
                {"label": GLib.Variant("s", upd_lbl)},
                action=upd_act,
            )
        )

        root_props = {"children-display": GLib.Variant("s", "submenu")}
        self.menu_items_flat[0] = root_props
        self.menu_nodes[0] = (0, root_props, root_children_ids)

    def _serialize_layout_node(self, node_id, depth):
        if not self.menu_nodes:
            self._rebuild_menu_model()
        nid, props, child_ids = self.menu_nodes.get(node_id, self.menu_nodes[0])
        if depth == 0 or not child_ids:
            return (nid, props, [])
        next_depth = depth - 1 if depth > 0 else -1
        children_variants = [
            GLib.Variant("(ia{sv}av)", self._serialize_layout_node(cid, next_depth))
            for cid in child_ids
            if cid in self.menu_nodes
        ]
        return (nid, props, children_variants)

    def _set_sync_or_manual(self, sync_screen, manual_brightness):
        self.cfg["sync_screen"] = bool(sync_screen)
        self.cfg["manual_brightness"] = int(manual_brightness)
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        save_config(self.cfg)
        self._notify_menu_updated()
        self._sync_window_from_config()

    def _apply_quick_color(self, hex_val):
        self.cfg["per_zone"] = False
        self.cfg["zones_rgb"] = [hex_val] * 4
        if self.cfg.get("mode") in ("spectrum", "rainbow"):
            self.cfg["mode"] = "static"
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        save_config(self.cfg)
        self._notify_menu_updated()
        self._sync_window_from_config()

    def _apply_quick_mode(self, mode_key):
        self.cfg["mode"] = mode_key
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        save_config(self.cfg)
        self._notify_menu_updated()
        self._sync_window_from_config()

    def _apply_power_profile(self, prof_id):
        self._queue_power_action("profile", prof_id, True)

    def _trigger_save_boot(self):
        if self._boot_timeout_id:
            GLib.source_remove(self._boot_timeout_id)
            self._boot_timeout_id = 0
        next_seq = core.request_boot_save(self.cfg, save_fn=lambda c: save_config(c))
        self._pending_boot_seq = next_seq
        self._boot_timeout_id = GLib.timeout_add_seconds(
            core.BOOT_SAVE_TIMEOUT_SEC, self._on_save_boot_timeout, next_seq
        )

    # --- Built-in Update Checker & 1-Click Self-Updater ---
    def _initial_update_check(self):
        self.check_for_updates_async(manual=False)
        return False

    def _periodic_update_check(self):
        self.check_for_updates_async(manual=False)
        return True

    def _format_update_subtitle(self):
        notice = core.local_build_update_notice(self.local_commit)
        if notice:
            return notice
        short_local = (
            self.local_commit[:7]
            if self.local_commit and self.local_commit != "unknown"
            else "local"
        )
        if self._updating_app:
            return tr(
                "Baixando e aplicando atualização oficial do GitHub...",
                "Downloading and applying official update from GitHub...",
            )
        if self._checking_update:
            return tr(
                "Consultando repositório oficial no GitHub...",
                "Checking official GitHub repository...",
            )
        if self.update_available:
            short_new = self.latest_commit[:7] if self.latest_commit else "new"
            msg = self.latest_commit_msg or ""
            return tr(
                f"Nova versão disponível ({short_new}): {msg}",
                f"New version available ({short_new}): {msg}",
            )
        return tr(
            f"Versão instalada: #{short_local} — Verifica automaticamente novas versões no GitHub",
            f"Installed version: #{short_local} — Automatically checks for new versions on GitHub",
        )

    def _format_update_button_label(self):
        if self._updating_app:
            return tr("⏳ Atualizando...", "⏳ Updating...")
        if self._checking_update:
            return tr("⏳ Verificando...", "⏳ Checking...")
        if self.update_available:
            return tr("🔄 Instalar Atualização", "🔄 Install Update")
        return tr("🔍 Verificar Agora", "🔍 Check Now")

    def _refresh_update_ui(self):
        if self.window is None or not hasattr(self, "_row_update"):
            return
        self._row_update.set_subtitle(self._format_update_subtitle())
        self._btn_update.set_label(self._format_update_button_label())
        self._btn_update.set_sensitive(not (self._checking_update or self._updating_app))
        if self.update_available:
            self._btn_update.add_css_class("suggested-action")
        else:
            self._btn_update.remove_css_class("suggested-action")

    def _on_ui_update_clicked(self, _btn):
        if self.update_available:
            self.perform_self_update_async()
        else:
            self.check_for_updates_async(manual=True)

    def check_for_updates_async(self, manual=False):
        notice = core.local_build_update_notice(self.local_commit)
        if notice:
            if manual:
                self.send_osd_notification(core.tr("Versão local", "Local build"), notice)
            return

        if self._checking_update or self._updating_app:
            return
        self._checking_update = True
        self._refresh_update_ui()

        def worker():
            remote_sha = ""
            commit_msg = ""
            err_msg = ""
            try:
                remote_sha, commit_msg = core.fetch_latest_github_commit()
            except Exception as exc:
                err_msg = str(exc)

            GLib.idle_add(
                self._on_update_check_done, remote_sha, commit_msg, manual, err_msg
            )

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_check_done(self, remote_sha, commit_msg, manual, err_msg):
        self._checking_update = False
        self.local_commit, self.repo_dir = read_local_version()

        if not remote_sha:
            self._refresh_update_ui()
            if manual:
                self.send_osd_notification(
                    tr("⚠️ Erro ao Verificar Atualizações", "⚠️ Update Check Failed"),
                    tr(
                        f"Não foi possível conectar ao GitHub: {err_msg}",
                        f"Could not reach GitHub: {err_msg}",
                    ),
                )
            return False

        is_same_or_ahead = core.is_commit_same_or_ahead(
            self.local_commit, remote_sha, self.repo_dir
        )

        if not is_same_or_ahead:
            self.update_available = True
            self.latest_commit = remote_sha
            self.latest_commit_msg = commit_msg
            self._notify_menu_updated()
            self._refresh_update_ui()
            if manual or self._notified_commit != remote_sha:
                self._notified_commit = remote_sha
                self.send_osd_notification(
                    tr("🔄 Atualização Disponível!", "🔄 Update Available!"),
                    tr(
                        f"Nova versão ({remote_sha[:7]}): {commit_msg}. Abra o menu ou painel para instalar em 1 clique.",
                        f"New version ({remote_sha[:7]}): {commit_msg}. Open tray or panel to install in 1 click.",
                    ),
                )
        else:
            self.update_available = False
            self.latest_commit = self.local_commit
            self._notify_menu_updated()
            self._refresh_update_ui()
            if manual:
                short_sha = self.local_commit[:7]
                self.send_osd_notification(
                    tr("✅ Aplicativo Atualizado", "✅ Application Up to Date"),
                    tr(
                        f"Você já está na versão mais recente (#{short_sha}).",
                        f"You are already running the latest version (#{short_sha}).",
                    ),
                )
                if self.window and hasattr(self, "_toast_overlay"):
                    toast = Adw.Toast.new(
                        tr(
                            f"Você já está na versão mais recente (#{short_sha})!",
                            f"You are already on the latest version (#{short_sha})!",
                        )
                    )
                    self._toast_overlay.add_toast(toast)
        return False

    def perform_self_update_async(self):
        notice = core.local_build_update_notice(self.local_commit)
        if notice:
            self.send_osd_notification(core.tr("Versão local", "Local build"), notice)
            return

        if self._updating_app:
            return
        self._updating_app = True
        self._refresh_update_ui()
        self.send_osd_notification(
            tr("⏳ Atualizando Dell G15 Control...", "⏳ Updating Dell G15 Control..."),
            tr(
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
                target_sha = stage_and_apply_update(
                    target_sha,
                    files_map=UPDATE_FILES_MAP,
                    repo_dir=self.repo_dir,
                )
            except Exception as exc:
                err_msg = str(exc)

            GLib.idle_add(self._on_self_update_done, target_sha, err_msg)

        threading.Thread(target=worker, daemon=True).start()

    def _on_self_update_done(self, target_sha, err_msg):
        self._updating_app = False
        if err_msg:
            self._refresh_update_ui()
            self.send_osd_notification(
                tr("❌ Falha na Atualização", "❌ Update Failed"),
                tr(
                    f"Erro ao atualizar: {err_msg}",
                    f"Error updating: {err_msg}",
                ),
            )
            return False

        self.local_commit = target_sha or self.local_commit
        self.update_available = False
        self._notify_menu_updated()
        self._refresh_update_ui()
        short_sha = self.local_commit[:7] if self.local_commit else "new"
        self.send_osd_notification(
            tr("✅ Atualização Concluída!", "✅ Update Complete!"),
            tr(
                f"Versão #{short_sha} instalada! Reiniciando serviços automaticamente...",
                f"Version #{short_sha} installed! Automatically restarting services...",
            ),
        )
        ok, detail = core.restart_systemd_services()
        if not ok:
            self.send_osd_notification(
                tr("Falha ao reiniciar serviços", "Service restart failed"), detail
            )
        return False

    def _notify_menu_updated(self):
        self._rebuild_menu_model()
        self.menu_revision += 1
        if not self._bus:
            return
        try:
            self._bus.emit_signal(
                None,
                MENU_PATH,
                "com.canonical.dbusmenu",
                "LayoutUpdated",
                GLib.Variant("(ui)", (self.menu_revision, 0)),
            )
            self._bus.emit_signal(
                None,
                SNI_PATH,
                "org.kde.StatusNotifierItem",
                "NewIcon",
                None,
            )
        except Exception:
            pass

    def _on_menu_get_property(self, _conn, _sender, _path, _iface, prop):
        if prop == "Version":
            return GLib.Variant("u", 3)
        if prop == "TextDirection":
            return GLib.Variant("s", "ltr")
        if prop == "Status":
            return GLib.Variant("s", "normal")
        if prop == "IconThemePath":
            return GLib.Variant("as", [ASSETS_DIR] if os.path.isdir(ASSETS_DIR) else [])
        return None

    def _on_menu_method_call(self, _conn, _sender, _path, _iface, method, params, invocation):
        if method == "GetLayout":
            parent_id, recursion_depth, _prop_names = params.unpack()
            if not self.menu_nodes:
                self._rebuild_menu_model()
            tree = self._serialize_layout_node(parent_id, recursion_depth)
            invocation.return_value(GLib.Variant("(u(ia{sv}av))", (self.menu_revision, tree)))
        elif method == "GetGroupProperties":
            ids, _prop_names = params.unpack()
            if not self.menu_items_flat:
                self._rebuild_menu_model()
            res = [(i, self.menu_items_flat[i]) for i in ids if i in self.menu_items_flat]
            invocation.return_value(GLib.Variant("(a(ia{sv}))", (res,)))
        elif method == "GetProperty":
            item_id, prop_name = params.unpack()
            if not self.menu_items_flat:
                self._rebuild_menu_model()
            val = self.menu_items_flat.get(item_id, {}).get(
                prop_name, GLib.Variant("s", "")
            )
            invocation.return_value(GLib.Variant("(v)", (val,)))
        elif method == "Event":
            item_id, event_id, _data, _ts = params.unpack()
            if event_id == "clicked" and item_id in self.menu_actions:
                GLib.idle_add(self._invoke_menu_action, item_id)
            invocation.return_value(None)
        elif method == "EventGroup":
            events = params.unpack()[0]
            for item_id, event_id, _data, _ts in events:
                if event_id == "clicked" and item_id in self.menu_actions:
                    GLib.idle_add(self._invoke_menu_action, item_id)
            invocation.return_value(GLib.Variant("(ai)", ([],)))
        elif method == "AboutToShow":
            invocation.return_value(GLib.Variant("(b)", (False,)))
        elif method == "AboutToShowGroup":
            invocation.return_value(GLib.Variant("(aiai)", ([], [])))
        else:
            invocation.return_value(None)

    def _invoke_menu_action(self, item_id):
        fn = self.menu_actions.get(item_id)
        if fn:
            fn()
        return False

    # --- GTK4 + Libadwaita Control Center ---
    def _make_full_text_combo_factory(self):
        factory = Gtk.SignalListItemFactory()

        def on_setup(_f, list_item):
            lbl = Gtk.Label(xalign=1.0)
            lbl.set_ellipsize(Pango.EllipsizeMode.NONE)
            lbl.set_valign(Gtk.Align.CENTER)
            list_item.set_child(lbl)

        def on_bind(_f, list_item):
            item = list_item.get_item()
            lbl = list_item.get_child()
            if item and lbl:
                lbl.set_label(item.get_string())

        factory.connect("setup", on_setup)
        factory.connect("bind", on_bind)
        return factory

    def _attach_scroll_step_5(self, scale, min_val, max_val):
        adj = scale.get_adjustment()
        adj.set_step_increment(5)
        adj.set_page_increment(5)
        ctrl = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
            | Gtk.EventControllerScrollFlags.DISCRETE
        )

        def on_scroll(_controller, _dx, dy):
            if not scale.get_sensitive() or dy == 0:
                return False
            curr = int(round(scale.get_value()))
            step = 5 if dy < 0 else -5
            new_val = max(min_val, min(max_val, curr + step))
            if new_val != curr:
                scale.set_value(new_val)
            return True

        ctrl.connect("scroll", on_scroll)
        scale.add_controller(ctrl)

    def _unclamp_and_unwrap_tree(self, widget):
        if isinstance(widget, Adw.Clamp):
            widget.set_maximum_size(1100)
            widget.set_tightening_threshold(800)
        elif isinstance(widget, Gtk.Label):
            widget.set_ellipsize(Pango.EllipsizeMode.NONE)
        child = widget.get_first_child()
        while child:
            self._unclamp_and_unwrap_tree(child)
            child = child.get_next_sibling()

    def present_control_window(self):
        if self.window is None:
            self._build_control_window()
        self._sync_window_from_config()
        self._update_window_telemetry()
        self.window.present()

    def _build_control_window(self):
        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title("Dell G15 Control Center")
        self.window.set_icon_name("io.github.murilogiatti.DellG15Control")
        self.window.set_default_size(680, 760)
        self.window.connect("close-request", self._on_window_close_request)

        self._toast_overlay = Adw.ToastOverlay()
        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        page = Adw.PreferencesPage()

        # --- Group 1: Brightness & Ambient Sync ---
        grp_bright = Adw.PreferencesGroup(
            title=tr("Iluminação e Brilho (Tecla Fn+F5)", "Backlight and Brightness (Fn+F5 Key)"),
            description=tr(
                "Sincronize automaticamente com a tela, ajuste manualmente ou use Fn+F5 para ciclar os modos.",
                "Automatically sync with screen, adjust manually, or press Fn+F5 to cycle modes.",
            ),
        )

        self._row_sync = Adw.SwitchRow(
            title=tr("Brilho Automático (Ambient Sync)", "Automatic Brightness (Ambient Sync)"),
            subtitle=tr(
                "Ajusta a intensidade dos LEDs em tempo real conforme o brilho da tela",
                "Adjusts keyboard LED intensity in real time as screen brightness changes",
            ),
        )
        self._row_sync.connect("notify::active", self._on_ui_sync_toggled)
        grp_bright.add(self._row_sync)

        self._row_manual = Adw.ActionRow(
            title=tr("Intensidade Manual do Teclado", "Manual Keyboard Intensity"),
            subtitle=tr(
                "Deslize ou use a roda do mouse (±5%) para definir o brilho fixo (0% a 100%)",
                "Slide or scroll mouse wheel (±5%) to set fixed brightness (0% to 100%)",
            ),
        )
        self._scale_manual = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        self._scale_manual.set_size_request(200, -1)
        self._scale_manual.set_draw_value(True)
        self._scale_manual.set_hexpand(True)
        for mark in (0, 10, 30, 50, 75, 100):
            self._scale_manual.add_mark(mark, Gtk.PositionType.BOTTOM, None)
        self._attach_scroll_step_5(self._scale_manual, 0, 100)
        self._scale_manual.connect("value-changed", self._on_ui_manual_changed)
        self._row_manual.add_suffix(self._scale_manual)
        grp_bright.add(self._row_manual)

        self._row_power_cap = Adw.SwitchRow(
            title=tr(
                "Proteção do Limitador de Energia (Cap 230)",
                "Power Limiter Protection (Cap 230)",
            ),
            subtitle=tr(
                "Limita o pico RGB em #E6E6E6 para evitar quedas de brilho no controlador",
                "Caps RGB peak at #E6E6E6 to prevent controller power-drop dimming",
            ),
        )
        self._row_power_cap.connect("notify::active", self._on_ui_power_cap_toggled)
        grp_bright.add(self._row_power_cap)
        page.add(grp_bright)

        # --- Group 2: Colors & Zones (Dynamic Unified vs 4-Zone View) ---
        grp_zones = Adw.PreferencesGroup(
            title=tr("Cores RGB e Zonas do Teclado", "RGB Colors and Keyboard Zones"),
            description=tr(
                "Use uma cor única para o teclado inteiro ou personalize cada uma das 4 regiões.",
                "Use a single color for the whole keyboard or customize each of the 4 regions.",
            ),
        )

        self._row_per_zone = Adw.SwitchRow(
            title=tr(
                "Separar em 4 Zonas Independentes",
                "Split into 4 Independent Zones",
            ),
            subtitle=tr(
                "Permite escolher cores diferentes para WASD, Centro-Esq, Centro-Dir e NumPad",
                "Allows choosing different colors for WASD, Center-Left, Center-Right and NumPad",
            ),
        )
        self._row_per_zone.connect("notify::active", self._on_ui_per_zone_toggled)
        grp_zones.add(self._row_per_zone)

        self._row_unified = Adw.ActionRow(
            title=tr("Cor do Teclado Inteiro", "Whole Keyboard Color"),
            subtitle=tr(
                "Clique no botão de cor ao lado para escolher uma cor personalizada para todas as teclas",
                "Click the color button to pick a custom RGB color for all keys",
            ),
        )
        unified_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        unified_btn_box.set_valign(Gtk.Align.CENTER)

        self._btn_unified_1 = Gtk.ColorDialogButton(
            dialog=Gtk.ColorDialog(with_alpha=False)
        )
        self._btn_unified_1.set_tooltip_text(
            tr("Selecionar Cor Principal do Teclado", "Select Primary Keyboard Color")
        )
        self._btn_unified_1.connect("notify::rgba", self._on_ui_unified_color_changed, False)
        unified_btn_box.append(self._btn_unified_1)

        self._btn_unified_2 = Gtk.ColorDialogButton(
            dialog=Gtk.ColorDialog(with_alpha=False)
        )
        self._btn_unified_2.set_tooltip_text(
            tr("Selecionar 2ª Cor (usada no efeito Transição/Morph)", "Select 2nd Color (used in Morph effect)")
        )
        self._btn_unified_2.connect("notify::rgba", self._on_ui_unified_color_changed, True)
        unified_btn_box.append(self._btn_unified_2)

        self._row_unified.add_suffix(unified_btn_box)
        grp_zones.add(self._row_unified)

        zones_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        zones_outer.set_margin_top(8)
        zones_outer.set_margin_bottom(8)
        zones_outer.set_margin_start(10)
        zones_outer.set_margin_end(10)

        lbl_zones_hint = Gtk.Label(
            label=tr(
                "Clique no seletor de cada região do teclado para alterar sua cor individual:",
                "Click each keyboard region's picker to customize its individual color:",
            ),
            xalign=0,
        )
        lbl_zones_hint.add_css_class("dim-label")
        lbl_zones_hint.add_css_class("caption")
        zones_outer.append(lbl_zones_hint)

        zones_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        zones_box.set_homogeneous(True)

        zone_titles = (
            tr("Zona 1 (WASD)", "Zone 1 (WASD)"),
            tr("Zona 2 (Centro-Esq)", "Zone 2 (Center-L)"),
            tr("Zona 3 (Centro-Dir)", "Zone 3 (Center-R)"),
            tr("Zona 4 (NumPad)", "Zone 4 (NumPad)"),
        )
        self._color_btns_1 = []
        self._color_btns_2 = []

        for idx in range(4):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            card.add_css_class("card")

            lbl = Gtk.Label(label=zone_titles[idx])
            lbl.set_margin_top(8)
            lbl.add_css_class("caption-heading")
            card.append(lbl)

            btn1 = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False))
            btn1.set_halign(Gtk.Align.CENTER)
            btn1.set_margin_bottom(8)
            btn1.set_tooltip_text(f"{zone_titles[idx]} — {tr('Cor Principal', 'Primary Color')}")
            btn1.connect("notify::rgba", self._on_ui_zone_color_changed, idx, False)
            self._color_btns_1.append(btn1)
            card.append(btn1)

            btn2 = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False))
            btn2.set_halign(Gtk.Align.CENTER)
            btn2.set_margin_bottom(8)
            btn2.set_tooltip_text(f"{zone_titles[idx]} — {tr('2ª Cor (Morph)', '2nd Color (Morph)')}")
            btn2.connect("notify::rgba", self._on_ui_zone_color_changed, idx, True)
            self._color_btns_2.append(btn2)
            card.append(btn2)

            zones_box.append(card)

        zones_outer.append(zones_box)
        self._row_zone_cards = Adw.PreferencesRow(activatable=False)
        self._row_zone_cards.set_child(zones_outer)
        grp_zones.add(self._row_zone_cards)

        palette_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        palette_outer.set_margin_top(8)
        palette_outer.set_margin_bottom(8)
        palette_outer.set_margin_start(12)
        palette_outer.set_margin_end(12)

        lbl_palette = Gtk.Label(
            label=tr(
                "Cores Pré-Selecionadas (clique em qualquer opção para aplicar no teclado):",
                "Pre-Selected Colors (click any preset to apply to the keyboard):",
            ),
            xalign=0,
        )
        lbl_palette.add_css_class("dim-label")
        lbl_palette.add_css_class("caption")
        palette_outer.append(lbl_palette)

        grid = Gtk.Grid(column_spacing=6, row_spacing=6, column_homogeneous=True)
        for idx, (code, hex_val, lbl_pt, lbl_en) in enumerate(COLOR_PRESETS):
            btn = Gtk.Button()
            btn.add_css_class("g15-preset-btn")
            btn.set_tooltip_text(f"{tr(lbl_pt, lbl_en)} (#{hex_val})")

            inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            inner.set_halign(Gtk.Align.START)

            dot = Gtk.Box()
            dot.add_css_class("g15-dot")
            dot.add_css_class(f"dot-{code}")
            dot.set_valign(Gtk.Align.CENTER)
            inner.append(dot)

            txt = Gtk.Label(label=tr(lbl_pt, lbl_en))
            txt.add_css_class("caption")
            inner.append(txt)

            btn.set_child(inner)
            btn.connect("clicked", lambda _b, h=hex_val: self._apply_quick_color(h))
            grid.attach(btn, idx % 4, idx // 4, 1, 1)

        palette_outer.append(grid)
        row_palette = Adw.PreferencesRow(activatable=False)
        row_palette.set_child(palette_outer)
        grp_zones.add(row_palette)
        page.add(grp_zones)

        # --- Group 3: Hardware Effects & Onboard Memory ---
        grp_fx = Adw.PreferencesGroup(
            title=tr("Efeitos de Hardware e Memória", "Hardware Effects and Memory"),
            description=tr(
                "Animações executadas pelo próprio chip do teclado (zero uso de processador).",
                "Animations executed directly by the keyboard chip (zero CPU usage).",
            ),
        )

        self._row_mode = Adw.ComboRow(
            title=tr("Efeito de Iluminação", "Lighting Effect"),
            subtitle=tr(
                "Escolha entre cor estática, respiração, pulso, transição (morph) ou arco-íris",
                "Choose between static color, breathing, pulse, two-color morph or rainbow",
            ),
        )
        mode_strings = Gtk.StringList.new([tr(pt, en) for _k, pt, en in EFFECT_MODES])
        self._row_mode.set_factory(self._make_full_text_combo_factory())
        self._row_mode.set_model(mode_strings)
        self._row_mode.connect("notify::selected", self._on_ui_mode_changed)
        grp_fx.add(self._row_mode)

        self._row_speed = Adw.ActionRow(
            title=tr("Velocidade da Animação (%)", "Animation Speed (%)"),
            subtitle=tr(
                "Use a roda do mouse (±5%) para ajustar (10% = bem lento e suave, 100% = rápido)",
                "Use mouse wheel (±5%) to adjust (10% = very slow and smooth, 100% = fast)",
            ),
        )
        self._scale_speed = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 100, 5)
        self._scale_speed.set_size_request(190, -1)
        self._scale_speed.set_draw_value(True)
        for mark in (10, 25, 50, 75, 100):
            self._scale_speed.add_mark(mark, Gtk.PositionType.BOTTOM, None)
        self._attach_scroll_step_5(self._scale_speed, 10, 100)
        self._scale_speed.connect("value-changed", self._on_ui_speed_changed)
        self._row_speed.add_suffix(self._scale_speed)
        grp_fx.add(self._row_speed)

        row_boot = Adw.ActionRow(
            title=tr(
                "Memória Interna do Teclado (Boot)",
                "Onboard Keyboard Memory (Boot)",
            ),
            subtitle=tr(
                "Grava a cor e efeito atuais no chip do teclado para ligar já configurado",
                "Saves current color and effect to the keyboard chip so it powers on configured",
            ),
        )
        btn_boot = Gtk.Button(label=tr("💾 Salvar no Teclado", "💾 Save to Keyboard"))
        btn_boot.set_valign(Gtk.Align.CENTER)
        btn_boot.set_tooltip_text(
            tr(
                "Gravar perfil no slot de usuário 0x0061 do microcontrolador do teclado",
                "Write profile to user slot 0x0061 of the keyboard microcontroller",
            )
        )
        btn_boot.connect("clicked", lambda _b: self._trigger_save_boot())
        row_boot.add_suffix(btn_boot)
        grp_fx.add(row_boot)
        page.add(grp_fx)

        # --- Group 4: G-Mode (Fn+F9), Telemetry & Power Profile ---
        grp_hw = Adw.PreferencesGroup(
            title=tr(
                "Modo G (Fn+F9), Energia e Sensores",
                "G-Mode (Fn+F9), Power and Sensors",
            ),
        )

        self._row_gmode = Adw.SwitchRow(
            title=tr("🚀 Modo G / Game Shift (Tecla Fn+F9)", "🚀 G-Mode / Game Shift (Fn+F9 Key)"),
            subtitle=tr(
                "Ativa Alto Desempenho e aplica Vermelho Puro mantendo o brilho atual; restaura suas cores ao desligar",
                "Activates High Performance and Pure Red keeping current brightness; restores your colors when disabled",
            ),
        )
        self._row_gmode.connect("notify::active", self._on_ui_gmode_toggled)
        grp_hw.add(self._row_gmode)

        self._row_power = Adw.ComboRow(
            title=tr("Perfil Térmico e de Energia", "Thermal and Power Profile"),
            subtitle=tr(
                "Alterna entre Economia de bateria, Equilibrado ou Alto Desempenho (G-Mode)",
                "Switches between Power Saver, Balanced or High Performance (G-Mode)",
            ),
        )
        power_strings = Gtk.StringList.new([tr(pt, en) for _k, pt, en in POWER_PROFILES])
        self._row_power.set_factory(self._make_full_text_combo_factory())
        self._row_power.set_model(power_strings)
        self._row_power.connect("notify::selected", self._on_ui_power_profile_changed)
        grp_hw.add(self._row_power)

        self._row_telemetry = Adw.ActionRow(
            title=tr("Sensores Internos (Ao Vivo)", "Internal Sensors (Live)"),
            subtitle=tr(
                "Temperaturas de CPU, GPU, SSD NVMe e rotação das ventoinhas (RPM)",
                "CPU, GPU, NVMe SSD temperatures and cooling fan speeds (RPM)",
            ),
        )
        self._lbl_telemetry = Gtk.Label(label="--")
        self._lbl_telemetry.add_css_class("monospace")
        self._row_telemetry.add_suffix(self._lbl_telemetry)
        grp_hw.add(self._row_telemetry)

        self._row_update = Adw.ActionRow(
            title=tr("Atualizações do Aplicativo", "Application Updates"),
            subtitle=self._format_update_subtitle(),
        )
        self._btn_update = Gtk.Button(label=self._format_update_button_label())
        self._btn_update.set_valign(Gtk.Align.CENTER)
        self._btn_update.connect("clicked", self._on_ui_update_clicked)
        self._row_update.add_suffix(self._btn_update)
        grp_hw.add(self._row_update)

        page.add(grp_hw)
        self._unclamp_and_unwrap_tree(page)

        toolbar_view.set_content(page)
        self._toast_overlay.set_child(toolbar_view)
        self.window.set_content(self._toast_overlay)

    def _on_window_close_request(self, win):
        win.set_visible(False)
        return True

    def _sync_window_from_config(self):
        if self.window is None:
            return
        self._updating_ui = True
        try:
            sync_on = bool(self.cfg.get("sync_screen", True))
            self._row_sync.set_active(sync_on)
            self._scale_manual.set_value(int(self.cfg.get("manual_brightness", 100)))
            self._row_manual.set_sensitive(not sync_on)
            self._row_power_cap.set_active(bool(self.cfg.get("power_cap", True)))
            self._row_gmode.set_active(bool(self.cfg.get("g_mode", False)))

            per_zone = bool(self.cfg.get("per_zone", False))
            self._row_per_zone.set_active(per_zone)

            mode = str(self.cfg.get("mode", "static")).lower()
            is_morph = mode == "morph"
            mode_idx = next(
                (i for i, (k, _pt, _en) in enumerate(EFFECT_MODES) if k == mode), 0
            )
            self._row_mode.set_selected(mode_idx)
            self._scale_speed.set_value(max(10, min(100, int(self.cfg.get("speed", 40)))))
            self._row_speed.set_sensitive(mode != "static")

            self._row_unified.set_visible(not per_zone)
            self._row_zone_cards.set_visible(per_zone)

            z1 = self.cfg.get("zones_rgb", DEFAULT_CONFIG["zones_rgb"])
            z2 = self.cfg.get("zones_rgb2", DEFAULT_CONFIG["zones_rgb2"])

            self._btn_unified_1.set_rgba(hex_to_rgba(z1[0]))
            self._btn_unified_2.set_rgba(hex_to_rgba(z2[0]))
            self._btn_unified_2.set_visible(is_morph)

            for idx in range(4):
                self._color_btns_1[idx].set_rgba(hex_to_rgba(z1[idx]))
                self._color_btns_2[idx].set_rgba(hex_to_rgba(z2[idx]))
                self._color_btns_2[idx].set_visible(is_morph)

            self._refresh_update_ui()
        finally:
            self._updating_ui = False

    def _update_window_telemetry(self):
        if self.window is None:
            return
        self._lbl_telemetry.set_label(
            core.format_detailed_telemetry_label(self.telemetry) + "\n" + self._daemon_label
        )
        self._updating_ui = True
        try:
            prof_idx = next(
                (
                    i
                    for i, (k, _pt, _en) in enumerate(POWER_PROFILES)
                    if k == self.active_power_profile
                ),
                1,
            )
            self._row_power.set_sensitive(self.active_power_profile is not None)
            self._row_power.set_selected(prof_idx)
        finally:
            self._updating_ui = False

    # --- UI Signal Handlers ---
    def _on_ui_gmode_toggled(self, row, _pspec):
        if self._updating_ui:
            return
        self.toggle_g_mode(target_state=row.get_active(), notify=True)

    def _on_ui_sync_toggled(self, row, _pspec):
        if self._updating_ui:
            return
        self.cfg["sync_screen"] = row.get_active()
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        self._row_manual.set_sensitive(not row.get_active())
        save_config(self.cfg)
        self._notify_menu_updated()

    def _on_ui_manual_changed(self, scale):
        if self._updating_ui:
            return
        val = int(round(scale.get_value()))
        if self.cfg.get("manual_brightness") != val:
            self.cfg["manual_brightness"] = val
            self.cfg["sync_screen"] = False
            self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
            save_config(self.cfg)
            self._notify_menu_updated()

    def _on_ui_power_cap_toggled(self, row, _pspec):
        if self._updating_ui:
            return
        self.cfg["power_cap"] = row.get_active()
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        save_config(self.cfg)

    def _on_ui_per_zone_toggled(self, row, _pspec):
        if self._updating_ui:
            return
        self.cfg["per_zone"] = row.get_active()
        if not self.cfg["per_zone"]:
            c0 = self.cfg["zones_rgb"][0]
            self.cfg["zones_rgb"] = [c0] * 4
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        save_config(self.cfg)
        self._sync_window_from_config()
        self._notify_menu_updated()

    def _on_ui_unified_color_changed(self, btn, _pspec, is_secondary):
        if self._updating_ui:
            return
        hex_val = rgba_to_hex(btn.get_rgba())
        key = "zones_rgb2" if is_secondary else "zones_rgb"
        self.cfg[key] = [hex_val] * 4
        if not is_secondary and self.cfg.get("mode") in ("spectrum", "rainbow"):
            self.cfg["mode"] = "static"
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        save_config(self.cfg)
        self._sync_window_from_config()
        self._notify_menu_updated()

    def _on_ui_zone_color_changed(self, btn, _pspec, zone_idx, is_secondary):
        if self._updating_ui:
            return
        hex_val = rgba_to_hex(btn.get_rgba())
        key = "zones_rgb2" if is_secondary else "zones_rgb"
        self.cfg[key][zone_idx] = hex_val
        if not is_secondary and self.cfg.get("mode") in ("spectrum", "rainbow"):
            self.cfg["mode"] = "static"
        self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
        save_config(self.cfg)
        self._sync_window_from_config()
        self._notify_menu_updated()

    def _on_ui_mode_changed(self, row, _pspec):
        if self._updating_ui:
            return
        idx = row.get_selected()
        if 0 <= idx < len(EFFECT_MODES):
            mode_key = EFFECT_MODES[idx][0]
            self.cfg["mode"] = mode_key
            self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
            save_config(self.cfg)
            self._sync_window_from_config()
            self._notify_menu_updated()

    def _on_ui_speed_changed(self, scale):
        if self._updating_ui:
            return
        val = int(round(scale.get_value()))
        if self.cfg.get("speed") != val:
            self.cfg["speed"] = val
            self.cfg["force_seq"] = int(self.cfg.get("force_seq", 0)) + 1
            save_config(self.cfg)

    def _on_ui_power_profile_changed(self, row, _pspec):
        if not self._updating_ui and 0 <= row.get_selected() < len(POWER_PROFILES):
            self._apply_power_profile(POWER_PROFILES[row.get_selected()][0])


def run_gtk_app(argv):
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    start_hidden = "--show" not in argv
    app = G15ControlApp(start_hidden=start_hidden)
    return app.run(argv)
