import ujson
import os

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

def _defaults_copy():
    return ujson.loads(ujson.dumps(DEFAULT_SETTINGS))

def _atomic_write(data):
    tmp = SETTINGS_FILE + ".tmp"
    with open(tmp, "w") as f:
        ujson.dump(data, f)
    try:
        os.remove(SETTINGS_FILE)
    except OSError:
        pass
    os.rename(tmp, SETTINGS_FILE)

def load_settings():
    data = None
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = ujson.load(f)
    except OSError:
        print("settings.json not found, creating defaults")
    except Exception as e:
        print("settings.json corrupt:", e)
        try:
            os.rename(SETTINGS_FILE, "settings.json.bak")
            print("Corrupt settings backed up to settings.json.bak")
        except Exception:
            pass
    if isinstance(data, dict) and "button_configs" in data:
        # 读取路径绝不写文件：缺失字段仅在内存中补齐
        for key in DEFAULT_SETTINGS:
            if key not in data:
                data[key] = DEFAULT_SETTINGS[key]
        return data
    defaults = _defaults_copy()
    try:
        _atomic_write(defaults)
        print("Created settings.json with default values")
    except Exception as e:
        print("settings write:", e)
    return defaults

def save_settings(data):
    current = _defaults_copy()
    old_configs = None
    try:
        with open(SETTINGS_FILE, "r") as f:
            old = ujson.load(f)
            if "button_configs" in old:
                current = old
                for key in DEFAULT_SETTINGS:
                    if key not in current:
                        current[key] = DEFAULT_SETTINGS[key]
                old_configs = old.get("button_configs", [])
    except:
        pass
    current.update(data)
    if "button_configs" in data and old_configs:
        new_configs = data["button_configs"]
        for i, cfg in enumerate(current["button_configs"]):
            if i < len(new_configs):
                if new_configs[i].get("macro") == "CUSTOM" and new_configs[i].get("custom_events") is None:
                    if i < len(old_configs) and old_configs[i].get("custom_events") is not None:
                        cfg["custom_events"] = old_configs[i]["custom_events"]
    try:
        _atomic_write(current)
    except Exception as e:
        print("settings write:", e)