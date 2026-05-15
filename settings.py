import ujson
from macros import get_macro_names, normalize_custom_macro

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "button_configs": [
        {"pin": 5,  "macro": "F12_AUTO", "custom_events": None},
        {"pin": 18, "macro": "F11_AUTO", "custom_events": None},
        {"pin": 26, "macro": "T_AUTO",   "custom_events": None},
        {"pin": 27, "macro": "R_AUTO",   "custom_events": None},
        {"pin": 12, "macro": "W_SWITCH", "custom_events": None},
        {"pin": 13, "macro": "LONG_SHIFT_T", "custom_events": None},
        {"pin": 23, "macro": "UP",       "custom_events": None},
        {"pin": 22, "macro": "LEFT",     "custom_events": None},
        {"pin": 32, "macro": "RIGHT",    "custom_events": None},
        {"pin": 33, "macro": "DOWN",     "custom_events": None}
    ],
    "gnd_pins": [19, 21, 25],
    "trigger_pins": [0, 1],
    "long_press_ms": 3000,
    "web_host": "0.0.0.0",
    "web_port": 80,
    "wifi_ssid": "",
    "wifi_password": ""
}


def _clone_default_settings():
    return ujson.loads(ujson.dumps(DEFAULT_SETTINGS))


def _int_value(value, default=0, minimum=None, maximum=None):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    if minimum is not None and value < minimum:
        return minimum
    if maximum is not None and value > maximum:
        return maximum
    return value


def _str_value(value, default=""):
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _normalize_pin(value, default):
    # Keep validation conservative: reject impossible ESP32 GPIO numbers,
    # but do not encode board-specific policy here.
    value = _int_value(value, default)
    if value < 0 or value > 39:
        return default
    return value


def _normalize_button_configs(configs, defaults):
    macro_names = get_macro_names()
    if not isinstance(configs, list):
        configs = []
    normalized = []
    count = len(configs) if configs else len(defaults)
    for i in range(count):
        default_cfg = defaults[i] if i < len(defaults) else defaults[-1]
        cfg = configs[i] if i < len(configs) and isinstance(configs[i], dict) else {}
        macro_name = cfg.get("macro", default_cfg.get("macro", "F12_AUTO"))
        if macro_name not in macro_names:
            macro_name = default_cfg.get("macro", "F12_AUTO")
        custom_events = cfg.get("custom_events", None)
        if macro_name == "CUSTOM":
            custom_events = normalize_custom_macro(custom_events)
            if custom_events is None:
                macro_name = default_cfg.get("macro", "F12_AUTO")
        elif custom_events is not None:
            custom_events = normalize_custom_macro(custom_events)
        normalized.append({
            "pin": _normalize_pin(cfg.get("pin", default_cfg.get("pin", 5)), default_cfg.get("pin", 5)),
            "macro": macro_name,
            "custom_events": custom_events
        })
    return normalized


def _normalize_pin_list(values, defaults):
    if not isinstance(values, list):
        values = []
    normalized = []
    for i, value in enumerate(values):
        default = defaults[i] if i < len(defaults) else defaults[-1]
        normalized.append(_normalize_pin(value, default))
    return normalized or list(defaults)


def _normalize_trigger_indices(values, button_count):
    if not isinstance(values, list):
        values = []
    normalized = []
    for value in values:
        idx = _int_value(value, -1)
        if 0 <= idx < button_count and idx not in normalized:
            normalized.append(idx)
    if normalized:
        return normalized
    return [idx for idx in DEFAULT_SETTINGS["trigger_pins"] if idx < button_count]


def normalize_settings(data):
    defaults = _clone_default_settings()
    if not isinstance(data, dict):
        data = {}
    settings = defaults
    button_configs = _normalize_button_configs(data.get("button_configs"), defaults["button_configs"])
    settings["button_configs"] = button_configs
    settings["gnd_pins"] = _normalize_pin_list(data.get("gnd_pins"), defaults["gnd_pins"])
    settings["trigger_pins"] = _normalize_trigger_indices(data.get("trigger_pins"), len(button_configs))
    settings["long_press_ms"] = _int_value(data.get("long_press_ms", defaults["long_press_ms"]), defaults["long_press_ms"], 500)
    settings["web_host"] = _str_value(data.get("web_host", defaults["web_host"]), defaults["web_host"])
    settings["web_port"] = _int_value(data.get("web_port", defaults["web_port"]), defaults["web_port"], 1, 65535)
    settings["wifi_ssid"] = _str_value(data.get("wifi_ssid", defaults["wifi_ssid"]), defaults["wifi_ssid"])
    settings["wifi_password"] = _str_value(data.get("wifi_password", defaults["wifi_password"]), defaults["wifi_password"])
    return settings


def _write_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        ujson.dump(data, f)


def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = ujson.load(f)
        normalized = normalize_settings(data)
        if normalized != data:
            _write_settings(normalized)
            print("Normalized settings.json")
        return normalized
    except OSError:
        defaults = _clone_default_settings()
        try:
            _write_settings(defaults)
            print("Created settings.json with default values")
        except OSError as e:
            print("Unable to create settings.json:", e)
        return defaults
    except (ValueError, TypeError) as e:
        defaults = _clone_default_settings()
        print("Invalid settings.json, using defaults:", e)
        return defaults


def save_settings(data):
    current = _clone_default_settings()
    old_configs = None
    try:
        with open(SETTINGS_FILE, "r") as f:
            current = normalize_settings(ujson.load(f))
            old_configs = current.get("button_configs", [])
    except (OSError, ValueError, TypeError) as e:
        print("Unable to load current settings before save:", e)
    if not isinstance(data, dict):
        data = {}
    current.update(data)
    if "button_configs" in data and old_configs:
        new_configs = data["button_configs"] if isinstance(data["button_configs"], list) else []
        for i, cfg in enumerate(current.get("button_configs", [])):
            if i < len(new_configs) and isinstance(new_configs[i], dict):
                if new_configs[i].get("macro") == "CUSTOM" and new_configs[i].get("custom_events") is None:
                    if i < len(old_configs) and old_configs[i].get("custom_events") is not None:
                        cfg["custom_events"] = old_configs[i]["custom_events"]
    _write_settings(normalize_settings(current))
