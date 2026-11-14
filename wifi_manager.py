import network
import time
import asyncio
from settings import load_settings

def connect_wifi(timeout=10):
    settings = load_settings()
    ssid = settings.get("wifi_ssid", "")
    password = settings.get("wifi_password", "")
    if not ssid:
        print("WiFi SSID not configured, skipping WiFi connection")
        return False, None
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True, wlan.ifconfig()[0]
    wlan.connect(ssid, password)
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout:
            wlan.active(False)
            return False, None
        time.sleep(1)
    return True, wlan.ifconfig()[0]

def disconnect_wifi():
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        wlan.disconnect()
    wlan.active(False)

def _disable_powersave(wlan):
    """关闭 WiFi 省电（modem sleep）。

    ESP32 上 BLE 与 WiFi 共用同一射频，默认 PM_NORMAL 会让主机在报文间隙休眠，
    导致小报文（ping）正常、连续突发（如 5KB 的 HTML）重传耗尽后报
    [Errno 116] ETIMEDOUT。配置模式必须全程保持全功率收发。
    """
    try:
        pm_none = getattr(wlan, "PM_NONE", 0)
        wlan.config(pm=pm_none)
        print("WiFi powersave disabled")
    except Exception as e:
        print("wifi pm config unsupported:", e)

async def connect_wifi_async(timeout=10):
    settings = load_settings()
    ssid = settings.get("wifi_ssid", "")
    password = settings.get("wifi_password", "")
    if not ssid:
        print("WiFi SSID not configured, skipping WiFi connection")
        return False, None
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    _disable_powersave(wlan)
    if wlan.isconnected():
        return True, wlan.ifconfig()[0]
    wlan.connect(ssid, password)
    start = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout * 1000:
            wlan.active(False)
            return False, None
        await asyncio.sleep_ms(100)
    _disable_powersave(wlan)
    return True, wlan.ifconfig()[0]