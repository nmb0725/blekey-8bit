import bluetooth
import time
from machine import Pin
from ble_hid import HID
import struct

# 1.25 关键常量
_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GET_SECRET = 21
_IRQ_SET_SECRET = 20
_IRQ_ENCRYPTION_UPDATE = 28 # 1.25 加密成功标志

MY_HID_NAME = 'ble_keyboard_mouse'
led = Pin(2, Pin.OUT)

class RobustHID(HID):
    def __init__(self, name):
        self.secrets = {}
        self.load_secrets()
        super().__init__(name)
        
        try:
            # 1.25 固件配置
            self._ble.config(bond=True, le_sec=True, io=0)
        except:
            pass

        self._ble.irq(self._custom_irq)
        print("1.25 适配广播中...")
        self.start_advertising(name)
# --- 新增：发送原始按键数据的逻辑 ---
    def send_raw(self, modifier, keycode, pressed=True):
        """
        发送标准的 8 字节 HID 报文
        modifier: 修饰键 (Shift, Ctrl 等)
        keycode: 按键码 (A=0x04)
        """
        if self.conn_handle is None:
            return
            
        # 构造 8 字节的 HID 键盘报文
        # byte 0: modifier, byte 2: keycode
        buf = bytearray(8)
        if pressed:
            buf[0] = modifier
            buf[2] = keycode
        # 否则全 0 代表释放
        
        try:
            # 使用内置 HID 类的 k_rep (Keyboard Report 句柄) 发送通知
            self._ble.gatts_notify(self.conn_handle, self.k_rep, buf)
        except Exception as e:
            print("Notify Error:", e)

    def release_all(self):
        """释放所有按键"""
        self.send_raw(0x00, 0x00, False)
    def load_secrets(self):
        try:
            import ble_hid_key
            self.secrets = ble_hid_key.keys
        except:
            pass
        aaa
    def start_advertising(self, name):
        payload = bytearray(b'\x02\x01\x06')
        payload += b'\x03\x19\xc1\x03'
        payload += b'\x03\x03\x12\x18'
        name_bytes = name.encode()
        payload += struct.pack('B', len(name_bytes) + 1) + b'\x09' + name_bytes
        self._ble.gap_advertise(100, adv_data=payload, connectable=True)

    def _custom_irq(self, event, data):
        # 1. 密钥匹配（重连核心）
        if event == _IRQ_GET_SECRET:
            raw_key_info = bytes(data[-1])
            for k, v in self.secrets.items():
                if k[1] == raw_key_info or raw_key_info in k[1]:
                    print(">>> 密钥匹配成功")
                    return v
            return None

        # 2. 密钥保存
        elif event == _IRQ_SET_SECRET:
            sec_type, index, key_data = data[0], data[1], data[2]
            self.secrets[(sec_type, index)] = key_data
            try:
                with open("ble_hid_key.py", "w") as f:
                    f.write("keys = " + repr(self.secrets))
                print("密钥已存档")
            except: pass
            return True

        # 3. 关键：手动捕捉连接句柄 (解决灯闪问题)
        elif event == _IRQ_CENTRAL_CONNECT:
            self.conn_handle = data[0] # <--- 显式赋值给 self.conn_handle
            print(">>> 物理连接已建立，Handle:", self.conn_handle)
        
        # 4. 关键：加密更新 (Windows 真正接通数据流)
        elif event == _IRQ_ENCRYPTION_UPDATE:
            # data: (conn_handle, encrypted, authenticated)
            if data[1]: # 如果 encrypted 为 True
                self.conn_handle = data[0]
                print(">>> 加密已激活，HID 通道开启")

        elif event == _IRQ_CENTRAL_DISCONNECT:
            self.conn_handle = None
            print("已断开")
            self.start_advertising(MY_HID_NAME)

        # 转发所有事件给内置逻辑
        return self._irq(event, data)

# --- 启动 ---
print("--- 自动重连完成：正在等待 Windows 握手 ---")
ble = RobustHID(MY_HID_NAME)

while True:
    # 现在 self.conn_handle 已经在 IRQ 中被显式赋值了
    if ble.conn_handle is not None:
        led.value(1) # 常亮
# 增加一个延时，确保连接后的握手彻底完成
        time.sleep(1) 
        
        print("正在发送 A...")
        try:
            # 1. 发送按下 'a' (0x04)
            # 这里的参数顺序通常是 (modifiers, keycode, is_pressed)
            ble.send_raw(0x00, 0x04, True)
            
            # 2. 必须保持按下状态一小段时间，Windows 才能识别
            time.sleep_ms(100) 
            
            # 3. 发送全部释放包 (这是 ble_hid 里的标准做法)
            # 或者 ble.send_raw(0x00, 0x00, False)
            ble.release_all() 
            
            print("已发送并释放")
        except Exception as e:
            print("发送失败:", e)
            
        # 每 2 秒循环一次
        time.sleep(2)
    else:
        led.value(not led.value()) # 闪烁
    time.sleep(0.5)