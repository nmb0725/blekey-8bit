# BLEKey-8Bit

[English](#english) | [简体中文](#简体中文)

---

## English

A **BLE HID keyboard/mouse macro simulator** built on **ESP32 + MicroPython**, with **WiFi Web configuration** and an **online macro editor** — no desktop flashing tools needed for daily use.

Wire physical buttons to ESP32 GPIO pins, and every press becomes a Bluetooth keyboard/mouse signal on the paired computer.

### Features

- **Keyboard emulation**: map buttons to any standard key (A–Z, F1–F12, arrows, etc.)
- **Combination keys**: Ctrl / Shift / Alt / Win modifier combinations
- **Mouse emulation**: left/middle/right click, mouse movement, wheel scroll
- **Auto repeat**: repeat a macro automatically while a button is held
- **Toggle mode**: one press starts the auto repeat, another stops it
- **Long-press mode**: keep executing while held, stop on release
- **BLE pairing persistence**: pairing keys are stored; auto-reconnect after reboot
- **WiFi Web configuration**: hold the trigger keys for 3 s to enter config mode; edit pin assignment and macro bindings in a browser
- **Online macro editor**: visually build key/mouse event sequences in the browser, including loading and editing single-key macros and reordering event rows
- **Robust config mode**: BLE is suspended during configuration to free the shared radio; the web server has per-request timeouts, connection limits and low-heap protection
- **LED status indication**: heartbeat / advertising blink / WiFi connecting / server state

### Requirements

| Item | Spec |
|------|------|
| MCU | ESP32 (4 MB+ flash) |
| Buttons | Up to 10 (default configuration) |
| LED | Onboard LED (GPIO2) |
| Wiring | Buttons to GND, GPIO pins as pull-up inputs |

### Default Pin Map

Freely editable via the web configuration page.

| GPIO | Function | Default Macro |
|------|----------|---------------|
| 5 | Button 0 | F12_AUTO |
| 18 | Button 1 | F11_AUTO |
| 26 | Button 2 | T_AUTO |
| 27 | Button 3 | R_AUTO |
| 12 | Button 4 | W_SWITCH |
| 13 | Button 5 | LONG_SHIFT_T |
| 23 | Button 6 | UP |
| 22 | Button 7 | LEFT |
| 32 | Button 8 | RIGHT |
| 33 | Button 9 | DOWN |
| 19/21/25 | GND output | Ground reference |

### Quick Start

#### 1. Flash MicroPython

Flash MicroPython **v1.25+** firmware to the ESP32 (must include the `ble_hid` library).

#### 2. Upload Files

With `mpremote` or `Thonny IDE`:

```bash
mpremote cp main.py :main.py
mpremote cp macros.py :macros.py
mpremote cp settings.py :settings.py
mpremote cp wifi_manager.py :wifi_manager.py
mpremote cp web_config.py :web_config.py
mpremote cp web_config.html :web_config.html
mpremote cp macro_editor.html :macro_editor.html
mpremote cp boot.py :boot.py
```

> `settings.json` and `ble_hid_key.py` are runtime state files on the device and should not be committed to Git.
> To initialize the BLE key file manually, see `ble_hid_key.example.py` (an empty dict by default).

#### 3. Configure WiFi (First Time)

1. Power on; the device starts BLE advertising as `ble_keyboard_mouse`
2. Hold **Button 0 + Button 1** for 3 s to enter config mode
3. The LED blinks fast while connecting to WiFi
4. On success the LED turns solid; the IP address is printed to the serial console
5. Open `http://<IP>/` in a browser
6. Fill in WiFi SSID and password, then Save & Reboot
7. After reboot, manage button configuration via the web page

#### 4. Pair with Your Computer

- Search for and pair `ble_keyboard_mouse` in the Bluetooth settings
- LED changes from blinking to solid on successful pairing
- Pairing keys are saved automatically and reconnect on next boot

### Config Mode

| Action | Effect |
|--------|--------|
| Hold trigger keys for 3 s | Enter/exit config mode |
| Open device IP in browser | Web configuration page |
| Edit pins / macro bindings | Applied after save + reboot |
| Click ✎ on a macro | Open the macro editor |

#### LED Status

| LED | Meaning |
|-----|---------|
| Solid, short blink every 5 s | BLE connected, working |
| 500 ms alternating blink | BLE advertising, waiting for pairing |
| 200 ms fast blink | Connecting to WiFi |
| Solid (config mode) | Web server listening |
| 80 ms fast blink (config mode) | Web server failed to listen (check `web_host` / `web_port`) |

### Project Structure

```
blekey-8bit/
├── main.py              # Main firmware: config load, button scan, config mode
├── macros.py            # HID event model, preset macro registry, custom macro conversion
├── settings.py          # Default config, validation, JSON storage (atomic write + corrupt backup)
├── wifi_manager.py      # WiFi connection management
├── web_config.py        # Web server + API
├── web_config.html      # Web configuration page
├── macro_editor.html    # Macro editor page
├── settings.json        # Config file (auto-generated, not tracked by Git)
├── ble_hid_key.py       # BLE pairing keys (auto-generated)
├── boot.py              # MicroPython boot file
├── blekey-8bit.py       # Legacy firmware (hardware timer version)
├── bletest.py           # Test variant (local only, untracked)
└── test.py              # BLE connection test (local only, untracked)
```

### Tech Stack

| Technology | Purpose |
|------------|---------|
| MicroPython | Embedded Python runtime |
| ESP32 | MCU (BLE + WiFi) |
| BLE HID Profile | Bluetooth HID protocol |
| asyncio | Async event loop |
| MicroPython socket | Web server |

### Macro Mode Reference

| Mode | long_press | auto_interval | Behavior |
|:----:|:----------:|:-------------:|----------|
| Single shot | 0 | 0 | Execute event sequence once on press |
| Toggle | 0 | >0 | One press starts auto repeat, another stops |
| Long press | 1 | 0 | Keep executing while held (sequence controls the loop) |
| Long-press auto | 1 | >0 | Repeat at fixed interval while held, stop on release |

## License

MIT

---

## 简体中文

基于 **ESP32 + MicroPython** 的 **BLE HID 键盘/鼠标宏按键模拟器**，支持 **WiFi Web 配置** 和 **在线宏编辑器**。

将物理按键连接到 ESP32 的 GPIO 引脚，即可将按键操作转换为蓝牙键盘/鼠标信号发送到已连接的计算机。

### 功能特性

- **键盘模拟**：映射为任意标准键盘按键（A-Z、F1-F12、方向键等）
- **组合键**：支持 Ctrl/Shift/Alt/Win 修饰键组合
- **鼠标模拟**：支持左/中/右键点击、鼠标移动和滚轮滚动
- **自动连点**：按键按下时自动重复执行宏
- **开关模式**：按一次开启自动执行，再按一次关闭
- **长按模式**：按住时持续执行，松开停止
- **BLE 配对持久化**：配对密钥自动保存，重启后自动重连
- **WiFi Web 配置**：长按触发键进入配置模式，浏览器中修改引脚分配和宏绑定
- **在线宏编辑器**：Web 页面中可视化编辑按键事件序列，支持单键映射宏加载编辑、事件行排序
- **稳健的配置模式**：配置期间自动关闭 BLE 释放共用射频，Web 服务器带请求超时、连接数上限与低堆保护
- **LED 状态指示**：心跳常亮/广播闪烁/WiFi 连接中/服务器状态提示

### 硬件要求

| 组件 | 规格 |
|------|------|
| 主控芯片 | ESP32（4MB+ 闪存） |
| 物理按键 | 最多 10 个（默认配置） |
| LED | 板载 LED（GPIO2） |
| 连接线 | 按键接 GND，GPIO 引脚内部上拉输入 |

### 引脚分配（默认）

可通过 Web 配置页面自由修改。

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
| 19/21/25 | GND 输出 | 接地参考 |

### 快速开始

#### 1. 烧录 MicroPython 固件

将 MicroPython **v1.25+** 固件烧录到 ESP32（需包含 `ble_hid` 库）。

#### 2. 上传文件

使用 `mpremote` 或 `Thonny IDE`：

```bash
# mpremote 方式
mpremote cp main.py :main.py
mpremote cp macros.py :macros.py
mpremote cp settings.py :settings.py
mpremote cp wifi_manager.py :wifi_manager.py
mpremote cp web_config.py :web_config.py
mpremote cp web_config.html :web_config.html
mpremote cp macro_editor.html :macro_editor.html
mpremote cp boot.py :boot.py
```

> `settings.json` 和 `ble_hid_key.py` 是设备运行时生成的本地状态文件，不应提交到 Git。
> 如果需要手动初始化 BLE 密钥文件，可参考 `ble_hid_key.example.py`，默认内容为空字典。

#### 3. 首次配置 WiFi

1. 上电后 ESP32 开始 BLE 广播，设备名 `ble_keyboard_mouse`
2. 长按 **按键 0 + 按键 1** 3 秒进入配置模式
3. LED 快速闪烁表示正在连接 WiFi
4. 连接成功后串口输出 IP 地址，服务器就绪后 LED 常亮
5. 浏览器访问 `http://<IP>/` 打开配置页面
6. 填写 WiFi SSID 和密码，点击 Save & Reboot
7. 重启后即可通过 Web 页面管理按键配置

#### 4. 与电脑配对

- 在电脑蓝牙设置中搜索并配对 `ble_keyboard_mouse`
- 配对成功后 LED 从闪烁变为常亮
- 配对密钥自动保存，下次开机自动重连

### 配置模式

| 操作 | 效果 |
|------|------|
| 长按触发键 3 秒 | 进入/退出配置模式 |
| 浏览器访问设备 IP | 打开 Web 配置页面 |
| 修改引脚/宏绑定 | 保存后重启生效 |
| 点击宏的 ✎ 按钮 | 打开宏编辑器 |

#### LED 状态指示

| LED 状态 | 含义 |
|----------|------|
| 常亮，每 5 秒闪一次 | BLE 已连接，正常工作 |
| 500ms 交替闪烁 | BLE 广播中，等待配对 |
| 200ms 快速闪烁 | 正在连接 WiFi |
| 常亮（配置模式） | Web 服务器已监听 |
| 80ms 快速闪烁（配置模式） | Web 服务器未启动（检查 web_host/web_port） |

### 项目文件结构

```
blekey-8bit/
├── main.py              # 主程序：配置加载、按键扫描、配置模式
├── macros.py            # HID 事件模型、预设宏注册表、自定义宏转换
├── settings.py          # 默认配置、配置校验、JSON 存储（原子写入 + 损坏备份）
├── wifi_manager.py      # WiFi 连接管理
├── web_config.py        # Web 服务器 + API
├── web_config.html      # Web 配置页面
├── macro_editor.html    # 宏编辑器页面
├── settings.json        # 配置文件（自动生成，不同步 Git）
├── ble_hid_key.py       # BLE 配对密钥（自动生成）
├── boot.py              # MicroPython 启动引导
├── blekey-8bit.py       # 旧版固件（硬件定时器版本）
├── bletest.py           # 测试变体（仅本地保留，不跟踪 Git）
└── test.py              # BLE 连接测试（仅本地保留，不跟踪 Git）
```

### 技术栈

| 技术 | 用途 |
|------|------|
| MicroPython | 嵌入式 Python 运行环境 |
| ESP32 | 主控芯片（BLE + WiFi） |
| BLE HID Profile | 蓝牙人机交互设备协议 |
| asyncio | 异步事件循环 |
| MicroPython socket | Web 服务器 |

### 宏类型参考

| 模式 | long_press | auto_interval | 行为 |
|:----:|:----------:|:-------------:|------|
| 单击 | 0 | 0 | 按下执行一次事件序列 |
| 开关 | 0 | >0 | 按一次开启自动重复，再按一次关闭 |
| 长按 | 1 | 0 | 按住持续执行（需自行控制循环） |
| 长按自动 | 1 | >0 | 按住时以固定间隔循环执行，松开停止 |

## License

MIT
