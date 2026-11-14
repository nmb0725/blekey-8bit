import socket
import ujson
import machine
import asyncio
import time
import os
import gc
from macros import get_macro_names, get_macro_registry, custom_macro_to_dict
from settings import load_settings, save_settings

SERVER_RUNNING = True
PENDING_REBOOT = False
# 服务是否成功开始监听：供上层用 LED 区分"服务正常"与"端口没起来"
SERVER_OK = False

# 请求上限：防止坏客户端耗尽堆内存
MAX_HEADER_BYTES = 1500
MAX_BODY_BYTES = 8192
# 单次请求整体超时（收），超时即断开，避免拖住事件循环
REQUEST_TIMEOUT_MS = 6000
# 未发送任何数据的连接（预连接）的回收时限
IDLE_DEADLINE_MS = 3000
# 单次发送超时：必须短，否则慢客户端会占住主循环，按键扫描随之卡住
SEND_TIMEOUT_MS = 2500
# 发送 HTML 文件的总预算（文件较大，且 ESP32 上射频偶发抖动需要留重试时间）
FILE_SEND_TIMEOUT_MS = 12000
# 同时保持的连接数：浏览器预连接很常见，上限防止内存耗尽
MAX_CLIENTS = 3
# 主循环轮询间隔：决定配置模式下退出组合键的响应灵敏度
POLL_INTERVAL_MS = 20
# 堆低于此值时拒绝新连接，保护 BLE 与按键扫描
MIN_FREE_HEAP = 3072

# lwip 非阻塞 socket 无数据/无空间时的错误码
_EAGAIN = (11, 10004, 110)


def _is_would_block(e):
    args = getattr(e, "args", None)
    if args and isinstance(args[0], int):
        return args[0] in _EAGAIN
    return True  # 无 errno 信息时按可重试处理


async def _send_all(conn, data, deadline):
    """发送完整 bytes。

    注意：这里刻意使用"带超时的阻塞发送"而不是非阻塞 + 手动重试。
    非阻塞 send 在不同 MicroPython 版本上可能返回 None 或以非 EAGAIN 的
    OSError 失败，实测会导致响应一个字节都发不出去（浏览器表现为连不上）。
    超时已经限死了占用时长，不会拖住事件循环。
    """
    total = len(data)
    sent = 0
    while sent < total:
        try:
            n = conn.send(data[sent:])
        except OSError as e:
            if _is_would_block(e):
                if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                    print("send timeout at %d/%d" % (sent, total))
                    return False
                await asyncio.sleep_ms(5)
                continue
            print("send error at %d/%d: %s (heap=%d)" % (sent, total, e, gc.mem_free()))
            return False
        if not n:
            # 阻塞模式下返回 0/None 视为异常，避免死循环
            print("send stalled at %d/%d (heap=%d)" % (sent, total, gc.mem_free()))
            return False
        sent += n
    return True


def _close(conn):
    try:
        conn.close()
    except:
        pass


async def _send_response(conn, status, content_type, body, status_text="OK"):
    """发送完整响应（含 Content-Length），body 为 bytes 或 None。"""
    deadline = time.ticks_add(time.ticks_ms(), SEND_TIMEOUT_MS)
    length = len(body) if body else 0
    head = "HTTP/1.1 %d %s\r\n" % (status, status_text)
    head += "Content-Type: %s\r\n" % content_type
    head += "Content-Length: %d\r\n" % length
    head += "Connection: close\r\n\r\n"
    if not await _send_all(conn, head.encode("utf-8"), deadline):
        return False
    if length and not await _send_all(conn, body, deadline):
        return False
    return True


async def _send_json(conn, data):
    try:
        body = ujson.dumps(data).encode("utf-8")
    except Exception as e:
        await _send_error(conn, 500, "JSON encode failed: " + str(e))
        _close(conn)
        return
    await _send_response(conn, 200, "application/json", body)
    _close(conn)


async def _send_error(conn, code, msg):
    status_text = {400: "Bad Request", 404: "Not Found",
                   413: "Payload Too Large", 500: "Internal Server Error",
                   503: "Service Unavailable"}.get(code, "Error")
    try:
        await _send_response(conn, code, "text/plain; charset=utf-8",
                             str(msg).encode("utf-8"), status_text)
    except:
        pass


async def _send_file(conn, filename, content_type="text/html; charset=utf-8"):
    try:
        st = os.stat(filename)
        size = st[6]
    except OSError as e:
        # 文件没上传到设备根目录时会走到这里
        print("file missing: %s (%s)" % (filename, e))
        await _send_error(conn, 404, "File not found: " + filename)
        _close(conn)
        return
    print("sending %s (%d bytes)" % (filename, size))
    deadline = time.ticks_add(time.ticks_ms(), FILE_SEND_TIMEOUT_MS)
    head = "HTTP/1.1 200 OK\r\n"
    head += "Content-Type: %s\r\n" % content_type
    head += "Content-Length: %d\r\n" % size
    head += "Connection: close\r\n\r\n"
    sent = 0
    try:
        if not await _send_all(conn, head.encode("utf-8"), deadline):
            print("header send failed for %s" % filename)
            return
        with open(filename, "rb") as f:
            while True:
                chunk = f.read(512)
                if not chunk:
                    break
                if not await _send_all(conn, chunk, deadline):
                    print("body send failed at %d/%d for %s" % (sent, size, filename))
                    return
                sent += len(chunk)
        # 发送字节数与声明的 Content-Length 不一致会让浏览器一直等或判定连接异常
        if sent != size:
            print("WARN %s: sent %d but Content-Length %d" % (filename, sent, size))
        else:
            print("sent OK: %s" % filename)
    finally:
        _close(conn)


def _get_ip():
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        if wlan.isconnected():
            return wlan.ifconfig()[0]
    except:
        pass
    return "0.0.0.0"


def _try_parse(buf):
    """非阻塞解析。
    返回 None（数据不完整）、"ERR_TOO_LARGE"、"ERR_BAD"，或 (method, path, body_bytes)
    """
    if len(buf) > MAX_HEADER_BYTES + MAX_BODY_BYTES:
        return "ERR_TOO_LARGE"
    sep = buf.find(b"\r\n\r\n")
    if sep < 0:
        if len(buf) > MAX_HEADER_BYTES:
            return "ERR_TOO_LARGE"
        return None
    lines = buf[:sep].decode("utf-8", "ignore").split("\r\n")
    body = buf[sep + 4:]
    first = lines[0].split(" ") if lines else []
    if len(first) < 2:
        return "ERR_BAD"
    method = first[0]
    path = first[1].split("?")[0]
    if method != "POST":
        return method, path, b""
    content_length = 0
    for line in lines:
        if line.lower().startswith("content-length:"):
            try:
                content_length = int(line.split(":")[1].strip())
            except:
                return "ERR_BAD"
            break
    if content_length > MAX_BODY_BYTES:
        return "ERR_TOO_LARGE"
    if len(body) < content_length:
        return None
    return method, path, bytes(body[:content_length])


async def _handle_api_settings(conn, method, body):
    if method == "GET":
        settings = load_settings()
        macro_names = get_macro_names()
        ip = _get_ip()
        await _send_json(conn, {"settings": settings, "macros": macro_names, "ip": ip})
    elif method == "POST":
        try:
            data = ujson.loads(body)
        except Exception as e:
            await _send_error(conn, 400, "Invalid JSON: " + str(e))
            _close(conn)
            return
        try:
            save_settings(data)
        except MemoryError:
            gc.collect()
            await _send_error(conn, 503, "Out of memory, please retry")
            _close(conn)
            return
        except Exception as e:
            await _send_error(conn, 400, "Save failed: " + str(e))
            _close(conn)
            return
        await _send_json(conn, {"status": "ok"})


async def _handle_api_reboot(conn):
    await _send_json(conn, {"status": "rebooting"})
    global PENDING_REBOOT
    PENDING_REBOOT = True


async def _handle_api_macros(conn):
    await _send_json(conn, {"macros": get_macro_names()})


async def _handle_api_macro(conn, name):
    registry = get_macro_registry()
    if name in registry:
        await _send_json(conn, custom_macro_to_dict(registry[name]))
    else:
        await _send_error(conn, 404, "Macro not found")
        _close(conn)


async def _handle_request(conn, method, path, body):
    try:
        print("REQ %s %s (%d)" % (method, path, len(body) if body else 0))
        if path == "/" and method == "GET":
            await _send_file(conn, "web_config.html")
        elif path.startswith("/editor") and method == "GET":
            await _send_file(conn, "macro_editor.html")
        elif path == "/api/settings":
            await _handle_api_settings(conn, method, body)
        elif path == "/api/macros":
            await _handle_api_macros(conn)
        elif path.startswith("/api/macro/") and method == "GET":
            await _handle_api_macro(conn, path.split("/api/macro/")[1])
        elif path == "/api/reboot" and method == "POST":
            await _handle_api_reboot(conn)
        else:
            await _send_error(conn, 404, "Not Found")
    except Exception as e:
        try:
            await _send_error(conn, 500, "Server Error: " + str(e))
        except:
            pass


async def run_web_server():
    global SERVER_RUNNING, PENDING_REBOOT, SERVER_OK
    SERVER_RUNNING = True
    SERVER_OK = False
    settings = load_settings()
    host = settings.get("web_host", "0.0.0.0") or "0.0.0.0"
    # 网页里填成非数字会让 bind 直接抛异常，导致"能 ping 通但没有服务"
    try:
        port = int(settings.get("web_port", 80) or 80)
    except (ValueError, TypeError):
        print("invalid web_port, falling back to 80")
        port = 80
    s = None
    clients = []
    # 依次尝试：配置的 host -> 0.0.0.0。若 web_host 被填成一个换网后已失效的具体 IP，
    # bind 会失败导致"能 ping 通但 80 端口没人听"，此时自动回退到监听所有接口。
    attempts = [host] + (["0.0.0.0"] if host != "0.0.0.0" else [])
    for try_host in attempts:
        for attempt in range(3):
            try:
                s = socket.socket()
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((try_host, port))
                s.listen(4)
                host = try_host
                break
            except Exception as e:
                print("bind %s:%s failed (try %d): %s" % (try_host, port, attempt + 1, e))
                if s:
                    _close(s)
                    s = None
                gc.collect()
                await asyncio.sleep_ms(500)
        if s:
            break
    if s is None:
        SERVER_OK = False
        print("Web server: giving up on %s:%s" % (host, port))
        return
    try:
        # 关键：accept 必须非阻塞，否则无连接时会同步阻塞整个事件循环
        s.settimeout(0)
        SERVER_OK = True
        print("Web server listening on %s:%s (heap=%d)" % (host, port, gc.mem_free()))
        while SERVER_RUNNING:
            now = time.ticks_ms()
            # 1. 接受新连接（不阻塞）
            try:
                conn, _ = s.accept()
            except OSError:
                conn = None
            if conn:
                conn.settimeout(0)
                if gc.mem_free() < MIN_FREE_HEAP and clients:
                    # 仅在已有其它连接时才拒绝，避免内存计数的瞬时抖动
                    # 把每一个连接都挡在门外
                    try:
                        conn.settimeout(2)
                        await _send_error(conn, 503, "Low memory, retry shortly")
                    except BaseException:
                        pass
                    _close(conn)
                    gc.collect()
                elif len(clients) >= MAX_CLIENTS:
                    # 槽位占满时优先淘汰尚未发送任何数据的预连接，
                    # 否则新请求会被拒绝，浏览器表现为 Failed to fetch
                    victim = None
                    for c in clients:
                        if not c["buf"]:
                            victim = c
                            break
                    if victim:
                        clients.remove(victim)
                        _close(victim["s"])
                        clients.append({"s": conn, "buf": bytearray(), "closed": False, "t0": now})
                    else:
                        _close(conn)
                else:
                    clients.append({"s": conn, "buf": bytearray(), "closed": False, "t0": now})
            # 2. 轮询所有连接：空闲连接每轮只付出一条非阻塞 recv 的代价
            for c in clients[:]:
                while len(c["buf"]) <= MAX_HEADER_BYTES + MAX_BODY_BYTES:
                    try:
                        chunk = c["s"].recv(512)
                    except OSError:
                        chunk = None
                    if chunk is None:
                        break
                    if not chunk:
                        c["closed"] = True
                        break
                    c["buf"] += chunk
                res = _try_parse(c["buf"])
                # 从未收到数据的连接（预连接）更早回收，尽快释放槽位
                limit = IDLE_DEADLINE_MS if not c["buf"] else REQUEST_TIMEOUT_MS
                expired = time.ticks_diff(time.ticks_add(c["t0"], limit), now) <= 0
                if res is None:
                    if c["closed"] or expired:
                        clients.remove(c)
                        _close(c["s"])
                    continue
                clients.remove(c)
                try:
                    # 请求已收完整，切回带超时的阻塞发送：非阻塞 send 在
                    # MicroPython 上不可靠（可能返回 None / 非 EAGAIN 错误）
                    conn_s = c["s"]
                    conn_s.settimeout(3)
                    if res == "ERR_TOO_LARGE":
                        await _send_error(conn_s, 413, "Request too large")
                    elif res == "ERR_BAD":
                        await _send_error(conn_s, 400, "Bad request")
                    else:
                        method, path, body = res
                        await _handle_request(conn_s, method, path,
                                              body.decode("utf-8", "ignore") if body else "")
                except KeyboardInterrupt:
                    raise
                except BaseException as e:
                    # 包括 MemoryError：单个请求绝不能让服务任务永久退出
                    print("request error:", e)
                finally:
                    _close(c["s"])
                    gc.collect()
            # 3. 重启请求
            if PENDING_REBOOT:
                PENDING_REBOOT = False
                try:
                    os.sync()
                except:
                    pass
                await asyncio.sleep_ms(300)
                machine.reset()
            await asyncio.sleep_ms(POLL_INTERVAL_MS)
    except BaseException as e:
        print("Web server error:", e)
    finally:
        for c in clients:
            _close(c["s"])
        if s:
            try:
                s.close()
            except:
                pass


def start_web_server():
    return asyncio.create_task(run_web_server())


def stop_web_server():
    global SERVER_RUNNING
    SERVER_RUNNING = False
