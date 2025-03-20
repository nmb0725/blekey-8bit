import time
import esp32,machine
from machine import Pin, Timer
from ble_hid import HID
from collections import namedtuple
class MyHID(HID):  # 继承现有的 HID 类
    def __init__(self, name):
        super().__init__(name)
        self.pressed_special_keys = set()  # 用于存储当前按下的特殊按键
        self.pressed_general_keys = set()  # 用于存储当前按下的普通按键
        self.saved_special_keys = set()  # 用于保存之前的特殊按键状态

    def keyboard_notify(self, special=0, general=0, pressed=True):
        '''键盘 特殊按键 + 常规组合按键*6'''
        if self.is_connected():
            _keys = bytearray(6)
            
            # 更新按键状态
            if pressed:
                if general:
                    if isinstance(general, int):
                        self.pressed_general_keys.add(general)
                    elif isinstance(general, (list, tuple)):
                        self.pressed_general_keys.update(general)
                if special:
                    self.pressed_special_keys.add(special)
            else:
                if general:
                    if isinstance(general, int):
                        self.pressed_general_keys.discard(general)
                    elif isinstance(general, (list, tuple)):
                        for key in general:
                            self.pressed_general_keys.discard(key)
                if special:
                    self.pressed_special_keys.discard(special)

            # 填充按键数据
            key_list = list(self.pressed_general_keys)
            for i in range(min(6, len(key_list))):
                _keys[i] = key_list[i]

            #  更新 special 的状态
            _special = 0
            for key in self.pressed_special_keys:
                _special |= key
            # 发送按键数据
            #print(_special)
            self._ble.gatts_notify(self.conn_handle, self.k_rep, bytes([_special & 0xFF, 0]) + _keys)


    def mouse_notify(self, keys=b'\x00', move=(0, 0), wheel=0):
        '''鼠标 按键*8 + 位移 + 滚轮'''
        if self.is_connected():
            _mouse_data = bytearray(4)
            _mouse_data[0] = keys[0] if len(keys) > 0 else 0x00  # 使用第一个字节表示按键状态
            _mouse_data[1] = move[0] & 0xFF
            _mouse_data[2] = move[1] & 0xFF
            _mouse_data[3] = wheel & 0xFF
            self._ble.gatts_notify(self.conn_handle, self.m_rep, bytes(_mouse_data))

    def key_press(self, special=0, general=0):
        '''按下按键'''
        self.saved_special_keys = self.pressed_special_keys.copy()
        self.keyboard_notify(special, general, pressed=True)

    def key_release(self, special=0, general=0):
        '''释放按键'''
        self.keyboard_notify(special, general, pressed=False)
        self.pressed_special_keys = self.saved_special_keys.copy()
    def mouse_press(self, button=b'\x01'):
        '''按下鼠标按键'''
        self.mouse_notify(keys=button)

    def mouse_release(self, button=b'\x00'):
        '''释放鼠标按键'''
        self.mouse_notify(keys=button)
    def mouse_click(self, button=b'\x01'):
        '''鼠标单击'''
        self.mouse_notify(keys=button)  # 按下鼠标按键
        self.mouse_notify(keys=b'\x00')  # 释放鼠标按键
    def release_all_keys(self):
        '''释放所有键盘按键'''
        # self.keyboard_notify(special=0, general=0, pressed=False)  #  这个方法可能不再适用
        self.pressed_special_keys.clear()
        self.pressed_general_keys.clear()
        self.keyboard_notify(special=0, general=0, pressed=False)
        
# 定义深度睡眠时间 (单位：秒)
DEEP_SLEEP_TIME = 900
POWER_PIN = 26

# 定义鼠标按键常量
MOUSE_LEFT = 0x01  # 左键
MOUSE_RIGHT = 0x02  # 右键
MOUSE_MIDDLE = 0x04  # 中键
MOUSE_BUTTON4 = 0x08  # 鼠标按键 4
MOUSE_BUTTON5 = 0x10  # 鼠标按键 5

ble_hid = MyHID('ble_keyboard_mouse')  # 使用 MyHID 类

# 定义按键的 keycode (需要根据你的库来确定)
KEYCODE_CTRL = 0x01
KEYCODE_ALT = 0x02
KEYCODE_DELETE = 0x2A

# 定义按键输入引脚
button_pins = [
    Pin(25, Pin.IN, Pin.PULL_UP),
    Pin(26, Pin.IN, Pin.PULL_UP),
    Pin(27, Pin.IN, Pin.PULL_UP),
    Pin(14, Pin.IN, Pin.PULL_UP)
]


# 定义 LED 输出引脚
led_pin = Pin(2, Pin.OUT)

# 定义按键事件
KeyEvent = namedtuple("KeyEvent", ["delay", "action", "modifier", "keycode"])

# 定义鼠标事件
MouseEvent = namedtuple("MouseEvent", ["delay", "action", "button"])

# 定义鼠标移动事件
MouseMoveEvent = namedtuple("MouseMoveEvent", ["delay", "action", "x", "y"])

# 定义滚轮事件
WheelEvent = namedtuple("WheelEvent", ["delay", "action", "delta"])

# 定义延时事件
DelayEvent = namedtuple("DelayEvent", ["delay", "action"])

# 定义按键宏
KeyMacro = namedtuple("KeyMacro", ["events", "auto_interval"])
# 0x00: No modifier
# 0x01: CTRL, 10 Rctrl
#ctrl 左是04,需要附加, cap 是 39 ,tab 是 2B,SPACE是2C,ENTER是28 ,R是15,E是08,T是17,U是18
# 自动按键状态
# 0x00: No modifier
# 0x01: CTRL (Left Control)
# 0x02: SHIFT (Left Shift)
# 0x03: CTRL + SHIFT
# 0x04: ALT (Left Alt)
# 创建按键宏实例
LONG_PRESS_R = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x15),    # 按下 R 键，立即执行
    DelayEvent(delay=1000, action="delay"), # 延时 1 秒
    KeyEvent(delay=0, action="release", modifier=0x00, keycode=0x15)   # 释放 R 键，立即执行
], auto_interval=0)  # 不启用自动按键

CTRL_R = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x10, keycode=0x00),  # 按下 CTRL + R 键，立即执行
], auto_interval=0)  # 不启用自动按键

R_AUTO = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x15),  # 按下 R 键，立即执行
    KeyEvent(delay=0, action="release", modifier=0x00, keycode=0x15)  # 释放 R 键，立即执行
], auto_interval=150)  # 启用自动按键，间隔 500 毫秒

E = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x08),  # 按下 E 键，立即执行
    DelayEvent(delay=0, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x00, keycode=0x08)  # 释放 E 键，立即执行
], auto_interval=0)  # 不启用自动按键

CTRL_SHIFT_T = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x03, keycode=0x17),  # 按下 CTRL + SHIFT + T 键，立即执行
    DelayEvent(delay=0, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x03, keycode=0x17)  # 释放 CTRL + SHIFT + T 键，立即执行
], auto_interval=0)  # 不启用自动按键

ALT_R = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x04, keycode=0x15),  # 按下 ALT + R 键，立即执行
    DelayEvent(delay=0, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x04, keycode=0x15)  # 释放 ALT + R 键，立即执行
], auto_interval=0)  # 不启用自动按键

# 鼠标左键单击
LEFT_CLICK = KeyMacro(events=[
    MouseEvent(delay=0, action="press", button="left"),   # 按下鼠标左键
    MouseEvent(delay=50, action="release", button="left")  # 释放鼠标左键
], auto_interval=0)

# 滚轮向上滚动
WHEEL_UP = KeyMacro(events=[
    WheelEvent(delay=0, action="scroll", delta=120)  # 滚轮向上滚动
], auto_interval=0)

# 自动鼠标左键单击
LEFT_CLICK_AUTO = KeyMacro(events=[
    MouseEvent(delay=0, action="press", button="left"),   # 按下鼠标左键
    MouseEvent(delay=50, action="release", button="left")  # 释放鼠标左键
], auto_interval=100)  # 启用自动点击，间隔 100 毫秒

# 鼠标向右移动
MOUSE_MOVE_RIGHT = KeyMacro(events=[
    MouseMoveEvent(delay=0, action="move", x=10, y=0)  # 鼠标向右移动 10 个像素
], auto_interval=0)

# 定义按键对应的宏
button_macros = [E,R_AUTO,  CTRL_R, CTRL_SHIFT_T, LEFT_CLICK,LEFT_CLICK_AUTO, WHEEL_UP, MOUSE_MOVE_RIGHT]

# 自动按键状态
auto_press_enabled = [False] * len(button_pins)

# 记录上次按键的时间
last_press_time = [0] * len(button_pins)

# 长按状态
long_press_enabled = [False] * len(button_pins)

# 记录按键状态
button_states = [1] * len(button_pins)  # 初始状态为未按下 (1)

# 消抖时间 (毫秒)
debounce_delay = 50

# 定时器列表
timers = {}
sleeptimer = Timer(-1)

# 定义定时器中断处理函数，进入深度睡眠模式
def go_to_deep_sleep(timer):
    print("进入深度睡眠模式...")
    time.sleep(1)

    # 配置 ESP32 在 GPIO 引脚上检测到电平变化时唤醒
    esp32.wake_on_ext0(pin=POWER_PIN, level=esp32.WAKEUP_ALL_LOW)
    #esp32.wake_on_ext1(pins=(Pin(POWER_PIN1, Pin.IN, Pin.PULL_UP), Pin(POWER_PIN2, Pin.IN, Pin.PULL_UP)), level=esp32.WAKEUP_ALL_LOW)

    # 进入深度睡眠模式
    machine.deepsleep()  # 使用 machine.deepsleep()
    
def handle_button_press(button_index):
    global button_macros, timers,sleeptimer, ble_hid, auto_press_enabled, last_press_time, long_press_enabled
        # 重置定时器
    sleeptimer.deinit()
    sleeptimer.init(mode=Timer.ONE_SHOT, period=DEEP_SLEEP_TIME * 1000, callback=go_to_deep_sleep)
    
    macro = button_macros[button_index]
    
    # 如果启用了自动按键功能
    if macro.auto_interval > 0:
        # 切换自动按键状态
        auto_press_enabled[button_index] = not auto_press_enabled[button_index]
        print("Auto press key {}: {}".format(button_index + 1, "Enabled" if auto_press_enabled[button_index] else "Disabled"))
        
        if auto_press_enabled[button_index]:
            # 启动定时器
            timer_id = (button_index, "auto")  # 创建唯一的定时器 ID
            timers[timer_id] = Timer(-1)  # 创建一个新的定时器
            timers[timer_id].init(period=macro.auto_interval, mode=Timer.PERIODIC, callback=lambda t: auto_key_press(button_index))
        else:
            # 停止定时器
            timer_id = (button_index, "auto")
            if timer_id in timers:
                timers[timer_id].deinit()
                del timers[timer_id]
        
        return  # 停止当前事件的处理
    
    # 如果没有启用自动按键功能，则执行长按操作
    # 切换长按状态
    long_press_enabled[button_index] = not long_press_enabled[button_index]
    print("Long press key {}: {}".format(button_index + 1, "Enabled" if long_press_enabled[button_index] else "Disabled"))
    
    if long_press_enabled[button_index]:
        # 启动长按
        # 遍历按键事件
        for i, event in enumerate(macro.events):
            if isinstance(event, KeyEvent):
                delay = event.delay
                action = event.action
                modifier = event.modifier
                keycode = event.keycode
                
                # 根据不同的 action 执行不同的操作
                if action == "press":
                    ble_hid.key_press(special=modifier,general=keycode)
                elif action == "release":
                    ble_hid.key_release(special=modifier,general=keycode)
            elif isinstance(event, MouseEvent):
                delay = event.delay
                action = event.action
                button = event.button
                
                # 根据不同的 action 执行不同的操作
                if action == "press":
                    #ble_hid.mouse_notify(get_mouse_button_code(button), (0, 0), 0, False)  # 按下鼠标按键
                    ble_hid.mouse_press(get_mouse_button_code(button))
                elif action == "release":
                    ble_hid.mouse_release(get_mouse_button_code(button))
                    #ble_hid.mouse_notify(get_mouse_button_code(button), (0, 0), 0, True)  # 释放鼠标按键
            elif isinstance(event, MouseMoveEvent):
                delay = event.delay
                action = event.action
                x = event.x
                y = event.y
                
                # 执行鼠标移动操作
                ble_hid.mouse_notify(0x00, (x, y), 0, True)  # 移动鼠标
            elif isinstance(event, WheelEvent):
                delay = event.delay
                action = event.action
                delta = event.delta
                
                # 执行滚轮操作
                ble_hid.mouse_notify(0x00, (0, 0), delta, True)  # 滚动滚轮
            elif isinstance(event, DelayEvent):
                delay = event.delay
                action = event.action
                
                # 延迟执行后续事件
                timer_id = (button_index, i)  # 创建唯一的定时器 ID
                timers[timer_id] = Timer(-1)  # 创建一个新的定时器
                timers[timer_id].init(period=delay, mode=Timer.ONE_SHOT, callback=lambda t: delayed_action(button_index, i + 1, timer_id))
                return  # 停止当前事件的处理

            # 如果没有延迟，则继续处理下一个事件
            if delay == 0:
                continue
            else:
                break  # 停止当前事件的处理
    else:
        # 停止长按
        # 释放所有按键
        ble_hid.release_all_keys()
        #ble_hid.keyboard_notify(0x00, 0x00, True)  # 释放所有按键
        #ble_hid.mouse_notify(0x00, (0, 0), 0, True)  # 释放所有鼠标按键
        ble_hid.mouse_notify(keys=b'\x00')
        
        # 停止所有定时器
        for timer_id in list(timers.keys()):
            if isinstance(timer_id, tuple) and timer_id[0] == button_index and timer_id[1] != "auto":
                timers[timer_id].deinit()
                del timers[timer_id]

def delayed_action(button_index, event_index, timer_id):
    global timers, ble_hid, button_macros
    
    macro = button_macros[button_index]
    
    # 检查事件索引是否越界
    if event_index >= len(macro.events):
        return
    
    event = macro.events[event_index]
    if isinstance(event, KeyEvent):
        delay = event.delay
        action = event.action
        modifier = event.modifier
        keycode = event.keycode
        
        # 根据不同的 action 执行不同的操作
        if action == "press":
            #ble_hid.keyboard_notify(modifier, keycode, False)  # 按下按键
            ble_hid.key_press(special=modifier,general=keycode)
        elif action == "release":
            #ble_hid.keyboard_notify(0x00, 0x00, True)  # 释放所有按键
            ble_hid.key_release(special=modifier,general=keycode)

    elif isinstance(event, MouseEvent):
        delay = event.delay
        action = event.action
        button = event.button
        
        # 根据不同的 action 执行不同的操作
        if action == "press":
            #ble_hid.mouse_notify(get_mouse_button_code(button), (0, 0), 0, False)  # 按下鼠标按键
            ble_hid.mouse_press(get_mouse_button_code(button))
        elif action == "release":
            ble_hid.mouse_release(get_mouse_button_code(button))
            #ble_hid.mouse_notify(get_mouse_button_code(button), (0, 0), 0, True)  # 释放鼠标按键
    elif isinstance(event, MouseMoveEvent):
        delay = event.delay
        action = event.action
        x = event.x
        y = event.y
        
        # 执行鼠标移动操作
        ble_hid.mouse_notify(0x00, (x, y), 0, True)  # 移动鼠标
    elif isinstance(event, WheelEvent):
        delay = event.delay
        action = event.action
        delta = event.delta
        
        # 执行滚轮操作
        ble_hid.mouse_notify(0x00, (0, 0), delta, True)  # 滚动滚轮
    elif isinstance(event, DelayEvent):
        delay = event.delay
        action = event.action
    
    # 停止并删除定时器
    timers[timer_id].deinit()
    del timers[timer_id]

def auto_key_press(button_index):
    global button_macros, ble_hid, last_press_time
    macro = button_macros[button_index]
    
    # 遍历按键事件
    for i, event in enumerate(macro.events):
        if isinstance(event, KeyEvent):
            delay = event.delay
            action = event.action
            modifier = event.modifier
            keycode = event.keycode
            
            # 根据不同的 action 执行不同的操作
            if action == "press":
                #ble_hid.keyboard_notify(modifier, keycode, False)  # 按下按键
                ble_hid.key_press(special=modifier,general=keycode)
            elif action == "release":
                ble_hid.key_release(special=modifier,general=keycode)
                #ble_hid.keyboard_notify(0x00, 0x00, True)  # 释放所有按键
        elif isinstance(event, MouseEvent):
            delay = event.delay
            action = event.action
            button = event.button
            
            # 根据不同的 action 执行不同的操作
            if action == "press":
                #ble_hid.mouse_notify(get_mouse_button_code(button), (0, 0), 0, False)  # 按下鼠标按键
                ble_hid.mouse_press(get_mouse_button_code(button))
            elif action == "release":
                ble_hid.mouse_release(get_mouse_button_code(button))
                #ble_hid.mouse_notify(get_mouse_button_code(button), (0, 0), 0, True)  # 释放鼠标按键
        elif isinstance(event, MouseMoveEvent):
            delay = event.delay
            action = event.action
            x = event.x
            y = event.y
            
            # 执行鼠标移动操作
            ble_hid.mouse_notify(0x00, (x, y), 0, True)  # 移动鼠标
        elif isinstance(event, WheelEvent):
            delay = event.delay
            action = event.action
            delta = event.delta
            
            # 执行滚轮操作
            ble_hid.mouse_notify(0x00, (0, 0), delta, True)  # 滚动滚轮
        elif isinstance(event, DelayEvent):
            continue  # 忽略 delay 事件

def get_mouse_button_code(button):
    if button == "left":
        return 0x01
    elif button == "right":
        return 0x02
    elif button == "middle":
        return 0x04
    elif button == "x1":
        return 0x08
    elif button == "x2":
        return 0x10
    else:
        return 0x00  # 默认返回 0

def button_callback(pin):
    global auto_press_enabled, button_states, timers, button_macros
    button_index = button_pins.index(pin)
    current_state = pin.value()

    if current_state == 0 and button_states[button_index] == 1:
        button_states[button_index] = 0
        
        handle_button_press(button_index)  # 处理按键事件
        
    elif current_state == 1 and button_states[button_index] == 0:
        button_states[button_index] = 1

# 初始化时 LED 闪烁
led_state = 0
def led_blink():
    global led_state
    led_state = 1 - led_state
    led_pin.value(led_state)

blink_timer = Timer(-1)
blink_timer.init(period=500, mode=Timer.PERIODIC, callback=lambda t: led_blink())

while True:
    if ble_hid.is_connected():
        # 连接成功，停止闪烁，LED 长亮
        blink_timer.deinit()
        led_pin.value(1)
        break
    time.sleep(0.1)

print("Loaded")

# 设置中断
for pin in button_pins:
    pin.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=button_callback)

# 启动定时器
sleeptimer.init(mode=Timer.ONE_SHOT, period=DEEP_SLEEP_TIME * 1000, callback=go_to_deep_sleep)

while True:
    time.sleep(0.01)

