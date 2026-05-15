from machine import Pin, freq
import machine
import time
import asyncio
import bluetooth
import struct
import gc
from ble_hid import HID
from macros import (
    KeyEvent, MouseEvent, MouseMoveEvent, WheelEvent, DelayEvent,
    get_macro_registry, parse_custom_macro
)
from settings import load_settings
from wifi_manager import connect_wifi, disconnect_wifi
from web_config import start_web_server, stop_web_server

freq(160000000)
MY_HID_NAME = 'ble_keyboard_mouse'
led_pin = Pin(2, Pin.OUT)

_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GET_SECRET = 21
_IRQ_SET_SECRET = 20
_IRQ_ENCRYPTION_UPDATE = 28

SETTINGS = load_settings()
MACRO_REGISTRY = get_macro_registry()

def _build_config():
    configs = SETTINGS.get("button_configs", [])
    pins = []
    macros = []
    for cfg in configs:
        pins.append(Pin(cfg.get("pin", 5), Pin.IN, Pin.PULL_UP))
        macro_name = cfg.get("macro", "F12_AUTO")
        if macro_name == "CUSTOM":
            custom_data = cfg.get("custom_events")
            macro = parse_custom_macro(custom_data)
            if macro is None:
                macro = MACRO_REGISTRY.get("F12_AUTO", None)
            macros.append(macro)
        elif macro_name == "DISABLED":
            macros.append(None)
        else:
            macros.append(MACRO_REGISTRY.get(macro_name, MACRO_REGISTRY.get("F12_AUTO")))
    gnd_pins = SETTINGS.get("gnd_pins", [19, 21, 25])
    for g in gnd_pins:
        Pin(g, Pin.OUT, 0)
    return pins, macros

button_pins, button_macros = _build_config()

trigger_indices = SETTINGS.get("trigger_pins", [0, 1])
long_press_ms = SETTINGS.get("long_press_ms", 3000)

class MyHID(HID):
    def __init__(self, name):
        self.secrets = {}
        self.load_secrets()
        super().__init__(name)
        try:
            self._ble.config(bond=True, le_sec=True, io=0)
        except:
            pass
        self._ble.irq(self._custom_irq)
        self.start_advertising(name)

    def load_secrets(self):
        try:
            import ble_hid_key
            self.secrets = ble_hid_key.keys
        except:
            pass

    def start_advertising(self, name):
        payload = bytearray(b'\x02\x01\x06')
        payload += b'\x03\x19\xc1\x03'
        payload += b'\x03\x03\x12\x18'
        name_bytes = name.encode()
        payload += struct.pack('B', len(name_bytes) + 1) + b'\x09' + name_bytes
        self._ble.gap_advertise(100, adv_data=payload, connectable=True)

    def _custom_irq(self, event, data):
        if event == _IRQ_GET_SECRET:
            raw_key_info = bytes(data[-1])
            for k, v in self.secrets.items():
                if k[1] == raw_key_info or raw_key_info in k[1]:
                    return v
            return None
        elif event == _IRQ_SET_SECRET:
            self.secrets[(data[0], bytes(data[1]))] = bytes(data[2])
            try:
                with open("ble_hid_key.py", "w") as f:
                    f.write("keys = " + repr(self.secrets))
            except:
                pass
            return True
        elif event == _IRQ_CENTRAL_CONNECT:
            self.conn_handle = data[0]
        elif event == _IRQ_ENCRYPTION_UPDATE:
            if data[1]:
                self.conn_handle = data[0]
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self.conn_handle = None
            self.start_advertising(MY_HID_NAME)
        return self._irq(event, data)

    def is_connected(self):
        return self.conn_handle is not None

    def send_raw(self, mod, key, pressed=True):
        if self.is_connected():
            buf = bytearray(8)
            if pressed:
                buf[0] = mod
                buf[2] = key
            try:
                self._ble.gatts_notify(self.conn_handle, self.k_rep, buf)
                if not pressed and mod != 0:
                    self._ble.gatts_notify(self.conn_handle, self.k_rep, b'\x00\x00\x00\x00\x00\x00\x00\x00')
            except:
                pass

    def send_mouse(self, buttons=0, x=0, y=0, wheel=0):
        if self.is_connected():
            x = max(min(x, 127), -127)
            y = max(min(y, 127), -127)
            wheel = max(min(wheel, 127), -127)
            buf = struct.pack('bbbb', buttons, x, y, wheel)
            try:
                self._ble.gatts_notify(self.conn_handle, self.m_rep, buf)
            except:
                pass

    def release_all(self):
        if self.is_connected():
            try:
                self._ble.gatts_notify(self.conn_handle, self.k_rep, b'\x00\x00\x00\x00\x00\x00\x00\x00')
                self.send_mouse(0, 0, 0, 0)
                time.sleep_ms(5)
                self._ble.gatts_notify(self.conn_handle, self.k_rep, b'\x00\x00\x00\x00\x00\x00\x00\x00')
            except:
                pass

ble_hid = MyHID(MY_HID_NAME)

auto_enabled = [False] * len(button_pins)
active_tasks = [None] * len(button_pins)
prev_state = [1] * len(button_pins)

config_mode_trigger = False
trigger_press_start = [0] * len(trigger_indices)

async def run_events_async(macro, idx, cancellable=False):
    for event in macro.events:
        if cancellable and macro.cancel == 1 and not auto_enabled[idx]:
            break
        if isinstance(event, KeyEvent):
            ble_hid.send_raw(event.modifier, event.keycode, (event.action == "press"))
            await asyncio.sleep_ms(max(event.delay, 10))
        elif isinstance(event, MouseEvent):
            btn_val = 1 if event.button == "left" else 2 if event.button == "right" else 4
            if event.action == "press":
                ble_hid.send_mouse(buttons=btn_val)
            else:
                ble_hid.send_mouse(buttons=0)
            await asyncio.sleep_ms(max(event.delay, 10))
        elif isinstance(event, MouseMoveEvent):
            ble_hid.send_mouse(x=event.x, y=event.y)
            await asyncio.sleep_ms(max(event.delay, 10))
        elif isinstance(event, WheelEvent):
            ble_hid.send_mouse(wheel=event.delta)
            await asyncio.sleep_ms(max(event.delay, 10))
        elif isinstance(event, DelayEvent):
            await asyncio.sleep_ms(event.delay)

async def auto_loop_task(idx):
    macro = button_macros[idx]
    try:
        while auto_enabled[idx]:
            await run_events_async(macro, idx, cancellable=True)
            if macro.auto_interval > 0:
                await asyncio.sleep_ms(macro.auto_interval)
            else:
                break
    finally:
        ble_hid.release_all()
        active_tasks[idx] = None

async def wait_for_exit_trigger():
    press_start = [0] * len(trigger_indices)
    while True:
        for i, idx in enumerate(trigger_indices):
            if 0 <= idx < len(button_pins):
                if button_pins[idx].value() == 0:
                    if press_start[i] == 0:
                        press_start[i] = time.ticks_ms()
                else:
                    press_start[i] = 0
        if all(t > 0 for t in press_start):
            elapsed = time.ticks_diff(time.ticks_ms(), min(press_start))
            if elapsed >= long_press_ms:
                return
        await asyncio.sleep_ms(50)

async def _blink_led(interval_ms):
    while True:
        led_pin.value(not led_pin.value())
        await asyncio.sleep_ms(interval_ms)

async def config_mode():
    global config_mode_trigger
    print("Entering config mode...")
    config_mode_trigger = True
    ble_hid.release_all()
    print("Connecting to WiFi...")
    led_pin.value(0)
    blink_task = asyncio.create_task(_blink_led(200))
    success, ip = connect_wifi(timeout=10)
    blink_task.cancel()
    led_pin.value(0)
    if not success:
        print("WiFi connection failed, returning to normal mode")
        config_mode_trigger = False
        return
    print("WiFi connected. IP: %s" % ip)
    print("Config mode: http://%s" % ip)
    server_task = start_web_server()
    await wait_for_exit_trigger()
    print("Exit trigger detected, saving and rebooting...")
    stop_web_server()
    server_task.cancel()
    await asyncio.sleep_ms(500)
    machine.reset()

async def button_scanner():
    global trigger_press_start, config_mode_trigger
    while True:
        if config_mode_trigger:
            await asyncio.sleep_ms(100)
            continue

        trigger_held = True
        for idx in trigger_indices:
            if 0 <= idx < len(button_pins):
                if button_pins[idx].value() != 0:
                    trigger_held = False
                    break
            else:
                trigger_held = False
                break

        if trigger_held:
            if trigger_press_start[0] == 0:
                now = time.ticks_ms()
                trigger_press_start = [now] * len(trigger_indices)
            elapsed = time.ticks_diff(time.ticks_ms(), trigger_press_start[0])
            if elapsed >= long_press_ms:
                for i in range(len(button_pins)):
                    auto_enabled[i] = False
                    if active_tasks[i]:
                        active_tasks[i].cancel()
                        active_tasks[i] = None
                ble_hid.release_all()
                trigger_press_start = [0] * len(trigger_indices)
                await config_mode()
                continue
        else:
            trigger_press_start = [0] * len(trigger_indices)

        for i, pin in enumerate(button_pins):
            if trigger_held and i in trigger_indices:
                prev_state[i] = pin.value()
                continue
            val = pin.value()
            if val != prev_state[i]:
                await asyncio.sleep_ms(15)
                if pin.value() == val:
                    prev_state[i] = val
                    macro = button_macros[i]
                    if macro is None:
                        continue
                    if val == 0:
                        if macro.long_press == 1:
                            auto_enabled[i] = True
                            if active_tasks[i]:
                                active_tasks[i].cancel()
                            active_tasks[i] = asyncio.create_task(auto_loop_task(i))
                        elif macro.auto_interval > 0:
                            auto_enabled[i] = not auto_enabled[i]
                            if auto_enabled[i]:
                                if active_tasks[i]:
                                    active_tasks[i].cancel()
                                active_tasks[i] = asyncio.create_task(auto_loop_task(i))
                            else:
                                if active_tasks[i]:
                                    active_tasks[i].cancel()
                        elif macro.key:
                            ble_hid.send_raw(macro.modifiers, macro.key, True)
                        elif macro.button:
                            btn_val = 1 if macro.button == "left" else 2 if macro.button == "right" else 4
                            ble_hid.send_mouse(buttons=btn_val)
                        else:
                            asyncio.create_task(run_events_async(macro, i, cancellable=False))
                    else:
                        if macro.long_press == 1:
                            auto_enabled[i] = False
                            if macro.cancel == 1 and active_tasks[i]:
                                active_tasks[i].cancel()
                                active_tasks[i] = None
                            ble_hid.release_all()
                        elif macro.key:
                            ble_hid.send_raw(macro.modifiers, macro.key, False)
                        elif macro.button:
                            ble_hid.send_mouse(buttons=0)
        await asyncio.sleep_ms(5)

async def main():
    print("BLE System Started: %s" % MY_HID_NAME)
    asyncio.create_task(button_scanner())

    heartbeat_count = 0
    while True:
        if config_mode_trigger:
            await asyncio.sleep_ms(500)
            continue
        if ble_hid.is_connected():
            heartbeat_count += 1
            if heartbeat_count >= 10:
                led_pin.value(0)
                await asyncio.sleep_ms(50)
                led_pin.value(1)
                heartbeat_count = 0
            else:
                led_pin.value(1)
        else:
            led_pin.value(not led_pin.value())
            heartbeat_count = 0
        gc.collect()
        await asyncio.sleep_ms(500)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass