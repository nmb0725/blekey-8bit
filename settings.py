import ujson

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

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = ujson.load(f)
            if "button_configs" in data:
                merged = False
                for key in DEFAULT_SETTINGS:
                    if key not in data:
                        data[key] = DEFAULT_SETTINGS[key]
                        merged = True
                if merged:
                    try:
                        with open(SETTINGS_FILE, "w") as f:
                            ujson.dump(data, f)
                        print("Merged missing default fields into settings.json")
                    except:
                        pass
                return data
    except:
        pass
    defaults = DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "w") as f:
            ujson.dump(defaults, f)
        print("Created settings.json with default values")
    except:
        pass
    return defaults

def save_settings(data):
    current = DEFAULT_SETTINGS.copy()
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
    with open(SETTINGS_FILE, "w") as f:
        ujson.dump(current, f)