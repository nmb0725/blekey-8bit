import network
import time
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