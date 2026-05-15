import network
import socket
import machine
import time

WIFI_SSID = "nmbwl1"
WIFI_PASSWORD = "ff1234567890"

def connect_wifi(timeout=10):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True, wlan.ifconfig()[0]
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout:
            return False, None
        time.sleep(1)
    return True, wlan.ifconfig()[0]

success, ip = connect_wifi()
if not success:
    print("WiFi FAIL")
else:
    print("WiFi OK, IP:", ip)

addr = ("0.0.0.0", 80)
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(3)
print("Server ready at http://%s:80" % ip)

while True:
    conn, _ = s.accept()
    data = conn.recv(1024)
    if data:
        html = "<h1>BLEKey Test</h1><p>OK</p>"
        resp = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s" % (len(html), html)
        conn.send(resp.encode())
    conn.close()