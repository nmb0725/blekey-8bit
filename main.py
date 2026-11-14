from machine import Pin, freq
import machine
import os
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
from wifi_manager import connect_wifi_async, disconnect_wifi
import web_config
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
    for i, cfg in enumerate(configs):
        macro_name = cfg.get("macro", "F12_AUTO")
        # 单个非法引脚（如 6-11 接 flash、34-39 无上拉）不能让整机启动崩溃
        try:
            pins.append(Pin(cfg.get("pin", 5), Pin.IN, Pin.PULL_UP))
        except Exception as e:
            print("button %d pin %s unusable (%s), disabled" % (i, cfg.get("pin"), e))
            pins.append(None)
            macros.append(None)
            continue
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
    for g in SETTINGS.get("gnd_pins", [19, 21, 25]):
        try:
            Pin(g, Pin.OUT, 0)
        except Exception as e:
            print("gnd pin %s unusable (%s), skipped" % (g, e))
    return pins, macros

try:
    button_pins, button_macros = _build_config()
except Exception as e:
    # 坏配置（非法引脚等）不能导致启动崩溃，否则 WEB CONFIG 永远进不去
    print("Config build failed (%s), falling back to defaults" % e)
    import settings as _settings
    SETTINGS = _settings._defaults_copy()
    button_pins, button_macros = _build_config()

trigger_indices = SETTINGS.get("trigger_pins", [0, 1])
if not isinstance(trigger_indices, list):
    trigger_indices = [0, 1]
# 只保留可用引脚：越界或引脚失效会让 min() 抛异常并拖垮扫描任务，
# 或使退出组合键永远无法满足
trigger_indices = [i for i in trigger_indices
                   if isinstance(i, int) and 0 <= i < len(button_pins)
                   and button_pins[i] is not None]
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
        except Exception as e:
            print("load secrets:", e)

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
            except Exception as e:
                print("save secrets:", e)
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
# 单次事件宏的 task 必须持有强引用，否则可能被 GC 中途回收（宏执行到一半停住）
transient_tasks = []

config_mode_trigger = False
trigger_press_start = [0] * max(len(trigger_indices), 1)


def _remove_transient(box):
    # 按身份移除：list.remove 用 == 比较，单元素列表可能与其它 box 误判相等
    for i in range(len(transient_tasks)):
        if transient_tasks[i] is box:
            transient_tasks.pop(i)
            return


async def _transient_runner(coro, box):
    """执行单次事件宏；结束时自行从列表摘除，不依赖 Task 内省 API。"""
    try:
        await coro
    finally:
        _remove_transient(box)


def _spawn_transient(coro):
    box = [None]
    transient_tasks.append(box)
    box[0] = asyncio.create_task(_transient_runner(coro, box))


def _cancel_transient():
    for box in transient_tasks:
        try:
            if box[0]:
                box[0].cancel()
        except:
            pass
    del transient_tasks[:]

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
    if not trigger_indices:
        # 无有效触发键：永不退出，避免 min([]) 抛异常
        while True:
            await asyncio.sleep_ms(500)
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
    try:
        success, ip = await connect_wifi_async(timeout=10)
    except Exception as e:
        print("WiFi connect error:", e)
        success, ip = False, None
    blink_task.cancel()
    led_pin.value(0)
    if not success:
        print("WiFi connection failed, returning to normal mode")
        config_mode_trigger = False
        return
    print("WiFi connected. IP: %s" % ip)
    print("Config mode: http://%s" % ip)
    # ESP32 的 BLE 与 WiFi 共用同一射频。配置模式要连续发几 KB 的 HTML，
    # 同时还有 BLE 广播/连接在抢占时隙，会直接把 TCP 打到重传超时
    # （表现：前 1KB 能发出，之后 [Errno 116] ETIMEDOUT）。
    # 配置模式的唯一出口是 machine.reset()，因此这里关掉 BLE 不需要恢复。
    try:
        ble_hid._ble.active(False)
        ble_hid.conn_handle = None
        print("BLE disabled for config mode")
    except Exception as e:
        print("BLE disable failed:", e)
    server_task = None
    err_blink = None
    try:
        server_task = start_web_server()
        await asyncio.sleep_ms(1200)
        if web_config.SERVER_OK:
            led_pin.value(1)
        else:
            # 端口没起来：快速闪烁提示，避免和"服务正常常亮"混淆
            print("Web server not listening - check web_host/web_port in settings.json")
            led_pin.value(0)
            err_blink = asyncio.create_task(_blink_led(80))
        await wait_for_exit_trigger()
        print("Exit trigger detected, saving and rebooting...")
        stop_web_server()
        await asyncio.sleep_ms(300)
        try:
            os.sync()
        except:
            pass
        machine.reset()
    except Exception as e:
        # 配置模式内部异常不能杀死扫描任务
        print("Config mode error:", e)
    finally:
        stop_web_server()
        if server_task:
            server_task.cancel()
        if err_blink:
            err_blink.cancel()
        config_mode_trigger = False

async def button_scanner():
    global config_mode_trigger
    while True:
        try:
            if config_mode_trigger:
                await asyncio.sleep_ms(100)
                continue
            await _scan_once()
        except Exception as e:
            # 单次异常绝不能让扫描任务静默死亡（表现为"按键全部失灵"）
            print("scanner error:", e)
            config_mode_trigger = False
        await asyncio.sleep_ms(5)

async def _scan_once():
    global trigger_press_start, config_mode_trigger
    if config_mode_trigger:
        return

    trigger_held = bool(trigger_indices)
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
            trigger_press_start = [now] * max(len(trigger_indices), 1)
        elapsed = time.ticks_diff(time.ticks_ms(), trigger_press_start[0])
        if elapsed >= long_press_ms:
            for i in range(len(button_pins)):
                auto_enabled[i] = False
                if active_tasks[i]:
                    active_tasks[i].cancel()
                    active_tasks[i] = None
            _cancel_transient()
            ble_hid.release_all()
            trigger_press_start = [0] * max(len(trigger_indices), 1)
            await config_mode()
            return
    else:
        trigger_press_start = [0] * max(len(trigger_indices), 1)

    for i, pin in enumerate(button_pins):
        if pin is None:
            continue
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
                    elif macro.key is not None:
                        ble_hid.send_raw(macro.modifiers, macro.key, True)
                    elif macro.button:
                        btn_val = 1 if macro.button == "left" else 2 if macro.button == "right" else 4
                        ble_hid.send_mouse(buttons=btn_val)
                    else:
                        _spawn_transient(run_events_async(macro, i, cancellable=False))
                else:
                    if macro.long_press == 1:
                        auto_enabled[i] = False
                        if macro.cancel == 1 and active_tasks[i]:
                            active_tasks[i].cancel()
                            active_tasks[i] = None
                        ble_hid.release_all()
                    elif macro.key is not None:
                        ble_hid.send_raw(macro.modifiers, macro.key, False)
                    elif macro.button:
                        ble_hid.send_mouse(buttons=0)

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