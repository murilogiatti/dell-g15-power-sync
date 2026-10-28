"""Configuration shared by daemon and interfaces; Python standard library only."""
import contextlib
import copy
import fcntl
import json
import math
import os
import tempfile
VALID_MODES = ("static", "breathing", "pulse", "morph", "spectrum", "rainbow")
DEFAULT_CONFIG = {
    "sync_screen": True,
    "manual_brightness": 100,
    "mode": "static",
    "speed": 40,
    "per_zone": False,
    "zones_rgb": ["E6E6E6", "E6E6E6", "E6E6E6", "E6E6E6"],
    "zones_rgb2": ["00E5FF", "00E5FF", "00E5FF", "00E5FF"],
    "power_cap": True,
    "save_boot": False,
    "save_boot_seq": 0,
    "save_boot_status": None,
    "g_mode": False,
    "pre_gmode": None,
    "force_seq": 0,
}

def _sanitize_hex_color(val, fallback):
    clean = str(val or "").lstrip("#").strip().upper()
    if len(clean) == 6 and all(c in "0123456789ABCDEF" for c in clean):
        try:
            int(clean, 16)
            return clean
        except ValueError:
            pass
    return fallback


def _safe_int(val, default, min_val=None, max_val=None):
    if isinstance(val, bool) or val is None:
        res = default
    elif isinstance(val, int):
        res = val
    elif isinstance(val, float):
        if not math.isfinite(val):
            res = default
        else:
            res = int(val)
    elif isinstance(val, str):
        s = val.strip()
        if not s:
            res = default
        else:
            try:
                res = int(s)
            except ValueError:
                try:
                    f = float(s)
                    res = int(f) if math.isfinite(f) else default
                except (ValueError, OverflowError):
                    res = default
    else:
        res = default
    if min_val is not None:
        res = max(min_val, res)
    if max_val is not None:
        res = min(max_val, res)
    return res


def normalize_config(raw):
    cfg = dict(DEFAULT_CONFIG)
    cfg["zones_rgb"] = list(DEFAULT_CONFIG["zones_rgb"])
    cfg["zones_rgb2"] = list(DEFAULT_CONFIG["zones_rgb2"])
    if not isinstance(raw, dict):
        return cfg

    for bool_key in ("sync_screen", "per_zone", "power_cap", "save_boot", "g_mode"):
        if isinstance(raw.get(bool_key), bool):
            cfg[bool_key] = raw[bool_key]

    cfg["manual_brightness"] = _safe_int(raw.get("manual_brightness"), 100, 0, 100)
    cfg["speed"] = _safe_int(raw.get("speed"), 40, 10, 100)
    cfg["force_seq"] = _safe_int(raw.get("force_seq"), 0, 0, 2_000_000_000)

    cfg["save_boot_seq"] = _safe_int(raw.get("save_boot_seq"), 0, 0, 9_223_372_036_854_775_807)

    raw_mode = raw.get("mode")
    if isinstance(raw_mode, str) and raw_mode.strip().lower() in VALID_MODES:
        cfg["mode"] = raw_mode.strip().lower()

    for key, fallback in (("zones_rgb", "E6E6E6"), ("zones_rgb2", "00E5FF")):
        arr = raw.get(key)
        if isinstance(arr, list) and len(arr) >= 4:
            cfg[key] = [_sanitize_hex_color(x, fallback) for x in arr[:4]]
        else:
            cfg[key] = [fallback] * 4

    pre = raw.get("pre_gmode")
    if isinstance(pre, dict):
        pre_mode = str(pre.get("mode", "static")).strip().lower()
        if pre_mode not in VALID_MODES:
            pre_mode = "static"
        pre_zones = pre.get("zones_rgb")
        if isinstance(pre_zones, list) and len(pre_zones) >= 4:
            norm_pre_zones = [_sanitize_hex_color(x, "E6E6E6") for x in pre_zones[:4]]
        else:
            norm_pre_zones = list(DEFAULT_CONFIG["zones_rgb"])
        pre_prof = pre.get("power_profile")
        if not isinstance(pre_prof, str) or pre_prof not in (
            "power-saver",
            "balanced",
            "performance",
        ):
            pre_prof = "balanced"
        cfg["pre_gmode"] = {
            "mode": pre_mode,
            "per_zone": bool(pre.get("per_zone", False))
            if isinstance(pre.get("per_zone"), bool)
            else False,
            "zones_rgb": norm_pre_zones,
            "power_profile": pre_prof,
        }
    else:
        cfg["pre_gmode"] = None

    sbs = raw.get("save_boot_status")
    if isinstance(sbs, dict):
        state = str(sbs.get("state", "")).strip().lower()
        ok_val = sbs.get("ok")
        if state in ("running", "done") or isinstance(ok_val, bool):
            if state not in ("running", "done"):
                state = "done"
            cfg["save_boot_status"] = {
                "seq": _safe_int(sbs.get("seq"), 0, 0, 9_223_372_036_854_775_807),
                "state": state,
                "ok": bool(ok_val) if isinstance(ok_val, bool) else None,
            }
        else:
            cfg["save_boot_status"] = None
    else:
        cfg["save_boot_status"] = None

    return cfg



class ConfigSnapshot(dict):
    def __init__(self, values):
        super().__init__(values)
        self.baseline = copy.deepcopy(values)


def load_config(path):
    try:
        with open(path, encoding="utf-8") as stream:
            raw = json.load(stream)
    except (OSError, ValueError):
        raw = None
    return ConfigSnapshot(normalize_config(raw))


@contextlib.contextmanager
def config_lock(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(str(path) + ".lock", "a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def write_json(path, value):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".g15-", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def save_config(cfg, path):
    with config_lock(path):
        latest = load_config(path)
        baseline = getattr(cfg, "baseline", None)
        changes = {k: copy.deepcopy(v) for k, v in cfg.items()
                   if baseline is None or baseline.get(k) != v}
        if "force_seq" in changes:
            changes["force_seq"] = min(2_000_000_000, max(latest["force_seq"] + 1, changes["force_seq"]))
        # Never replace a newer boot request/feedback with an old UI snapshot.
        if latest["save_boot_seq"] > cfg.get("save_boot_seq", 0):
            for k in ("save_boot_seq", "save_boot", "save_boot_status"):
                changes.pop(k, None)
        latest.update(changes)
        merged = normalize_config(latest)
        write_json(path, merged)
    cfg.clear()
    cfg.update(merged)
    if isinstance(cfg, ConfigSnapshot):
        cfg.baseline = copy.deepcopy(merged)
    return cfg


def update_config(mutator, path):
    with config_lock(path):
        cfg = load_config(path)
        mutator(cfg)
        normalized = normalize_config(cfg)
        write_json(path, normalized)
    return ConfigSnapshot(normalized)
