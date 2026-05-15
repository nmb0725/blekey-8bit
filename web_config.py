import socket
import ujson
import machine
import asyncio
from macros import get_macro_names, get_macro_registry, custom_macro_to_dict
from settings import load_settings, save_settings

SERVER_RUNNING = True

def _send_headers(conn, status, content_type):
    response = "HTTP/1.1 %d OK\r\n" % status
    response += "Content-Type: %s\r\n" % content_type
    response += "Connection: close\r\n"
    response += "\r\n"
    try:
        conn.send(response.encode("utf-8"))
    except OSError as e:
        print("HTTP header send failed:", e)

def _send(conn, text):
    try:
        conn.send(text.encode("utf-8"))
    except OSError as e:
        print("HTTP body send failed:", e)

def _close(conn):
    try:
        conn.close()
    except OSError as e:
        print("HTTP close failed:", e)

def _send_json(conn, data):
    body = ujson.dumps(data)
    _send_headers(conn, 200, "application/json")
    _send(conn, body)
    _close(conn)

def _send_error(conn, code, msg):
    _send_headers(conn, code, "text/plain")
    _send(conn, msg)
    _close(conn)

def _send_file(conn, filename, content_type="text/html; charset=utf-8"):
    try:
        _send_headers(conn, 200, content_type)
        with open(filename, "r") as f:
            while True:
                chunk = f.read(128)
                if not chunk:
                    break
                _send(conn, chunk)
    except OSError:
        _send_error(conn, 404, "File not found")
    finally:
        _close(conn)

def _get_ip():
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        if wlan.isconnected():
            return wlan.ifconfig()[0]
    except Exception as e:
        print("Unable to read WiFi IP:", e)
    return "0.0.0.0"

def _parse_request(conn):
    try:
        data = b""
        while True:
            chunk = conn.recv(256)
            if not chunk:
                break
            data += chunk
            if b"\r\n\r\n" in data:
                break
        if not data:
            return None, None, None, None
        request = data.decode("utf-8")
        header_part, _, body_part = request.partition("\r\n\r\n")
        header_lines = header_part.split("\r\n")
        if not header_lines:
            return None, None, None, None
        first = header_lines[0].split(" ")
        if len(first) < 2:
            return None, None, None, None
        method = first[0]
        path = first[1].split("?")[0]
        body = None
        if method == "POST":
            content_length = 0
            for line in header_lines:
                if line.lower().startswith("content-length:"):
                    content_length = int(line.split(":")[1].strip())
                    break
            body = body_part
            while len(body) < content_length:
                chunk = conn.recv(256)
                if not chunk:
                    break
                body += chunk.decode("utf-8")
        return method, path, body, conn
    except Exception as e:
        print("Invalid HTTP request:", e)
        return None, None, None, conn

def _handle_api_settings(conn, method, body):
    if method == "GET":
        settings = load_settings()
        macro_names = get_macro_names()
        ip = _get_ip()
        _send_json(conn, {"settings": settings, "macros": macro_names, "ip": ip})
    elif method == "POST":
        try:
            data = ujson.loads(body)
            save_settings(data)
            _send_json(conn, {"status": "ok"})
        except Exception as e:
            _send_error(conn, 400, "Invalid JSON: " + str(e))

def _handle_api_reboot(conn):
    _send_json(conn, {"status": "rebooting"})
    global SERVER_RUNNING
    SERVER_RUNNING = False
    machine.reset()

def _handle_api_macros(conn):
    names = get_macro_names()
    _send_json(conn, {"macros": names})

def _handle_api_macro(conn, name):
    registry = get_macro_registry()
    if name in registry:
        macro = registry[name]
        data = custom_macro_to_dict(macro)
        _send_json(conn, data)
    else:
        _send_error(conn, 404, "Macro not found")

def _handle_request(conn):
    try:
        method, path, body, conn = _parse_request(conn)
        if method is None:
            _close(conn)
            return
        if path == "/" and method == "GET":
            _send_file(conn, "web_config.html")
        elif path.startswith("/editor") and method == "GET":
            _send_file(conn, "macro_editor.html")
        elif path == "/api/settings":
            _handle_api_settings(conn, method, body)
        elif path == "/api/macros":
            _handle_api_macros(conn)
        elif path.startswith("/api/macro/") and method == "GET":
            macro_name = path.split("/api/macro/")[1]
            _handle_api_macro(conn, macro_name)
        elif path == "/api/reboot" and method == "POST":
            _handle_api_reboot(conn)
        else:
            _send_error(conn, 404, "Not Found")
    except Exception as e:
        try:
            _send_error(conn, 500, "Server Error: " + str(e))
        except Exception as send_error:
            print("Unable to send server error response:", send_error)

async def run_web_server():
    global SERVER_RUNNING
    SERVER_RUNNING = True
    settings = load_settings()
    host = settings.get("web_host", "0.0.0.0")
    port = settings.get("web_port", 80)
    addr = (host, port)
    s = None
    try:
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(3)
        s.settimeout(1)
        while SERVER_RUNNING:
            try:
                conn, _ = s.accept()
                _handle_request(conn)
            except OSError:
                pass
            await asyncio.sleep_ms(50)
    except Exception as e:
        print("Web server error:", e)
    finally:
        if s:
            try:
                s.close()
            except OSError as e:
                print("Web server socket close failed:", e)

def start_web_server():
    return asyncio.create_task(run_web_server())

def stop_web_server():
    global SERVER_RUNNING
    SERVER_RUNNING = False
