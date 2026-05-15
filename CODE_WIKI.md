# BLEKey-8Bit 项目 Code Wiki

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 项目结构](#2-项目结构)
- [3. 运行环境与依赖](#3-运行环境与依赖)
- [4. 系统架构](#4-系统架构)
- [5. 核心模块详解](#5-核心模块详解)
  - [5.1 事件系统（Event System）](#51-事件系统event-system)
  - [5.2 按键宏系统（KeyMacro）](#52-按键宏系统keymacro)
  - [5.3 BLE HID 通信层（MyHID）](#53-ble-hid-通信层myhid)
  - [5.4 按键扫描器（Button Scanner）](#54-按键扫描器button-scanner)
  - [5.5 宏执行引擎（Macro Executor）](#55-宏执行引擎macro-executor)
  - [5.6 主循环与状态管理](#56-主循环与状态管理)
- [6. 关键类与函数参考](#6-关键类与函数参考)
- [7. 文件说明](#7-文件说明)
- [8. HID 键码参考表](#8-hid-键码参考表)
- [9. 运行与部署方式](#9-运行与部署方式)
- [10. 常见问题与调试](#10-常见问题与调试)

---

## 1. 项目概述

**BLEKey-8Bit** 是一个基于 **ESP32** 微控制器和 **MicroPython** 固件的 **蓝牙低功耗（BLE）HID 键盘鼠标模拟器** 项目。它通过将物理按键连接到 ESP32 的 GPIO 引脚，实现将按键操作转换为蓝牙键盘/鼠标信号发送到已连接的计算机。

### 核心功能

- **键盘模拟**：将 GPIO 按键映射为标准键盘按键（如 F11、F12、Tab、方向键等）
- **组合键支持**：支持修饰键组合（Ctrl+数字、Ctrl+Shift+T、Alt+R 等）
- **鼠标模拟**：支持鼠标左/中/右键点击、鼠标移动和滚轮滚动
- **自动连点**：支持按键按下时自动重复执行宏（如自动点击、自动按键）
- **开关模式**：支持切换式自动执行（按一次开启，再按一次关闭）
- **BLE 配对与重连**：支持与主机（Windows/Linux/Mac）的蓝牙配对密钥持久化存储，实现自动重连
- **LED 状态指示**：通过板载 LED 显示连接状态（常亮=已连接，闪烁=广播中）
- **深度睡眠（旧版本）**：旧版本支持长时间无操作后进入深度睡眠以节省电量

### 技术栈

| 技术 | 用途 |
|------|------|
| MicroPython | 嵌入式 Python 运行环境 |
| ESP32 | 主控芯片（BLE + WiFi 双模） |
| BLE HID Profile | 蓝牙人机交互设备协议 |
| asyncio | 异步事件循环（main.py） |
| Machine Timer | 硬件定时器中断（blekey-8bit.py） |

---

## 2. 项目结构

```
blekey-8bit/
├── main.py              # 主程序：配置加载、按键扫描、配置模式触发
├── macros.py            # HID 事件模型、预设宏注册表、自定义宏转换
├── settings.py          # 默认配置、JSON 存储
├── wifi_manager.py      # WiFi 连接管理
├── web_config.py        # Web 服务器 + API 路由
├── web_config.html      # Web 配置页面（独立 HTML 文件）
├── macro_editor.html    # 宏编辑器页面（独立 HTML 文件）
├── settings.json        # 运行时生成的配置文件（自动创建）
├── ble_hid_key.py       # BLE 配对密钥（自动生成）
├── boot.py              # MicroPython 启动引导文件
├── blekey-8bit.py       # (旧版本) 基于硬件定时器的旧版固件
├── bletest.py           # (测试/变体) 与 main.py 架构相同，宏配置不同
├── test.py              # (测试脚本) 简单的 BLE HID 连接测试
└── .gitattributes       # Git 换行符配置
```

### 文件关系图

```
                  ┌─────────────────────┐
                  │    boot.py          │
                  │  (MicroPython 启动)  │
                  └─────────┬───────────┘
                            │
          ┌─────────────────┼──────────────────────────┐
          │                 │                          │
   ┌──────▼──────┐  ┌──────▼──────┐           ┌───────▼───────┐
   │   main.py   │  │ blekey-8bit │           │  bletest.py   │
   │ (asyncio版) │  │  .py(定时器) │           │  (asyncio版)  │
   └──┬───┬───┬──┘  └──────┬──────┘           └───────┬───────┘
      │   │   │            │                          │
      ▼   ▼   ▼            └────────────┬─────────────┘
  ┌────┐ ┌───┐ ┌──────┐               │
  │mac-│ │set-│ │wifi │ │web_          │
  │ros │ │tings│ │mana│ │config├──┐    │
  │.py │ │.py  │ │ger │ │.py   │  │   │
  └──┬─┘ │.py  │ │.py  │ │.html │  │  │
     │   └──┬──┘ └────┘ └───────┘  │  │
     │         │            │          │
     │         ▼            ▼          │
     │   ┌──────────┐ ┌──────────┐     │
     │   │settings. │ │web_config│     │
     │   │json      │ │.html     │     │
     │   └──────────┘ │macro_edi │     │
     │                │tor.html  │     │
     │                └──────────┘     │
     └────────────────┬───────────────-┘
                      │
               ┌──────▼──────┐
               │ ble_hid_key │
               │   .py       │
               │  (密钥存储)  │
               └─────────────┘
```

**依赖的外部库（烧录在 ESP32 固件中）**：

- `ble_hid` — MicroPython 标准 BLE HID 库，提供 `HID` 基类
- `machine` — MicroPython 硬件控制库（Pin, freq）
- `bluetooth` — MicroPython BLE 核心库
- `asyncio` — MicroPython 异步 I/O 库
- `struct` — Python 标准库，字节打包
- `ujson` — MicroPython JSON 库
- `gc` — 垃圾回收
- `network` — WiFi 连接管理
- `socket` — TCP/IP 网络通信（Web 服务器）

---

## 3. 运行环境与依赖

### 硬件要求

| 组件 | 规格 |
|------|------|
| 主控芯片 | ESP32（如 ESP-WROOM-32, ESP32-DevKitC） |
| 闪存 | 至少 4MB（用于存放 MicroPython 固件 + 脚本） |
| 物理按键 | 10 个（main.py 配置为 10 按键） |
| LED | 板载 LED（GPIO2） |
| 连接线 | 按键接 GND，GPIO 引脚配置为内部上拉输入 |

### 引脚分配（main.py 版本 — 默认值，可通过 Web 配置页面修改）

| GPIO | 功能 | 默认宏 |
|------|------|--------|
| 5 | 按键 0 | F12_AUTO |
| 18 | 按键 1 | F11_AUTO |
| 26 | 按键 2 | T_AUTO |
| 27 | 按键 3 | R_AUTO |
| 12 | 按键 4 | W_SWITCH |
| 13 | 按键 5 | LONG_SHIFT_T |
| 23 | 按键 6 | UP |
| 22 | 按键 7 | LEFT |
| 32 | 按键 8 | RIGHT |
| 33 | 按键 9 | DOWN |
| 19 | GND 输出 | 接地参考 |
| 21 | GND 输出 | 接地参考 |
| 25 | GND 输出 | 接地参考 |

### 软件依赖

- MicroPython 固件 **v1.25+**（对 main.py 版本，因为使用了新的 BLE 安全 API）
- `ble_hid` 库（MicroPython 标准库的一部分，需包含在固件中）

### 烧录工具

- 使用 `mpremote`、`Thonny IDE` 等工具

---

## 4. 系统架构

### 4.1 整体架构（main.py — asyncio 版本）

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         main.py 系统架构                                   │
│                                                                          │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────────────────┐       │
│  │ 按键扫描器 │──▶│  状态管理     │──▶│  宏执行引擎                 │       │
│  │ (button   │   │ auto_enabled │   │  auto_loop_task /          │       │
│  │  _scanner)│   │ active_tasks │   │  run_events_async          │       │
│  │          │   │ prev_state   │   │                            │       │
│  └────┬─────┘   └──────────────┘   └───────────┬────────────────┘       │
│       │                                         │                        │
│       │ 长按触发 3 秒                            ▼                        │
│       │                                  ┌──────────────┐               │
│       └───────────────────────────────▶   │  Config Mode │               │
│                                           │  ┌──────────┐│               │
│                                           │  │WiFi连接   ││               │
│                                           │  │Web服务器  ││               │
│                                           │  │宏编辑器   ││               │
│                                           │  └──────────┘│               │
│                                           └──────────────┘               │
│                                                  │                       │
│                                                  ▼                       │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    BLE HID 通信层 (MyHID)                      │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │       │
│  │  │密钥管理   │  │广播管理   │  │IRQ处理    │  │数据发送      │ │       │
│  │  │secrets   │  │advertising│  │_custom_irq│  │send_raw /    │ │       │
│  │  │          │  │          │  │          │  │send_mouse    │ │       │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    主循环 (main)                               │       │
│  │  连接状态检测 → LED 心跳指示 → 垃圾回收 (gc.collect)           │       │
│  └──────────────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.2 架构特点

**main.py（asyncio 版本）**：
- 使用 MicroPython 的 `asyncio` 实现非阻塞并发
- 按键扫描采用轮询方式（非中断），每隔 5ms 扫描一次
- 宏执行使用异步任务（`asyncio.create_task`），支持多宏并发
- 支持长按自动重复和开关式自动执行

**blekey-8bit.py（定时器版本）**：
- 使用硬件 GPIO 中断（`Pin.irq`）检测按键事件
- 使用硬件定时器（`Timer`）实现自动重复
- 支持深度睡眠（`deepsleep`）以省电
- 不支持鼠标移动功能（仅支持按键和鼠标点击）

---

## 5. 核心模块详解

### 5.1 事件系统（Event System）

事件系统使用 Python 的 `namedtuple` 定义了五种事件类型，作为宏的基本执行单元。

#### KeyEvent — 键盘按键事件

```python
KeyEvent = namedtuple("KeyEvent", ["delay", "action", "modifier", "keycode"])
```

| 字段 | 类型 | 说明 |
|------|------|------|
| delay | int | 执行前等待的毫秒数 |
| action | str | `"press"` 按下 / `"release"` 释放 |
| modifier | int | 修饰键位掩码（见下方） |
| keycode | int | HID 键码（见 HID 键码参考表） |

**修饰键位掩码**：

| 值 | 含义 |
|----|------|
| 0x00 | 无修饰键 |
| 0x01 | 左 Ctrl |
| 0x02 | 左 Shift |
| 0x03 | Ctrl + Shift |
| 0x04 | 左 Alt |
| 0x05 | Ctrl + Alt |
| 0x10 | 右 Ctrl |

#### MouseEvent — 鼠标点击事件

```python
MouseEvent = namedtuple("MouseEvent", ["delay", "action", "button"])
```

| 字段 | 类型 | 说明 |
|------|------|------|
| delay | int | 执行前等待的毫秒数 |
| action | str | `"press"` 按下 / `"release"` 释放 |
| button | str | `"left"` / `"right"` / `"middle"` |

#### MouseMoveEvent — 鼠标移动事件

```python
MouseMoveEvent = namedtuple("MouseMoveEvent", ["delay", "action", "x", "y"])
```

| 字段 | 类型 | 说明 |
|------|------|------|
| delay | int | 执行前等待的毫秒数 |
| action | str | 固定为 `"move"` |
| x | int | 水平位移 (-127 ~ 127) |
| y | int | 垂直位移 (-127 ~ 127) |

#### WheelEvent — 滚轮事件

```python
WheelEvent = namedtuple("WheelEvent", ["delay", "action", "delta"])
```

| 字段 | 类型 | 说明 |
|------|------|------|
| delay | int | 执行前等待的毫秒数 |
| action | str | 固定为 `"scroll"` |
| delta | int | 滚轮步进值（正=上滚，负=下滚，通常 120 为一步） |

#### DelayEvent — 延迟事件

```python
DelayEvent = namedtuple("DelayEvent", ["delay", "action"])
```

| 字段 | 类型 | 说明 |
|------|------|------|
| delay | int | 等待的毫秒数 |
| action | str | 固定为 `"delay"` |

---

### 5.2 按键宏系统（KeyMacro）

`KeyMacro` 是项目中最重要的数据结构，它将物理按键与一系列 HID 操作绑定在一起。

```python
KeyMacro = namedtuple("KeyMacro", [
    "events",         # list[Event] — 事件列表
    "auto_interval",  # int — 自动重复间隔(ms)，0=不自动
    "long_press",     # int — 0=单击模式, 1=长按/开关模式
    "key",            # int/None — 直接映射的 HID 键码
    "modifiers",      # int — 修饰键位掩码
    "button",         # str/None — 鼠标按钮名
    "cancel"          # int — 1=释放时取消任务, 0=继续执行(仅main.py)
])
```

**宏的工作模式**（由 `long_press` 和 `auto_interval` 的组合决定）：

| long_press | auto_interval | 行为模式 |
|:----------:|:-------------:|----------|
| 0 | 0 | **单击模式**：按下时执行一次 `events` 中的事件序列 |
| 0 | >0 | **开关模式**：按一次开启自动重复，再按一次关闭 |
| 1 | 0 | **长按模式**：按住时持续执行 `events`（需在 events 中自行控制循环） |
| 1 | >0 | **长按自动重复模式**：按住时以 `auto_interval` 间隔循环执行 events，松开停止 |

**直接映射模式**（当 `key` 或 `button` 不为 None 时）：

- **key 模式**：`events` 为空，按下/松开直接发送对应的 HID 键码
- **button 模式**：`events` 为空，按下/松开直接发送鼠标按钮信号

#### 预定义的宏示例

```python
# 简单按键映射（方向键）
UP    = KeyMacro(events=[], auto_interval=0, long_press=0,
                 key=0x52, modifiers=0, button=None, cancel=1)

# 组合键（Ctrl+1）
CTRL_1 = KeyMacro(events=[], auto_interval=0, long_press=0,
                  key=0x1E, modifiers=0x01, button=None, cancel=1)

# 自动重复（自动按 F12，每 50ms 一次）
F12_AUTO = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x00, keycode=0x45),
    KeyEvent(delay=30, action="release", modifier=0x00, keycode=0x45)
], auto_interval=50, long_press=1, key=None, modifiers=0, button=None, cancel=1)

# 鼠标连点
LEFT_CLICK_AUTO = KeyMacro(events=[
    MouseEvent(delay=0, action="press", button="left"),
    MouseEvent(delay=50, action="release", button="left")
], auto_interval=100, long_press=0, key=None, modifiers=0x00, button=None, cancel=1)

# 复杂组合键（Ctrl+Shift+T）
CTRL_SHIFT_T = KeyMacro(events=[
    KeyEvent(delay=0, action="press", modifier=0x03, keycode=0x17),
    KeyEvent(delay=0, action="release", modifier=0x03, keycode=0x17)
], auto_interval=0, long_press=0, key=None, modifiers=0x00, button=None, cancel=1)
```

---

### 5.3 BLE HID 通信层（MyHID）

`MyHID` 类继承自 `ble_hid` 库的 `HID` 基类，负责所有蓝牙通信细节。

#### 类定义

```python
class MyHID(HID):
    def __init__(self, name)
    def load_secrets(self)
    def start_advertising(self, name)
    def _custom_irq(self, event, data)
    def is_connected(self) -> bool
    def send_raw(self, mod, key, pressed=True)
    def send_mouse(self, buttons=0, x=0, y=0, wheel=0)
    def release_all(self)
```

#### 初始化流程

```
MyHID.__init__("ble_keyboard_mouse")
    │
    ├── 1. 加载本地密钥 (load_secrets)
    │     从 ble_hid_key.py 读取已保存的配对密钥
    │
    ├── 2. 调用父类 HID.__init__ 注册 BLE 服务
    │     注册 HID 键盘、鼠标服务到 GATT 服务器
    │
    ├── 3. 配置 BLE 安全
    │     bond=True   → 支持绑定（记住配对）
    │     le_sec=True → 启用 LE 安全连接
    │     io=0        → 无 I/O 能力（NoInputNoOutput）
    │
    ├── 4. 注册自定义 IRQ 处理函数
    │     覆盖默认中断处理，处理密钥交换
    │
    └── 5. 开始广播 (start_advertising)
           手动构建标准 HID 广播包
```

#### IRQ 事件处理（_custom_irq）

`_custom_irq` 是 BLE 通信的核心，处理 5 种关键事件：

| 事件 | 常量值 | 处理逻辑 |
|------|:------:|----------|
| `_IRQ_GET_SECRET` | 21 | **密钥匹配**：主机请求配对密钥，在本地字典中查找匹配项返回 |
| `_IRQ_SET_SECRET` | 20 | **密钥存储**：主机下发配对密钥，保存到字典并写入 `ble_hid_key.py` |
| `_IRQ_CENTRAL_CONNECT` | 1 | **连接建立**：记录连接句柄 `conn_handle` |
| `_IRQ_ENCRYPTION_UPDATE` | 28 | **加密完成**：加密激活后更新连接句柄（此时才可发送数据） |
| `_IRQ_CENTRAL_DISCONNECT` | 2 | **断开连接**：清除连接句柄，重新开始广播 |

未处理的事件通过 `return self._irq(event, data)` 转发给父类的默认处理。

#### 数据发送

**键盘报文**（8 字节）：

```
byte[0]: 修饰键位掩码 (Ctrl/Shift/Alt/等)
byte[1]: 保留 (0x00)
byte[2]: 按键1 HID 键码
byte[3]: 按键2 HID 键码 (未使用)
byte[4-7]: 按键3-6 HID 键码 (未使用)
```

**鼠标报文**（4 字节）：

```
byte[0]: 鼠标按钮位掩码 (0x01=左, 0x02=右, 0x04=中)
byte[1]: X 轴位移 (-127 ~ 127)
byte[2]: Y 轴位移 (-127 ~ 127)
byte[3]: 滚轮步进 (-127 ~ 127)
```

#### 广播数据包结构

```
[0x02, 0x01, 0x06]             → BLE Flags: LE General Discoverable + BR/EDR Not Supported
[0x03, 0x19, 0xC1, 0x03]       → Appearance: Keyboard (0x03C1)
[0x03, 0x03, 0x12, 0x18]       → Complete List of 16-bit UUIDs: HID Service (0x1812)
[len+1, 0x09, name_bytes...]    → Complete Local Name: "ble_keyboard_mouse"
```

---

### 5.4 按键扫描器（Button Scanner）

`button_scanner()` 是 `main.py` 中的异步协程，负责检测 GPIO 引脚的电平变化。

#### 扫描流程

```python
async def button_scanner():
    while True:
        for i, pin in enumerate(button_pins):
            val = pin.value()          # 读取当前电平
            if val != prev_state[i]:   # 检测变化
                await asyncio.sleep_ms(15)  # 消抖延时
                if pin.value() == val:      # 再次确认
                    prev_state[i] = val
                    # ... 根据宏配置执行相应操作
        await asyncio.sleep_ms(5)      # 每 5ms 扫描一轮
```

#### 按键按下（val == 0）处理逻辑

```
检测到按键按下
    │
    ├── long_press == 1
    │   └── 开启自动重复任务 (auto_loop_task)
    │
    ├── auto_interval > 0 (且 long_press == 0)
    │   └── 切换 auto_enabled[i] 状态
    │       ├── 开启 → 创建 auto_loop_task
    │       └── 关闭 → 取消 auto_loop_task
    │
    ├── macro.key 不为 None
    │   └── 直接发送按键按下信号 (send_raw)
    │
    ├── macro.button 不为 None
    │   └── 直接发送鼠标按钮按下信号 (send_mouse)
    │
    └── 其他情况
        └── 异步执行一次 events (run_events_async)
```

#### 按键释放（val == 1）处理逻辑

```
检测到按键释放
    │
    ├── long_press == 1
    │   ├── 关闭 auto_enabled[i]
    │   ├── 如果 cancel==1，取消 active_tasks[i]
    │   └── 释放所有按键 (release_all)
    │
    ├── macro.key 不为 None
    │   └── 发送按键释放信号 (send_raw, pressed=False)
    │
    └── macro.button 不为 None
        └── 发送鼠标按钮释放信号 (send_mouse, buttons=0)
```

---

### 5.5 宏执行引擎（Macro Executor）

#### run_events_async — 事件序列执行器

按顺序执行宏中的事件列表，根据事件类型调用不同的 BLE 发送方法：

```python
async def run_events_async(macro, idx):
    for event in macro.events:
        if macro.cancel == 1 and not auto_enabled[idx]:
            break  # 取消标志，提前退出
        if isinstance(event, KeyEvent):
            ble_hid.send_raw(event.modifier, event.keycode, action=="press")
        elif isinstance(event, MouseEvent):
            ble_hid.send_mouse(buttons=btn_val)  # press 或 0
        elif isinstance(event, MouseMoveEvent):
            ble_hid.send_mouse(x=event.x, y=event.y)
        elif isinstance(event, WheelEvent):
            ble_hid.send_mouse(wheel=event.delta)
        elif isinstance(event, DelayEvent):
            await asyncio.sleep_ms(event.delay)
        await asyncio.sleep_ms(max(event.delay, 10))
```

#### auto_loop_task — 自动循环任务

当宏配置了 `auto_interval` 时使用，在循环中反复执行事件序列：

```python
async def auto_loop_task(idx):
    macro = button_macros[idx]
    try:
        while auto_enabled[idx]:
            await run_events_async(macro, idx)
            if macro.auto_interval > 0:
                await asyncio.sleep_ms(macro.auto_interval)
            else:
                break
    finally:
        ble_hid.release_all()  # 确保异常退出时释放按键
        active_tasks[idx] = None
```

---

### 5.6 主循环与状态管理

#### main() — 主协程

```python
async def main():
    asyncio.create_task(button_scanner())  # 启动扫描器
    while True:
        if ble_hid.is_connected():
            # 已连接：LED 常亮，每 5 秒闪烁一次心跳
        else:
            # 未连接：LED 闪烁表示正在广播
        gc.collect()  # 主动垃圾回收
        await asyncio.sleep_ms(500)
```

#### 全局状态数组

```python
auto_enabled = [False] * len(button_pins)  # 每个按键的自动执行开关状态
active_tasks = [None] * len(button_pins)   # 每个按键的活跃异步任务引用
prev_state   = [1] * len(button_pins)      # 每个按键的上一次电平状态（用于边沿检测）
```

---

## 6. 关键类与函数参考

### 6.1 MyHID 类（main.py / bletest.py）

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `__init__` | `name: str` | — | 初始化 BLE HID 设备，加载密钥，开始广播 |
| `load_secrets` | — | — | 从 `ble_hid_key.py` 加载已保存的配对密钥 |
| `start_advertising` | `name: str` | — | 手动构建标准 HID 广播包并开始广播 |
| `_custom_irq` | `event: int, data: tuple` | `Any` | 处理 BLE 中断事件（密钥交换、连接、断开） |
| `is_connected` | — | `bool` | 返回当前 BLE 连接状态 |
| `send_raw` | `mod: int, key: int, pressed: bool` | — | 发送 8 字节 HID 键盘报文 |
| `send_mouse` | `buttons, x, y, wheel: int` | — | 发送 4 字节 HID 鼠标报文 |
| `release_all` | — | — | 释放所有键盘和鼠标按键 |

### 6.2 MyHID 类（blekey-8bit.py — 旧版本）

| 方法 | 说明 |
|------|------|
| `keyboard_notify(special, general, pressed)` | 更新按键状态并发送键盘通知，支持最多 6 键同时按下 |
| `mouse_notify(keys, move, wheel)` | 发送鼠标通知 |
| `key_press(special, general)` | 按下按键并停止睡眠定时器 |
| `key_release(special, general)` | 释放按键并重置睡眠定时器 |
| `mouse_press(button)` | 按下鼠标按钮 |
| `mouse_release(button)` | 释放鼠标按钮 |
| `mouse_click(button)` | 执行鼠标单击 |
| `release_all_keys()` | 清除所有按键状态并发送释放通知 |

### 6.3 核心函数（main.py）

| 函数 | 说明 |
|------|------|
| `button_scanner()` | 异步协程，轮询所有 GPIO 引脚检测按键状态变化 |
| `run_events_async(macro, idx)` | 异步执行宏中的事件序列 |
| `auto_loop_task(idx)` | 异步循环任务，按 auto_interval 重复执行宏 |
| `main()` | 程序主入口协程，启动扫描器并管理 LED 心跳 |

### 6.4 核心函数（blekey-8bit.py — 旧版本）

| 函数 | 说明 |
|------|------|
| `button_callback(pin)` | GPIO 中断处理函数，检测按键按下/释放 |
| `handle_button_press(button_index)` | 处理按键按下事件（切换自动/长按模式） |
| `delayed_action(button_index, event_index, timer_id)` | 定时器回调，执行延迟的按键事件 |
| `auto_key_press(button_index)` | 定时器回调，自动重复执行宏事件 |
| `execute_events(events)` | 同步执行事件列表（阻塞式） |
| `get_mouse_button_code(button)` | 将按钮名称转换为 HID 鼠标按钮码 |
| `go_to_deep_sleep(timer)` | 进入深度睡眠模式 |
| `stop_sleep_timer()` | 停止睡眠定时器 |
| `reset_sleep_timer()` | 重置睡眠定时器（重新计时） |

---

## 7. 文件说明

### 7.1 main.py（主要版本）

- **用途**：项目的主固件，使用 asyncio 异步架构
- **特点**：
  - 10 个 GPIO 按键输入，支持 Web 页面配置引脚和宏绑定
  - 基于 asyncio 的非阻塞并发
  - 完整的鼠标支持（点击、移动、滚轮）
  - BLE 1.25 固件兼容（绑定、加密、自动重连）
  - LED 心跳指示（已连接时常亮，每 5 秒闪一次）
  - 主动垃圾回收（每 500ms 调用 `gc.collect()`）
  - **配置模式**：长按触发键 3 秒进入，通过 WiFi Web 页面配置

### 7.2 macros.py（新增）

- **用途**：HID 事件模型、预设宏注册表和自定义宏转换
- **功能**：
  - 定义 `KeyEvent`、`MouseEvent`、`MouseMoveEvent`、`WheelEvent`、`DelayEvent`、`KeyMacro` 等核心数据结构
  - 维护 35 个预置宏的注册表（`MACRO_REGISTRY`）
  - 支持自定义宏的 JSON 解析（`parse_custom_macro`）和序列化（`custom_macro_to_dict`）
  - 提供宏名称列表查询（`get_macro_names`）供 Web 配置页面使用

### 7.3 settings.py

- **用途**：配置持久化管理
- **功能**：
  - 定义 `DEFAULT_SETTINGS` 默认配置
  - 管理 `settings.json` 的加载/保存/合并
  - 处理 CUSTOM 宏的 custom_events 保留逻辑

### 7.4 wifi_manager.py（新增）

- **用途**：WiFi 连接管理
- **功能**：
  - 从 `settings.json` 读取 SSID/密码
  - 连接预设 WiFi 网络（超时处理）
  - 断开 WiFi 连接

### 7.5 web_config.py（新增）

- **用途**：Web 配置服务器
- **功能**：
  - 基于 MicroPython `socket` 的 HTTP 服务器
  - 路由分发：主页面、宏编辑器页面、API 接口
  - API：`/api/settings`、`/api/macros`、`/api/macro/<name>`、`/api/reboot`
  - HTML 文件流式发送（128 字节分块，避免内存溢出）

### 7.6 web_config.html（新增）

- **用途**：Web 配置主页面（独立 HTML 文件，不占用 RAM）
- **功能**：
  - 按键配置列表（引脚 + 宏下拉选择）
  - 系统设置（触发键、长按时间、Web 服务器）
  - WiFi 设置（SSID、密码）
  - 保存 / 保存并重启
  - 每个按键的 **✎ 编辑按钮**，链接到宏编辑器

### 7.7 macro_editor.html（新增）

- **用途**：宏编辑器页面（独立 HTML 文件，不占用 RAM）
- **功能**：
  - 5 种事件类型：key / mouse / move / wheel / delay
  - 常用键下拉菜单 + 兜底 hex 输入
  - 修饰键下拉菜单（Ctrl/Shift/Alt/Win 组合）
  - 增/删事件行
  - 宏级设置：auto_interval、long_press、cancel
  - 保存时自动转为 CUSTOM 类型

### 7.8 blekey-8bit.py（旧版本）

- **用途**：项目的早期版本，使用硬件定时器和中断
- **特点**：
  - 4 个 GPIO 按键输入
  - 基于硬件中断（`Pin.irq`）和定时器（`Timer`）
  - 深度睡眠省电模式（3600 秒超时）
  - 关闭 WiFi 以节省电量
  - CPU 频率降低到 80MHz（省电）
  - 连接超时检测（300 秒）

### 7.9 bletest.py（测试变体）

- **用途**：与 main.py 架构相同的测试版本，宏配置略有不同
- **特点**：
  - 与 main.py 共享相同的 `MyHID` 类定义
  - 宏配置：`MOUSE_WIGGLE`, `F11_AUTO`, `T_AUTO`, `R_AUTO`, `KEY_6` 等
  - 10 个按键，引脚分配与 main.py 相同

### 7.10 test.py / bletest.py（简单测试）

- **用途**：快速测试 BLE HID 连接和按键发送功能
- **特点**：
  - 连接成功后发送字母 "A"（0x04）按键
  - 每 2 秒发送一次
  - 用于验证 BLE 通信是否正常

### 7.11 ble_hid_key.py

- **用途**：自动生成的 BLE 配对密钥存储文件
- **生成方式**：首次与主机配对时由 `_custom_irq` 中的 `_IRQ_SET_SECRET` 事件处理逻辑自动写入
- **格式**：`keys = {(sec_type, key_data): stored_key_data, ...}`
- **注意**：此文件在每次配对成功后自动更新，不应手动编辑

### 7.12 boot.py

- **用途**：MicroPython 启动引导文件
- **内容**：当前基本为空（仅含注释），可按需启用 WebREPL 等

---

## 8. HID 键码参考表

项目中使用的 HID 键码（USB HID Usage Tables）：

| 键码 (Hex) | 按键 | 键码 (Hex) | 按键 |
|:----------:|:----:|:----------:|:----:|
| 0x04 | A | 0x05 | B |
| 0x06 | C | 0x07 | D |
| 0x08 | E | 0x09 | F |
| 0x0A | G | 0x0B | H |
| 0x0C | I | 0x0D | J |
| 0x0E | K | 0x0F | L |
| 0x10 | M | 0x11 | N |
| 0x12 | O | 0x13 | P |
| 0x14 | Q | 0x15 | R |
| 0x16 | S | 0x17 | T |
| 0x18 | U | 0x19 | V |
| 0x1A | W | 0x1B | X |
| 0x1C | Y | 0x1D | Z |
| 0x1E | 1 (!) | 0x1F | 2 (@) |
| 0x20 | 3 (#) | 0x21 | 4 ($) |
| 0x22 | 5 (%) | 0x23 | 6 (^) |
| 0x28 | Enter | 0x29 | Escape |
| 0x2B | Tab | 0x2C | Space |
| 0x39 | Caps Lock | 0x44 | F11 |
| 0x45 | F12 | 0x4F | 右箭头 |
| 0x50 | 左箭头 | 0x51 | 下箭头 |
| 0x52 | 上箭头 | | |

**修饰键位掩码**：

| 值 | 含义 |
|:--:|------|
| 0x01 | 左 Ctrl |
| 0x02 | 左 Shift |
| 0x04 | 左 Alt |
| 0x08 | 左 Win/Command |
| 0x10 | 右 Ctrl |
| 0x20 | 右 Shift |
| 0x40 | 右 Alt |
| 0x80 | 右 Win/Command |

---

## 9. 运行与部署方式

### 9.1 准备工作

1. **烧录 MicroPython 固件**到 ESP32（推荐 v1.25+ 版本）
2. **确保固件包含 `ble_hid` 库**（部分预编译固件可能不包含，需要自行编译）
3. **连接硬件**：按键一端接 GND，另一端接对应的 GPIO 引脚

### 9.2 部署步骤

**方法一：使用 mpremote（推荐）**

```bash
# 上传全部文件
mpremote cp main.py :main.py
mpremote cp macros.py :macros.py
mpremote cp settings.py :settings.py
mpremote cp wifi_manager.py :wifi_manager.py
mpremote cp web_config.py :web_config.py
mpremote cp web_config.html :web_config.html
mpremote cp macro_editor.html :macro_editor.html
mpremote cp boot.py :boot.py
```

**方法二：使用 Thonny IDE**

1. 打开 Thonny IDE，选择 "MicroPython (ESP32)" 解释器
2. 选择对应的串口
3. 打开 `main.py` 并保存到 ESP32 设备
4. 复位 ESP32，程序自动运行

### 9.3 启动流程

```
ESP32 上电
    │
    ├── boot.py 执行（基本为空）
    │
    └── main.py 执行
        │
        ├── 设置 CPU 频率 160MHz
        ├── 配置 GPIO 引脚（上拉输入）
        ├── 配置 GND 输出引脚
        ├── 初始化 BLE HID 设备
        │   ├── 加载配对密钥
        │   ├── 注册 BLE 服务
        │   └── 开始广播
        │
        ├── 启动按键扫描器
        │
        └── 进入主循环
            ├── LED 心跳（已连接 / 未连接）
            └── 垃圾回收
```

### 9.4 与主机配对

1. 上电后 ESP32 开始广播，设备名称为 `ble_keyboard_mouse`
2. 在电脑的蓝牙设置中搜索并配对
3. 配对成功后，ESP32 的板载 LED 从闪烁变为常亮
4. 配对密钥会自动保存到 `ble_hid_key.py`，下次开机可自动重连

---

## 10. 常见问题与调试

### 10.1 LED 状态指示

| LED 状态 | 含义 |
|-----------|------|
| 常亮，每 5 秒短暂熄灭 | 正常模式，BLE 已连接 |
| 500ms 交替闪烁 | BLE 广播中，等待配对 |
| 200ms 快速闪烁 | 正在连接 WiFi |
| 熄灭 | 配置模式运行中 |

### 10.2 常见问题

**Q: 连接后按键无反应？**

A: 检查 `_IRQ_ENCRYPTION_UPDATE` 事件是否被正确触发。在 MicroPython 1.25 中，加密完成后才能发送数据。确认 `conn_handle` 在加密更新事件中被正确赋值。

**Q: 每次开机都需要重新配对？**

A: 检查 `ble_hid_key.py` 是否存在且内容正确。密钥存储依赖文件写入，如果 ESP32 文件系统损坏或密钥文件丢失，需要重新配对。

**Q: 按键不灵敏或误触？**

A: 软件中已有 15ms 的消抖延时。如果仍然有问题，可以增大 `button_scanner` 中的 `asyncio.sleep_ms(15)` 值。

**Q：如何在不上传代码的情况下修改按键功能？**

A：进入配置模式，通过 Web 页面修改：
1. 长按按键 0 + 按键 1 约 3 秒进入配置模式
2. ESP32 连接预设 WiFi 后 LED 常亮
3. 浏览器访问串口输出的 IP 地址
4. 在配置页面修改按键的宏绑定或引脚号
5. 点击 Save & Reboot 重启生效

详细步骤见 README.md 中的"配置模式"章节。

### 10.3 调试方法

在 main.py 开头取消注释相关打印语句，或添加新的调试输出：

```python
# 查看连接状态
print("Connected:", ble_hid.is_connected())

# 查看按键事件
print("Button", i, "pressed")

# 查看发送的数据
print("Sending:", modifier, keycode, pressed)
```

也可使用 MicroPython 的 WebREPL 进行远程调试（需在 boot.py 中启用）。

---

## 附录：版本对比

| 特性 | main.py (asyncio) | blekey-8bit.py (定时器) |
|:-----|:-----------------:|:----------------------:|
| 并发模型 | asyncio 协程 | 硬件中断 + 定时器 |
| 按键检测 | 轮询 (5ms) | 中断 (IRQ) |
| 按键数量 | 10 | 4 |
| 鼠标移动 | 支持 | 不支持 |
| 滚轮 | 支持 | 支持 |
| 深度睡眠 | 不支持 | 支持 (3600s) |
| CPU 频率 | 160MHz | 80MHz |
| WiFi | 未关闭 | 显式关闭 |
| 密钥持久化 | 支持 | 不支持 |
| 连接超时 | 无 | 300s 后休眠 |
| 垃圾回收 | 每 500ms | 无 |