from collections import namedtuple

KeyEvent = namedtuple("KeyEvent", ["delay", "action", "modifier", "keycode"])
MouseEvent = namedtuple("MouseEvent", ["delay", "action", "button"])
MouseMoveEvent = namedtuple("MouseMoveEvent", ["delay", "action", "x", "y"])
WheelEvent = namedtuple("WheelEvent", ["delay", "action", "delta"])
DelayEvent = namedtuple("DelayEvent", ["delay", "action"])
KeyMacro = namedtuple("KeyMacro", ["events", "auto_interval", "long_press", "key", "modifiers", "button", "cancel"])


def _build_macro_registry():
    LEFT_CLICK_SPAM = KeyMacro(events=[
        MouseEvent(delay=0, action="press", button="left"),
        MouseEvent(delay=50, action="release", button="left")
    ], auto_interval=50, long_press=1, key=None, modifiers=0x00, button=None, cancel=1)

    MOUSE_WIGGLE = KeyMacro(events=[
        MouseMoveEvent(delay=0, action="move", x=50, y=0),
        DelayEvent(delay=200, action="delay"),
        MouseMoveEvent(delay=0, action="move", x=-50, y=0)
    ], auto_interval=200, long_press=1, key=None, modifiers=0x00, button=None, cancel=0)

    SCREENSHOT_COMBO = KeyMacro(events=[
        KeyEvent(delay=0, action="press", modifier=0x01, keycode=0x00),
        KeyEvent(delay=10, action="press", modifier=0x05, keycode=0x00),
        KeyEvent(delay=10, action="press", modifier=0x05, keycode=0x04),
        KeyEvent(delay=50, action="release", modifier=0x05, keycode=0x04),
        KeyEvent(delay=10, action="release", modifier=0x01, keycode=0x00),
        KeyEvent(delay=10, action="release", modifier=0x00, keycode=0x00)
    ], auto_interval=0, long_press=0, key=None, modifiers=0x00, button=None, cancel=1)

    F11_AUTO = KeyMacro(
        events=[KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x44),
                KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x44)],
        auto_interval=50, long_press=1, key=None, modifiers=0, button=None, cancel=1
    )
    F12_AUTO = KeyMacro(
        events=[KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x45),
                KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x45)],
        auto_interval=50, long_press=1, key=None, modifiers=0, button=None, cancel=1
    )
    R_AUTO = KeyMacro(
        events=[KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x15),
                KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x15)],
        auto_interval=150, long_press=0, key=None, modifiers=0, button=None, cancel=1
    )
    T_AUTO = KeyMacro(
        events=[KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x17),
                KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x17)],
        auto_interval=300, long_press=0, key=None, modifiers=0, button=None, cancel=1
    )
    LONG_SHIFT_T = KeyMacro(
        events=[
            KeyEvent(delay=0, action="press", modifier=0x02, keycode=0x00),
            KeyEvent(delay=30, action="release", modifier=0x02, keycode=0x00),
            DelayEvent(delay=200, action="delay"),
            KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x17),
            KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x17)
        ],
        auto_interval=150, long_press=1, key=None, modifiers=0, button=None, cancel=0
    )

    UP = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x52, modifiers=0, button=None, cancel=1)
    DOWN = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x51, modifiers=0, button=None, cancel=1)
    LEFT = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x50, modifiers=0, button=None, cancel=1)
    RIGHT = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x4F, modifiers=0, button=None, cancel=1)
    KEY_6 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x23, modifiers=0, button=None, cancel=1)

    CTRL_1 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x1E, modifiers=0x01, button=None, cancel=1)
    CTRL_2 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x1F, modifiers=0x01, button=None, cancel=1)
    CTRL_3 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x20, modifiers=0x01, button=None, cancel=1)
    CTRL_4 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x21, modifiers=0x01, button=None, cancel=1)

    CTRL = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x00, modifiers=0x01, button=None, cancel=1)
    F11 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x44, modifiers=0x00, button=None, cancel=1)
    F12 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x45, modifiers=0x00, button=None, cancel=1)
    TAB = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x2B, modifiers=0x00, button=None, cancel=1)
    CAPS = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x39, modifiers=0x00, button=None, cancel=1)

    LONG_PRESS_R = KeyMacro(events=[
        KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x15),
        DelayEvent(delay=1000, action="delay"),
        KeyEvent(delay=0, action="release", modifier=0x00, keycode=0x15)
    ], auto_interval=0, long_press=1, key=None, modifiers=0x00, button=None, cancel=1)

    R_LONG = KeyMacro(events=[
        KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x15),
        KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x15)
    ], auto_interval=150, long_press=1, key=None, modifiers=0x00, button=None, cancel=1)

    T_LONG = KeyMacro(events=[
        KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x17),
        KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x17)
    ], auto_interval=300, long_press=1, key=None, modifiers=0x00, button=None, cancel=1)

    AUTO_2 = KeyMacro(events=[
        KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x1F),
        KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x1F)
    ], auto_interval=50, long_press=1, key=None, modifiers=0x00, button=None, cancel=1)

    AUTO_4 = KeyMacro(events=[
        KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x21),
        KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x21)
    ], auto_interval=50, long_press=1, key=None, modifiers=0x00, button=None, cancel=1)

    AUTO_CAPS_E = KeyMacro(events=[
        KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x39),
        KeyEvent(delay=30, action="press", modifier=0x00, keycode=0x08),
        KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x08),
        KeyEvent(delay=0, action="release", modifier=0x00, keycode=0x39),
    ], auto_interval=50, long_press=1, key=None, modifiers=0x00, button=None, cancel=0)

    CTRL_SHIFT_T = KeyMacro(events=[
        KeyEvent(delay=0, action="press", modifier=0x03, keycode=0x17),
        DelayEvent(delay=0, action="delay"),
        KeyEvent(delay=0, action="release", modifier=0x03, keycode=0x17)
    ], auto_interval=0, long_press=0, key=None, modifiers=0x00, button=None, cancel=1)

    ALT_R = KeyMacro(events=[
        KeyEvent(delay=0, action="press", modifier=0x04, keycode=0x15),
        DelayEvent(delay=0, action="delay"),
        KeyEvent(delay=0, action="release", modifier=0x04, keycode=0x15)
    ], auto_interval=0, long_press=0, key=None, modifiers=0x00, button=None, cancel=1)

    LEFT_CLICK = KeyMacro(events=[
        MouseEvent(delay=0, action="press", button="left"),
        MouseEvent(delay=50, action="release", button="left")
    ], auto_interval=0, long_press=0, key=None, modifiers=0x00, button=None, cancel=1)

    MIDDLE_CLICK = KeyMacro(events=[], auto_interval=0, long_press=0, key=None, modifiers=0x00, button="middle", cancel=1)

    WHEEL_UP = KeyMacro(events=[
        WheelEvent(delay=0, action="scroll", delta=120)
    ], auto_interval=0, long_press=0, key=None, modifiers=0x00, button=None, cancel=1)

    LEFT_CLICK_AUTO = KeyMacro(events=[
        MouseEvent(delay=0, action="press", button="left"),
        MouseEvent(delay=50, action="release", button="left")
    ], auto_interval=100, long_press=0, key=None, modifiers=0x00, button=None, cancel=1)

    MOUSE_MOVE_RIGHT = KeyMacro(events=[
        MouseMoveEvent(delay=0, action="move", x=10, y=0)
    ], auto_interval=0, long_press=0, key=None, modifiers=0x00, button=None, cancel=1)

    W_SWITCH = KeyMacro(
        events=[KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x1A)],
        auto_interval=1000, long_press=0, key=None, modifiers=0x00, button=None, cancel=1
    )

    return {
        "LEFT_CLICK_SPAM": LEFT_CLICK_SPAM,
        "MOUSE_WIGGLE": MOUSE_WIGGLE,
        "SCREENSHOT_COMBO": SCREENSHOT_COMBO,
        "F11_AUTO": F11_AUTO,
        "F12_AUTO": F12_AUTO,
        "R_AUTO": R_AUTO,
        "T_AUTO": T_AUTO,
        "LONG_SHIFT_T": LONG_SHIFT_T,
        "W_SWITCH": W_SWITCH,
        "UP": UP,
        "DOWN": DOWN,
        "LEFT": LEFT,
        "RIGHT": RIGHT,
        "KEY_6": KEY_6,
        "CTRL_1": CTRL_1,
        "CTRL_2": CTRL_2,
        "CTRL_3": CTRL_3,
        "CTRL_4": CTRL_4,
        "CTRL": CTRL,
        "F11": F11,
        "F12": F12,
        "TAB": TAB,
        "CAPS": CAPS,
        "LONG_PRESS_R": LONG_PRESS_R,
        "R_LONG": R_LONG,
        "T_LONG": T_LONG,
        "AUTO_2": AUTO_2,
        "AUTO_4": AUTO_4,
        "AUTO_CAPS_E": AUTO_CAPS_E,
        "CTRL_SHIFT_T": CTRL_SHIFT_T,
        "ALT_R": ALT_R,
        "LEFT_CLICK": LEFT_CLICK,
        "MIDDLE_CLICK": MIDDLE_CLICK,
        "WHEEL_UP": WHEEL_UP,
        "LEFT_CLICK_AUTO": LEFT_CLICK_AUTO,
        "MOUSE_MOVE_RIGHT": MOUSE_MOVE_RIGHT,
    }


MACRO_REGISTRY = _build_macro_registry()


def get_macro_registry():
    return MACRO_REGISTRY


def get_macro_names():
    names = sorted(MACRO_REGISTRY.keys())
    return ["DISABLED", "CUSTOM"] + names


def parse_custom_macro(data):
    if data is None:
        return None
    events = []
    for e in data.get("custom_events", []):
        t = e.get("type", "")
        delay = e.get("delay", 0)
        if t == "key":
            events.append(KeyEvent(delay=delay, action=e.get("action", "press"),
                                   modifier=e.get("modifier", 0), keycode=e.get("keycode", 0)))
        elif t == "mouse":
            events.append(MouseEvent(delay=delay, action=e.get("action", "press"),
                                     button=e.get("button", "left")))
        elif t == "move":
            events.append(MouseMoveEvent(delay=delay, action="move",
                                         x=e.get("x", 0), y=e.get("y", 0)))
        elif t == "wheel":
            events.append(WheelEvent(delay=delay, action="scroll",
                                     delta=e.get("delta", 0)))
        elif t == "delay":
            events.append(DelayEvent(delay=delay, action="delay"))
    return KeyMacro(
        events=events,
        auto_interval=data.get("auto_interval", 0),
        long_press=data.get("long_press", 0),
        key=None,
        modifiers=0,
        button=None,
        cancel=data.get("cancel", 1)
    )


def custom_macro_to_dict(macro):
    if macro is None:
        return None
    event_list = []
    for e in macro.events:
        if isinstance(e, KeyEvent):
            event_list.append({"type": "key", "delay": e.delay, "action": e.action,
                               "modifier": e.modifier, "keycode": e.keycode})
        elif isinstance(e, MouseEvent):
            event_list.append({"type": "mouse", "delay": e.delay, "action": e.action,
                               "button": e.button})
        elif isinstance(e, MouseMoveEvent):
            event_list.append({"type": "move", "delay": e.delay, "action": "move",
                               "x": e.x, "y": e.y})
        elif isinstance(e, WheelEvent):
            event_list.append({"type": "wheel", "delay": e.delay, "action": "scroll",
                               "delta": e.delta})
        elif isinstance(e, DelayEvent):
            event_list.append({"type": "delay", "delay": e.delay, "action": "delay"})
    result = {
        "custom_events": event_list,
        "auto_interval": macro.auto_interval,
        "long_press": macro.long_press,
        "cancel": macro.cancel
    }
    # 新增：输出单键映射字段
    if macro.key is not None:
        result["key"] = macro.key
        result["modifiers"] = macro.modifiers
    if macro.button is not None:
        result["button"] = macro.button
    return result