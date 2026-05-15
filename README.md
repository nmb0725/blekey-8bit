# BLEKey-8Bit

基于 **ESP32 + MicroPython** 的 **BLE HID 键盘/鼠标宏按键模拟器**，支持 **WiFi Web 配置** 和 **在线宏编辑器**。

将物理按键连接到 ESP32 的 GPIO 引脚，即可将按键操作转换为蓝牙键盘/鼠标信号发送到已连接的计算机。

## 功能特性

- **键盘模拟**：映射为任意标准键盘按键（A-Z、F1-F12、方向键等）
- **组合键**：支持 Ctrl/Shift/Alt/Win 修饰键组合
- **鼠标模拟**：支持左/中/右键点击、鼠标移动和滚轮滚动
- **自动连点**：按键按下时自动重复执行宏
- **开关模式**：按一次开启自动执行，再按一次关闭
- **长按模式**：按住时持续执行，松开停止
- **BLE 配对持久化**：配对密钥自动保存，重启后自动重连
- **WiFi Web 配置**：长按触发键进入配置模式，浏览器中修改引脚分配和宏绑定
- **在线宏编辑器**：Web 页面中可视化编辑按键事件序列
- **LED 状态指示**：心跳常亮/广播闪烁/WiFi 连接中快速闪烁

## 硬件要求

| 组件 | 规格 |
|------|------|
| 主控芯片 | ESP32（4MB+ 闪存） |
| 物理按键 | 最多 10 个（默认配置） |
| LED | 板载 LED（GPIO2） |
| 连接线 | 按键接 GND，GPIO 引脚内部上拉输入 |

## 引脚分配（默认）

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

## 快速开始

### 1. 烧录 MicroPython 固件

将 MicroPython **v1.25+** 固件烧录到 ESP32（需包含 `ble_hid` 库）。

### 2. 上传文件

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

### 3. 首次配置 WiFi

1. 上电后 ESP32 开始 BLE 广播，设备名 `ble_keyboard_mouse`
2. 长按 **按键 0 + 按键 1** 3 秒进入配置模式
3. LED 快速闪烁表示正在连接 WiFi
4. 连接成功后 LED 熄灭，串口输出 IP 地址
5. 浏览器访问 `http://<IP>/` 打开配置页面
6. 填写 WiFi SSID 和密码，点击 Save & Reboot
7. 重启后即可通过 Web 页面管理按键配置

### 4. 与电脑配对

- 在电脑蓝牙设置中搜索并配对 `ble_keyboard_mouse`
- 配对成功后 LED 从闪烁变为常亮
- 配对密钥自动保存，下次开机自动重连

## 配置模式

| 操作 | 效果 |
|------|------|
| 长按触发键 3 秒 | 进入/退出配置模式 |
| 浏览器访问设备 IP | 打开 Web 配置页面 |
| 修改引脚/宏绑定 | 保存后重启生效 |
| 点击宏的 ✎ 按钮 | 打开宏编辑器 |

### LED 状态指示

| LED 状态 | 含义 |
|----------|------|
| 常亮，每 5 秒闪一次 | BLE 已连接，正常工作 |
| 500ms 交替闪烁 | BLE 广播中，等待配对 |
| 200ms 快速闪烁 | 正在连接 WiFi |
| 熄灭 | 配置模式运行中 |

## 项目文件结构

```
blekey-8bit/
├── main.py              # 主程序：配置加载、按键扫描、配置模式
├── macros.py            # HID 事件模型、预设宏注册表、自定义宏转换
├── settings.py          # 默认配置、配置校验、JSON 存储
├── wifi_manager.py      # WiFi 连接管理
├── web_config.py        # Web 服务器 + API
├── web_config.html      # Web 配置页面
├── macro_editor.html    # 宏编辑器页面
├── settings.json        # 配置文件（自动生成，不同步 Git）
├── ble_hid_key.py       # BLE 配对密钥（自动生成）
├── boot.py              # MicroPython 启动引导
├── blekey-8bit.py       # 旧版固件（硬件定时器版本）
├── bletest.py           # 测试变体
└── test.py              # BLE 连接测试
```

## 技术栈

| 技术 | 用途 |
|------|------|
| MicroPython | 嵌入式 Python 运行环境 |
| ESP32 | 主控芯片（BLE + WiFi） |
| BLE HID Profile | 蓝牙人机交互设备协议 |
| asyncio | 异步事件循环 |
| MicroPython socket | Web 服务器 |

## 宏类型参考

| 模式 | long_press | auto_interval | 行为 |
|:----:|:----------:|:-------------:|------|
| 单击 | 0 | 0 | 按下执行一次事件序列 |
| 开关 | 0 | >0 | 按一次开启自动重复，再按一次关闭 |
| 长按 | 1 | 0 | 按住持续执行（需自行控制循环） |
| 长按自动 | 1 | >0 | 按住时以固定间隔循环执行，松开停止 |

## License

MIT