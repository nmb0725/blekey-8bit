from machine import Pin, Timer, deepsleep, freq
import time
import esp32
from ble_hid import HID
from collections import namedtuple
import network

wlan = network.WLAN(network.STA_IF)
wlan.active(False)
# 降低 CPU 频率到 80MHz
freq(80000000)

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
KeyEvent = namedtuple("KeyEvent", ["delay", "action", "modifier", "keycode"])
MouseEvent = namedtuple("MouseEvent", ["delay", "action", "button"])
MouseMoveEvent = namedtuple("MouseMoveEvent", ["delay", "action", "x", "y"])
WheelEvent = namedtuple("WheelEvent", ["delay", "action", "delta"])
DelayEvent = namedtuple("DelayEvent", ["delay", "action"])
KeyMacro = namedtuple("KeyMacro", ["events", "auto_interval", "long_press", "key", "modifiers", "button"])


# 定义按键宏
#auto_interval 是间隔时间自动执行, LONG_PRESS是做长按, 2个都加是键按住时触发
LONG_PRESS_R = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x15),
    DelayEvent(delay=1000, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x00, keycode=0x15)
], auto_interval=0, long_press=1, key=None, modifiers=0x00,button=None)

#开关型 自动R
R_AUTO = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x15),
    KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x15)
], auto_interval=150, long_press=0, key=None, modifiers=0x00,button=None)

F12_AUTO = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x45),
    KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x45)
], auto_interval=50, long_press=1, key=None, modifiers=0x00,button=None)

F11_AUTO = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x44),
    KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x44)
], auto_interval=50, long_press=1, key=None, modifiers=0x00,button=None)

CTRL_1 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x1E, modifiers=0x01,button=None)
CTRL_2 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x1F, modifiers=0x01,button=None)
CTRL_3 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x20, modifiers=0x01,button=None)
CTRL_4 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x21, modifiers=0x01,button=None)

AUTO_2 = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x1F),
    KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x1F)
], auto_interval=50, long_press=1, key=None, modifiers=0x00,button=None)

AUTO_4 = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x21),
    KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x21)
], auto_interval=50, long_press=1, key=None, modifiers=0x00,button=None)


E = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x08),  # 按下 E 键，立即执行
    DelayEvent(delay=0, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x00, keycode=0x08)  # 释放 E 键，立即执行
], auto_interval=0, long_press=1, key=None, modifiers=0x00,button=None)

CTRL_SHIFT_T = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x03, keycode=0x17),
    DelayEvent(delay=0, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x03, keycode=0x17)
], auto_interval=0, long_press=0, key=None, modifiers=0x00,button=None)

ALT_R = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x04, keycode=0x15),
    DelayEvent(delay=0, action="delay"),
    KeyEvent(delay=0, action="release", modifier=0x04, keycode=0x15)
], auto_interval=0, long_press=0, key=None, modifiers=0x00,button=None)

LEFT_CLICK = KeyMacro(events=[
    MouseEvent(delay=0, action="press", button="left"),
    MouseEvent(delay=50, action="release", button="left")
], auto_interval=0, long_press=0, key=None, modifiers=0x00,button=None)

MIDDLE_CLICK = KeyMacro(events=[], auto_interval=0, long_press=0, key=None, modifiers=0x00,button="middle")

WHEEL_UP = KeyMacro(events=[
    WheelEvent(delay=0, action="scroll", delta=120)
], auto_interval=0, long_press=0, key=None, modifiers=0x00,button=None)

LEFT_CLICK_AUTO = KeyMacro(events=[
    MouseEvent(delay=0, action="press", button="left"),
    MouseEvent(delay=50, action="release", button="left")
], auto_interval=100, long_press=0, key=None, modifiers=0x00,button=None)

MOUSE_MOVE_RIGHT = KeyMacro(events=[
    MouseMoveEvent(delay=0, action="move", x=10, y=0)
], auto_interval=0, long_press=0, key=None, modifiers=0x00,button=None)

CTRL = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x00, modifiers=0x01,button=None) # CTRL 映射
F11 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x44, modifiers=0x00,button=None) # f11 映射
F12 = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x45, modifiers=0x00,button=None) # f12 映射
TAB = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x2B, modifiers=0x00,button=None) # tab 映射
CAPS = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x39, modifiers=0x00,button=None) # CAPS 映射
LEFT = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x50, modifiers=0x00,button=None) # tab 映射
RIGHT = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x4F, modifiers=0x00,button=None) # CAPS 映射
UP = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x52, modifiers=0x00,button=None) # tab 映射
DOWN = KeyMacro(events=[], auto_interval=0, long_press=0, key=0x51, modifiers=0x00,button=None) # CAPS 映射
# 定义按键对应的宏
#button_macros = [F12, MIDDLE_CLICK,CAPS, CTRL_R, CTRL_SHIFT_T, LEFT_CLICK, LEFT_CLICK_AUTO, WHEEL_UP, MOUSE_MOVE_RIGHT]
button_macros = [F12_AUTO,F11_AUTO,CTRL_1,CTRL_4,CTRL_2,CTRL_3]

# 定义按键输入引脚
button_pins = [
    Pin(5, Pin.IN, Pin.PULL_UP),
    Pin(18, Pin.IN, Pin.PULL_UP),
    Pin(25, Pin.IN, Pin.PULL_UP),#left
    Pin(26, Pin.IN, Pin.PULL_UP),#down
    Pin(12, Pin.IN, Pin.PULL_UP),  #up
    Pin(13, Pin.IN, Pin.PULL_UP) #right

]
    
#SET GND        
Pin(19, Pin.OUT, 0)
Pin(21, Pin.OUT, 0)
Pin(27, Pin.OUT, 0) 

POWER_PIN = Pin(5, Pin.IN, Pin.PULL_UP)

DEEP_SLEEP_TIME = 7200
# 秒

# 设置超时时间（秒）
CONNECT_TIMEOUT = 300

# 自动按键状态
auto_press_enabled = [False] * len(button_pins)

# 记录上次按键的时间
last_press_time = [0] * len(button_pins)

# 长按状态
long_press_enabled = [False] * len(button_pins)

# 记录按键状态
button_states = [1] * len(button_pins)  # 初始状态为未按下 (1)

# 消抖时间 (毫秒)
debounce_delay = 0

# 定时器列表
timers = {}

sleeptimer = Timer(-1)

# 定义定时器中断处理函数，进入深度睡眠模式
def go_to_deep_sleep(timer):
    print("deep sleeping...")
    time.sleep(1)
    # 配置 ESP32 在 GPIO 引脚上检测到电平变化时唤醒
    esp32.wake_on_ext0(pin=POWER_PIN, level=esp32.WAKEUP_ALL_LOW)
    deepsleep()

def execute_events(events):
    global ble_hid
    for event in events:
        if isinstance(event, KeyEvent):
            delay = event.delay
            action = event.action
            modifier = event.modifier
            keycode = event.keycode

            # 根据不同的 action 执行不同的操作
            if action == "press":
                ble_hid.key_press(special=modifier, general=keycode)
            elif action == "release":
                ble_hid.key_release(special=modifier, general=keycode)
        elif isinstance(event, MouseEvent):
            delay = event.delay
            action = event.action
            button = event.button
            
            # 根据不同的 action 执行不同的操作
            if action == "press":
                ble_hid.mouse_press(get_mouse_button_code(button))
            elif action == "release":
                ble_hid.mouse_release(get_mouse_button_code(button))
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
            time.sleep_ms(event.delay)  # 延迟执行后续事件

def handle_button_press(button_index):
    global button_macros, timers, ble_hid, auto_press_enabled, last_press_time, long_press_enabled, debounce_delay, button_states

    # 消抖处理
    if (time.ticks_ms() - last_press_time[button_index]) < debounce_delay:
        return

    last_press_time[button_index] = time.ticks_ms()

    macro = button_macros[button_index]

    # 如果启用了自动按键功能
    if macro.auto_interval > 0:
        # 切换自动按键状态
        auto_press_enabled[button_index] = not auto_press_enabled[button_index]
        print("Auto press key {}: {}".format(button_index + 1, "Enabled" if auto_press_enabled[button_index] else "Disabled"))

        if auto_press_enabled[button_index]: 
            # 启动定时器
            timer_id = (button_index, "auto")  # 创建唯一的定时器 ID
            #print("on" ,button_index)
            timers[timer_id] = Timer(button_index + 1)  # 创建一个新的定时器，使用正整数 ID
            #timers[timer_id] = Timer(-1) 
            timers[timer_id].init(period=macro.auto_interval, mode=Timer.PERIODIC, callback=lambda t: auto_key_press(button_index))
        else:
            # 停止定时器
           # print("off" ,button_index)
            timer_id = (button_index, "auto")
            if timer_id in timers:
                timers[timer_id].deinit()
                del timers[timer_id]
        return  # 停止当前事件的处理

    # 如果 long_press 为 1，则执行长按操作
    if macro.long_press == 1:
        # 切换长按状态
        long_press_enabled[button_index] = not long_press_enabled[button_index]
        print("Long press key {}: {}".format(button_index + 1, "Enabled" if long_press_enabled[button_index] else "Disabled"))

        if long_press_enabled[button_index]:
            # 启动长按
            execute_events(macro.events)
        else:
            # 停止长按
            # 释放所有按键
            ble_hid.release_all_keys()
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
            ble_hid.key_press(special=modifier, general=keycode)
        elif action == "release":
            ble_hid.key_release(special=modifier, general=keycode)
    elif isinstance(event, MouseEvent):
        delay = event.delay
        action = event.action
        button = event.button

        # 根据不同的 action 执行不同的操作
        if action == "press":
            ble_hid.mouse_press(get_mouse_button_code(button))
        elif action == "release":
            ble_hid.mouse_release(get_mouse_button_code(button))
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
                ble_hid.key_press(special=modifier, general=keycode)
            elif action == "release":
                ble_hid.key_release(special=modifier, general=keycode)
        elif isinstance(event, MouseEvent):
            delay = event.delay
            action = event.action
            button = event.button

            # 根据不同的 action 执行不同的操作
            if action == "press":
                ble_hid.mouse_press(get_mouse_button_code(button))
            elif action == "release":
                ble_hid.mouse_release(get_mouse_button_code(button))
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
    global auto_press_enabled, button_states, timers, button_macros, last_press_time, long_press_enabled

    button_index = button_pins.index(pin)
    current_state = pin.value()

    # 消抖处理
    if (time.ticks_ms() - last_press_time[button_index]) < debounce_delay:
        return

    last_press_time[button_index] = time.ticks_ms()

    macro = button_macros[button_index]

    if current_state == 0 and button_states[button_index] == 1:
        #print("Press")
        button_states[button_index] = 0
        # 按键按下
        
        print("Press key {}: {}".format(button_index + 1,""))

        if macro.key is not None:  # 如果定义了要模拟的键
            ble_hid.key_press(special=macro.modifiers, general=macro.key)  # 模拟组合键按下
        elif macro.button is not None:
            # 执行鼠标按键操作
            #print("mouse press" )
            ble_hid.mouse_press(get_mouse_button_code(macro.button))
        else:
            handle_button_press(button_index)  # 处理其他按键事件

    elif current_state == 1 and button_states[button_index] == 0:
        button_states[button_index] = 1
        # 按键松开
        print("Release key {}: {}".format(button_index + 1, ""))
        
        if macro.key is not None:  # 如果定义了要模拟的键
            ble_hid.key_release(special=macro.modifiers, general=macro.key)  # 模拟组合键松开
        elif macro.button is not None:
            # 执行鼠标按键操作
            #print("mouse release" )
            ble_hid.mouse_release(get_mouse_button_code(macro.button))
        elif macro.auto_interval > 0  and macro.long_press == 1:
            handle_button_press(button_index)  # 处理其他按键事件
            
        # 停止长按
        long_press_enabled[button_index] = False
        ble_hid.release_all_keys()
        # 停止所有定时器
        for timer_id in list(timers.keys()):
            if isinstance(timer_id, tuple) and timer_id[0] == button_index and timer_id[1] != "auto":
                timers[timer_id].deinit()
                del timers[timer_id]

# 初始化时 LED 闪烁
led_state = 0
def led_blink():
    global led_state
    led_state = 1 - led_state
    led_pin.value(led_state)

blink_timer = Timer(-1)
blink_timer.init(period=500, mode=Timer.PERIODIC, callback=lambda t: led_blink())

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


    def mouse_notify(self, keys=0x00, move=(0, 0), wheel=0):
        '''鼠标 按键*8 + 位移 + 滚轮'''
        if self.is_connected():
            _mouse_data = bytearray(4)
            _mouse_data[0] = keys  # 使用第一个字节表示按键状态
            _mouse_data[1] = move[0] & 0xFF
            _mouse_data[2] = move[1] & 0xFF
            _mouse_data[3] = wheel & 0xFF
            self._ble.gatts_notify(self.conn_handle, self.m_rep, bytes(_mouse_data))

    def key_press(self, special=0, general=0):
        '''按下按键'''
        self.saved_special_keys = self.pressed_special_keys.copy()
        self.keyboard_notify(special, general, pressed=True)
        stop_sleep_timer()

    def key_release(self, special=0, general=0):
        '''释放按键'''
        self.keyboard_notify(special, general, pressed=False)
        self.pressed_special_keys = self.saved_special_keys.copy()
        reset_sleep_timer()  # 重置睡眠定时器
    def mouse_press(self, button=0x01):
        '''按下鼠标按键'''
        self.mouse_notify(keys=button)
        stop_sleep_timer()

    def mouse_release(self, button=0x00):
        '''释放鼠标按键'''
        self.mouse_notify(keys=0x00)
        reset_sleep_timer()
    def mouse_click(self, button=0x01):
        '''鼠标单击'''
        self.mouse_notify(keys=button)  # 按下鼠标按键
        self.mouse_notify(keys=0x00)  # 释放鼠标按键
        reset_sleep_timer()
    def release_all_keys(self):
        '''释放所有键盘按键'''
        # self.keyboard_notify(special=0, general=0, pressed=False)  #  这个方法可能不再适用
        self.pressed_special_keys.clear()
        self.pressed_general_keys.clear()
        self.keyboard_notify(special=0, general=0, pressed=False)
        
ble_hid = MyHID(MY_HID_NAME)  # 使用 MyHID 类

start_time = time.time()  # 记录开始时间

while True:
    if ble_hid.is_connected():
        # 连接成功，停止闪烁，LED 长亮
        blink_timer.deinit()
        led_pin.value(1)
        break
    
    time.sleep(0.1)

    # 检查是否超时
    if time.time() - start_time > CONNECT_TIMEOUT:
        print("connect timeout,sleeping")
        go_to_deep_sleep(None)
        break

print("Loaded")

# 设置中断
for pin in button_pins:
    pin.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=button_callback)


#sleeptimer.init(mode=Timer.ONE_SHOT, period=DEEP_SLEEP_TIME * 1000, callback=go_to_deep_sleep)
def stop_sleep_timer():
    return
    global sleeptimer
    #print("sleep stop")
    sleeptimer.deinit()
    
def reset_sleep_timer():
    return
    global sleeptimer
    #print("sleep reset")
    sleeptimer.deinit()
    sleeptimer.init(mode=Timer.ONE_SHOT, period=DEEP_SLEEP_TIME * 1000, callback=go_to_deep_sleep)
    
# 启动定时器    
reset_sleep_timer()
while True:
    time.sleep(0.1)

# 
