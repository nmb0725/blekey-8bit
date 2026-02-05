from machine import Pin, freq
import time
import asyncio
import bluetooth
import struct
from ble_hid import HID
from collections import namedtuple

# --- 1. 基础配置 ---
freq(160000000)
MY_HID_NAME = 'ble_keyboard_mouse' 
led_pin = Pin(2, Pin.OUT)
# 0x00: No modifier
# 0x01: CTRL, 10 Rctrl
#ctrl 左是04,需要附加, cap 是 39 ,tab 是 2B,SPACE是2C,ENTER是28 ,R是15,E是08,T是17,U是18+
#2 1F  ,4 21
# 自动按键状态
# 0x00: No modifier
# 0x01: CTRL (Left Control)
# 0x02: SHIFT (Left Shift)
# 0x03: CTRL + SHIFT
# 0x04: ALT (Left Alt)
#0x45 F12
# 创建按键宏实例
# 定义按键事件

# 1.25 蓝牙核心中断常量
_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GET_SECRET = 21
_IRQ_SET_SECRET = 20
_IRQ_ENCRYPTION_UPDATE = 28

# 定义数据结构
KeyEvent = namedtuple("KeyEvent", ["delay", "action", "modifier", "keycode"])
MouseEvent = namedtuple("MouseEvent", ["delay", "action", "button"])
MouseMoveEvent = namedtuple("MouseMoveEvent", ["delay", "action", "x", "y"])
WheelEvent = namedtuple("WheelEvent", ["delay", "action", "delta"])
DelayEvent = namedtuple("DelayEvent", ["delay", "action"])
KeyMacro = namedtuple("KeyMacro", ["events", "auto_interval", "long_press", "key", "modifiers", "button", "cancel"])

# --- 2. HID 类 (修复 1.25 自动重连与连接状态) ---
class MyHID(HID):
    def __init__(self, name):
        self.secrets = {}
        self.load_secrets()
        
        # 必须先执行父类初始化以注册服务
        super().__init__(name)
        
        try:
            # 1.25 核心安全配置：开启绑定与链路加密
            self._ble.config(bond=True, le_sec=True, io=0)
        except:
            pass
            
        # 核心：接管 IRQ 处理密钥交换
        self._ble.irq(self._custom_irq)
        # 显式启动适配 1.25 的广播包
        self.start_advertising(name)

    def load_secrets(self):
        """从本地文件加载配对密钥"""
        try:
            import ble_hid_key
            self.secrets = ble_hid_key.keys
        except:
            pass

    def start_advertising(self, name):
        """手动构建标准 HID 广播包，确保 Windows 能识别键盘身份"""
        payload = bytearray(b'\x02\x01\x06') # Flags
        payload += b'\x03\x19\xc1\x03'      # Appearance: Keyboard (0x03C1)
        payload += b'\x03\x03\x12\x18'      # Service: HID (0x1812)
        name_bytes = name.encode()
        payload += struct.pack('B', len(name_bytes) + 1) + b'\x09' + name_bytes
        self._ble.gap_advertise(100, adv_data=payload, connectable=True)

    def _custom_irq(self, event, data):
        """1.25 专用的中断拦截器"""
        # A. 自动重连密钥匹配
        if event == _IRQ_GET_SECRET:
            raw_key_info = bytes(data[-1])
            for k, v in self.secrets.items():
                if k[1] == raw_key_info or raw_key_info in k[1]:
                    return v
            return None
            
        # B. 初次配对密钥存储
        elif event == _IRQ_SET_SECRET:
            # 1.25 动态索引解包
            self.secrets[(data[0], bytes(data[1]))] = bytes(data[2])
            try:
                with open("ble_hid_key.py", "w") as f:
                    f.write("keys = " + repr(self.secrets))
            except: pass
            return True

        # C. 物理连接建立
        elif event == _IRQ_CENTRAL_CONNECT:
            self.conn_handle = data[0]
            
        # D. 加密完成通知 (1.25 真正能打字的点)
        elif event == _IRQ_ENCRYPTION_UPDATE:
            if data[1]: # encrypted == True
                self.conn_handle = data[0]
                
        # E. 断开重连
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self.conn_handle = None
            self.start_advertising(MY_HID_NAME)

        # ！！关键：转发所有其余事件（如描述符请求）给内置 HID 类 ！！
        return self._irq(event, data)

    def is_connected(self):
        return self.conn_handle is not None

    def send_raw(self, mod, key, pressed=True):
        """核心发送：使用 8 字节 HID 键盘报文"""
        if self.is_connected():
            buf = bytearray(8)
            if pressed:
                buf[0] = mod
                buf[2] = key
            
            try:
                # 使用内置的 k_rep 句柄发送通知
                self._ble.gatts_notify(self.conn_handle, self.k_rep, buf)
                # 针对修饰键释放的增强同步
                if not pressed and mod != 0:
                    self._ble.gatts_notify(self.conn_handle, self.k_rep, b'\x00\x00\x00\x00\x00\x00\x00\x00')
            except:
                pass

    def send_mouse(self, buttons=0, x=0, y=0, wheel=0):
        """发送 4 字节鼠标报文"""
        if self.is_connected():
            # 限制坐标在 -127 到 127 之间
            x = max(min(x, 127), -127)
            y = max(min(y, 127), -127)
            wheel = max(min(wheel, 127), -127)
            buf = struct.pack('bbbb', buttons, x, y, wheel)
            try:
                # 使用内置的 m_rep 句柄发送通知 (Mouse Report)
                self._ble.gatts_notify(self.conn_handle, self.m_rep, buf)
            except:
                pass

    def release_all(self):
        """双保险释放：确保键盘和鼠标状态都彻底清零"""
        if self.is_connected():
            try:
                # 发送键盘全释放报文
                self._ble.gatts_notify(self.conn_handle, self.k_rep, b'\x00\x00\x00\x00\x00\x00\x00\x00')
                # 发送鼠标全释放报文
                self.send_mouse(0, 0, 0, 0)
                # 额外同步一次，防止丢包
                time.sleep_ms(5)
                self._ble.gatts_notify(self.conn_handle, self.k_rep, b'\x00\x00\x00\x00\x00\x00\x00\x00')
            except:
                pass

# 实例化
ble_hid = MyHID(MY_HID_NAME)

# --- 3. 宏定义 (保持原样) ---

# 1. 自动连点左键 (每100ms点击一次，按住开关触发)
LEFT_CLICK_SPAM = KeyMacro(events=[
    MouseEvent(delay=0, action="press", button="left"),
    MouseEvent(delay=50, action="release", button="left")
], auto_interval=50, long_press=1, key=None, modifiers=0x00, button=None, cancel=1)

# 2. 鼠标左右反复横移 (验证移动功能)
MOUSE_WIGGLE = KeyMacro(events=[
    MouseMoveEvent(delay=0, action="move", x=50, y=0),
    DelayEvent(delay=200, action="delay"),
    MouseMoveEvent(delay=0, action="move", x=-50, y=0)
], auto_interval=200, long_press=1, key=None, modifiers=0x00, button=None, cancel=0)

# 3. 复杂组合键示例：Ctrl + Alt + A (截图常用)
# 逻辑：按住 Ctrl -> 按住 Alt -> 按下 A -> 释放 A -> 释放 Alt -> 释放 Ctrl
SCREENSHOT_COMBO = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x01, keycode=0x00), # 按住 Ctrl
    KeyEvent(delay=10, action="press", modifier=0x05, keycode=0x00), # 叠加 Alt (0x01|0x04)
    KeyEvent(delay=10, action="press", modifier=0x05, keycode=0x04), # 按下 A
    KeyEvent(delay=50, action="release", modifier=0x05, keycode=0x04), # 释放 A
    KeyEvent(delay=10, action="release", modifier=0x01, keycode=0x00), # 释放 Alt
    KeyEvent(delay=10, action="release", modifier=0x00, keycode=0x00)  # 全释放
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
        DelayEvent(delay=250, action="delay"),
        KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x17), 
        KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x17)
    ],
    auto_interval=150, long_press=1, key=None, modifiers=0, button=None, cancel=0
)

UP    = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x52, modifiers=0, button=None, cancel=1)
DOWN  = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x51, modifiers=0, button=None, cancel=1)
LEFT  = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x50, modifiers=0, button=None, cancel=1)
RIGHT = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x4F, modifiers=0, button=None, cancel=1)
KEY_6 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x23, modifiers=0, button=None, cancel=1)


CTRL_1 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x1E, modifiers=0x01,button=None, cancel=1)
CTRL_2 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x1F, modifiers=0x01,button=None, cancel=1)
CTRL_3 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x20, modifiers=0x01,button=None, cancel=1)
CTRL_4 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x21, modifiers=0x01,button=None, cancel=1)

CTRL = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x00, modifiers=0x01,button=None, cancel=1) # CTRL 映射
F11 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x44, modifiers=0x00,button=None, cancel=1) # f11 映射
F12 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x45, modifiers=0x00,button=None, cancel=1) # f12 映射
TAB = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x2B, modifiers=0x00,button=None, cancel=1) # tab 映射
CAPS = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x39, modifiers=0x00,button=None, cancel=1) # CAPS 映射

# 定义按键宏
#auto_interval 是间隔时间自动执行, LONG_PRESS是做长按, 2个都加是键按住时触发
LONG_PRESS_R = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x15),
    DelayEvent(delay=1000, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x00, keycode=0x15)
], auto_interval=0, long_press=1, key=None, modifiers=0x00,button=None, cancel=1)

#开关型 自动R
R_LONG = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x15),
    KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x15)
], auto_interval=150, long_press=1, key=None, modifiers=0x00,button=None, cancel=1)

#开关型 自动T
T_LONG = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x17),
    KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x17)
], auto_interval=300, long_press=1, key=None, modifiers=0x00,button=None, cancel=1)

AUTO_2 = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x1F),
    KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x1F)
], auto_interval=50, long_press=1, key=None, modifiers=0x00,button=None, cancel=1) 

AUTO_4 = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x21),
    KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x21)
], auto_interval=50, long_press=1, key=None, modifiers=0x00,button=None, cancel=1) 

E = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x08),  # 按下 E 键，立即执行
    DelayEvent(delay=0, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x00, keycode=0x08)  # 释放 E 键，立即执行
], auto_interval=0, long_press=1, key=None, modifiers=0x00,button=None, cancel=1) 

CTRL_SHIFT_T = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x03, keycode=0x17),
    DelayEvent(delay=0, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x03, keycode=0x17)
], auto_interval=0, long_press=0, key=None, modifiers=0x00,button=None, cancel=1) 

ALT_R = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x04, keycode=0x15),
    DelayEvent(delay=0, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x04, keycode=0x15)
], auto_interval=0, long_press=0, key=None, modifiers=0x00,button=None, cancel=1) 

LEFT_CLICK = KeyMacro(events=[
    MouseEvent(delay=0, action="press", button="left"),
    MouseEvent(delay=50, action="release", button="left")
], auto_interval=0, long_press=0, key=None, modifiers=0x00,button=None, cancel=1) 

MIDDLE_CLICK = KeyMacro(events=[], auto_interval=0, long_press=0, key=None, modifiers=0x00,button="middle", cancel=1)

WHEEL_UP = KeyMacro(events=[
    WheelEvent(delay=0, action="scroll", delta=120)
], auto_interval=0, long_press=0, key=None, modifiers=0x00,button=None, cancel=1) 

LEFT_CLICK_AUTO = KeyMacro(events=[
    MouseEvent(delay=0, action="press", button="left"),
    MouseEvent(delay=50, action="release", button="left")
], auto_interval=100, long_press=0, key=None, modifiers=0x00,button=None, cancel=1) 

MOUSE_MOVE_RIGHT = KeyMacro(events=[
    MouseMoveEvent(delay=0, action="move", x=10, y=0)
], auto_interval=0, long_press=0, key=None, modifiers=0x00,button=None, cancel=1) 

CTRL = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x00, modifiers=0x01,button=None, cancel=1) # CTRL 映射

# 按键与宏绑定列表
button_macros = [F12_AUTO, F11_AUTO, T_AUTO, R_AUTO, KEY_6, LONG_SHIFT_T, UP, LEFT, RIGHT, DOWN]

# 定义按键输入引脚
button_pins = [
    Pin(5, Pin.IN, Pin.PULL_UP),
    Pin(18, Pin.IN, Pin.PULL_UP),
    Pin(26, Pin.IN, Pin.PULL_UP),#left
    Pin(27, Pin.IN, Pin.PULL_UP),#down
    Pin(12, Pin.IN, Pin.PULL_UP),  #up
    Pin(13, Pin.IN, Pin.PULL_UP),#right
    Pin(23, Pin.IN, Pin.PULL_UP),
    Pin(22, Pin.IN, Pin.PULL_UP),
    Pin(32, Pin.IN, Pin.PULL_UP),
    Pin(33, Pin.IN, Pin.PULL_UP)
]
    
#SET GND        
Pin(19, Pin.OUT, 0)
Pin(21, Pin.OUT, 0)
Pin(25, Pin.OUT, 0)


# --- 4. 任务与状态管理 (保持原样) ---
auto_enabled = [False] * len(button_pins)
active_tasks = [None] * len(button_pins)
prev_state = [1] * len(button_pins)

async def run_events_async(macro, idx):
    for event in macro.events:
        if macro.cancel == 1 and not auto_enabled[idx]: break
        
        # 处理按键事件
        if isinstance(event, KeyEvent):
            ble_hid.send_raw(event.modifier, event.keycode, (event.action == "press"))
            await asyncio.sleep_ms(max(event.delay, 10))
            
        # 处理鼠标点击事件
        elif isinstance(event, MouseEvent):
            btn_val = 1 if event.button == "left" else 2 if event.button == "right" else 4
            if event.action == "press":
                ble_hid.send_mouse(buttons=btn_val)
            else:
                ble_hid.send_mouse(buttons=0)
            await asyncio.sleep_ms(max(event.delay, 10))
            
        # 处理鼠标移动事件
        elif isinstance(event, MouseMoveEvent):
            ble_hid.send_mouse(x=event.x, y=event.y)
            await asyncio.sleep_ms(max(event.delay, 10))
            
        # 处理滚轮事件
        elif isinstance(event, WheelEvent):
            ble_hid.send_mouse(wheel=event.delta)
            await asyncio.sleep_ms(max(event.delay, 10))
            
        elif isinstance(event, DelayEvent):
            await asyncio.sleep_ms(event.delay)

async def auto_loop_task(idx):
    macro = button_macros[idx]
    try:
        while auto_enabled[idx]:
            await run_events_async(macro, idx)
            if macro.auto_interval > 0: await asyncio.sleep_ms(macro.auto_interval)
            else: break
    finally:
        ble_hid.release_all()
        active_tasks[idx] = None

# --- 5. 核心扫描器 (保持原样) ---
async def button_scanner():
    while True:
        for i, pin in enumerate(button_pins):
            val = pin.value()
            if val != prev_state[i]:
                await asyncio.sleep_ms(15)
                if pin.value() == val:
                    prev_state[i] = val
                    macro = button_macros[i]
                    if val == 0: # 按下
                        if macro.long_press == 1:
                            auto_enabled[i] = True
                            if active_tasks[i]: active_tasks[i].cancel()
                            active_tasks[i] = asyncio.create_task(auto_loop_task(i))
                        elif macro.auto_interval > 0:
                            auto_enabled[i] = not auto_enabled[i]
                            if auto_enabled[i]:
                                if active_tasks[i]: active_tasks[i].cancel()
                                active_tasks[i] = asyncio.create_task(auto_loop_task(i))
                            else:
                                if active_tasks[i]: active_tasks[i].cancel()
                        elif macro.key:
                            ble_hid.send_raw(macro.modifiers, macro.key, True)
                        elif macro.button:
                            btn_val = 1 if macro.button == "left" else 2 if macro.button == "right" else 4
                            ble_hid.send_mouse(buttons=btn_val)
                        else:
                            asyncio.create_task(run_events_async(macro, i))
                    else: # 抬起
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

# --- 6. 主循环 (加入内存管理与心跳显示) ---
async def main():
    print("BLE System Started: %s" % MY_HID_NAME)
    asyncio.create_task(button_scanner())
    
    heartbeat_count = 0
    while True:
        if ble_hid.is_connected():
            # 心跳逻辑：大部分时间常亮，每 10 次循环(5秒)闪烁一下
            heartbeat_count += 1
            if heartbeat_count >= 10:
                led_pin.value(0) # 眨眼
                await asyncio.sleep_ms(50)
                led_pin.value(1)
                heartbeat_count = 0
            else:
                led_pin.value(1) # 保持常亮
        else:
            led_pin.value(not led_pin.value()) # 广播闪烁
            heartbeat_count = 0
            
        # 稳健性核心：主动回收垃圾内存
        gc.collect() 
        
        await asyncio.sleep_ms(500)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass

