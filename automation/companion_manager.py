"""
JARVIS Companion Manager & Local Wi-Fi WebSocket Server
Handles secure, authenticated pairing and two-way communication between
the Windows JARVIS assistant and the JARVIS Companion Android app.
"""

import asyncio
import json
import logging
import os
import socket
import threading
import time
import uuid
from typing import Dict, List, Optional, Tuple, Callable

try:
    import websockets
    from websockets.server import serve
except ImportError:
    websockets = None
    serve = None

logger = logging.getLogger("JarvisCompanion")

STATUS_DISCONNECTED = "DISCONNECTED"
STATUS_AWAITING_AUTH = "AWAITING_AUTH"
STATUS_CONNECTED = "CONNECTED"


def get_local_wifi_ip() -> str:
    """Detects local IPv4 address on the active Wi-Fi or local network interface."""
    # Method 1: Try socket route detection (fastest)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.6)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # Method 2: Inspect network interfaces using psutil
    try:
        import psutil
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        # Priority A: Interface with 'wi-fi', 'wifi', 'wlan', 'wireless' in name
        for iface_name, iface_addrs in addrs.items():
            is_up = stats.get(iface_name).isup if iface_name in stats else True
            if not is_up:
                continue
            name_lower = iface_name.lower()
            if any(k in name_lower for k in ["wi-fi", "wifi", "wlan", "wireless"]):
                for addr in iface_addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        return addr.address

        # Priority B: Any active non-virtual interface with standard private LAN IP
        for iface_name, iface_addrs in addrs.items():
            is_up = stats.get(iface_name).isup if iface_name in stats else True
            if not is_up:
                continue
            name_lower = iface_name.lower()
            if any(k in name_lower for k in ["virtual", "vethernet", "loopback", "wsl", "bluetooth"]):
                continue
            for addr in iface_addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    if addr.address.startswith(("192.168.", "10.", "172.")):
                        return addr.address
    except Exception:
        pass

    # Method 3: Hostname lookup fallback
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    return "127.0.0.1"


class CompanionManager:
    def __init__(self, port: int = 8765, pin: str = "742918", on_status_change: Optional[Callable[[str, str], None]] = None):
        self.port = port
        self.pin = str(pin).strip()
        self.on_status_change = on_status_change

        self.server_ip = get_local_wifi_ip()
        self.status = STATUS_DISCONNECTED
        self.connected_device_info = {}

        self._active_ws = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._is_running = False

    def get_pairing_info(self) -> dict:
        return {
            "ip": self.server_ip,
            "port": self.port,
            "pin": self.pin,
            "status": self.status,
            "device": self.connected_device_info.get("device", "None"),
        }

    def _ensure_port_free(self):
        """Kills any orphaned process holding our companion port using pure psutil."""
        try:
            import psutil
            curr_pid = os.getpid()
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr and conn.laddr.port == self.port:
                    if conn.pid and conn.pid != curr_pid:
                        try:
                            p = psutil.Process(conn.pid)
                            p.kill()
                        except Exception:
                            pass
        except Exception:
            pass

    def start(self):
        """Starts the companion server in a background daemon thread."""
        if self._is_running:
            return
        self.server_ip = get_local_wifi_ip()
        self._ensure_port_free()
        self._is_running = True
        self._thread = threading.Thread(target=self._run_server_thread, daemon=True)
        self._thread.start()
        print(f"[Companion] Server started on ws://{self.server_ip}:{self.port} (Pairing PIN: {self.pin})")

    def _run_server_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main_server())

    async def _main_server(self):
        if not serve:
            print("[Companion] Error: websockets package not installed.")
            return

        for attempt in range(3):
            try:
                async with serve(self._handle_client, "0.0.0.0", self.port):
                    while self._is_running:
                        await asyncio.sleep(1)
                break
            except OSError as e:
                print(f"[Companion] Port {self.port} bind notice (attempt {attempt+1}): {e}")
                self._ensure_port_free()
                await asyncio.sleep(1)

    async def _handle_client(self, websocket):
        client_ip = websocket.remote_address[0] if websocket.remote_address else "Unknown"
        print(f"[Companion] Incoming connection from {client_ip}. Waiting for authentication...")
        self._set_status(STATUS_AWAITING_AUTH, f"Authenticating device at {client_ip}...")

        authenticated = False
        try:
            # First message must be auth payload within 10 seconds
            raw_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(raw_msg)

            if data.get("type") == "auth" and str(data.get("pin")).strip() == self.pin:
                authenticated = True
                device_name = data.get("device", "Android Phone")
                self.connected_device_info = {
                    "device": device_name,
                    "ip": client_ip,
                    "model": data.get("model", "Realme 10 Pro"),
                    "connected_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                self._active_ws = websocket
                self._set_status(STATUS_CONNECTED, f"Connected to {device_name} ({client_ip})")

                # Send success response
                await websocket.send(json.dumps({
                    "type": "auth_ok",
                    "server": "JARVIS Windows",
                    "device": device_name,
                    "message": "Secure authentication successful!"
                }))
                print(f"[Companion] Authenticated device '{device_name}' successfully!")
            else:
                await websocket.send(json.dumps({
                    "type": "auth_error",
                    "message": "Invalid pairing PIN. Connection rejected."
                }))
                print(f"[Companion] Authentication failed for {client_ip}. Closing connection.")
                await websocket.close()
                self._set_status(STATUS_DISCONNECTED, "Authentication rejected")
                return

            # Main message receiver loop
            async for message in websocket:
                try:
                    payload = json.loads(message)
                    self._dispatch_incoming_message(payload)
                except Exception as ex:
                    print(f"[Companion] Error parsing incoming message: {ex}")

        except asyncio.TimeoutError:
            print(f"[Companion] Auth timeout from {client_ip}")
            self._set_status(STATUS_DISCONNECTED, "Auth timeout")
        except websockets.exceptions.ConnectionClosed:
            print(f"[Companion] Connection closed by {client_ip}")
        except Exception as e:
            print(f"[Companion] Connection error with {client_ip}: {e}")
        finally:
            if self._active_ws == websocket:
                self._active_ws = None
                self.connected_device_info = {}
                self._set_status(STATUS_DISCONNECTED, "Device disconnected")

    def _set_status(self, status: str, message: str):
        self.status = status
        if self.on_status_change:
            try:
                self.on_status_change(status, message)
            except Exception:
                pass

    def _dispatch_incoming_message(self, data: dict):
        msg_type = data.get("type")
        req_id = data.get("req_id")

        if req_id and req_id in self._pending_requests:
            fut = self._pending_requests[req_id]
            if not fut.done():
                fut.set_result(data)

        if msg_type == "status_update":
            print(f"[Companion Update] {data.get('message', '')}")
        elif msg_type == "call_placed":
            print(f"[Companion Call Placed] Successfully dialed {data.get('name')} ({data.get('number')})")

    def is_phone_connected(self) -> bool:
        return self.status == STATUS_CONNECTED and self._active_ws is not None

    def _wait_for_phone_connection(self, max_wait: float = 2.5) -> bool:
        """Briefly waits for the phone to reconnect if it recently disconnected (e.g. right after ending a call)."""
        if self.is_phone_connected():
            return True
        start_t = time.time()
        while time.time() - start_t < max_wait:
            time.sleep(0.25)
            if self.is_phone_connected():
                return True
        return False

    def search_contact(self, query: str, timeout: float = 5.0) -> List[dict]:
        """
        Requests the Android Companion to search the user's phone contacts.
        Returns a list of dicts: [{'name': 'Mummy', 'number': '+91 98765 43210'}]
        """
        if not self.is_phone_connected() and not self._wait_for_phone_connection():
            return []

        req_id = str(uuid.uuid4())
        payload = {
            "type": "search_contact",
            "req_id": req_id,
            "query": query
        }

        future = self._run_coroutine_threadsafe(self._send_request(req_id, payload, timeout))
        try:
            res = future.result(timeout=timeout + 1.0)
            if res and res.get("type") == "search_contact_result":
                return res.get("matches", [])
        except Exception as e:
            print(f"[Companion] search_contact timeout/error: {e}")
        return []

    def make_call(self, number: str, name: str, timeout: float = 6.0) -> Tuple[bool, str]:
        """
        Sends command to Android Companion to place a phone call.
        """
        if not self.is_phone_connected() and not self._wait_for_phone_connection():
            return False, "Phone is not connected to JARVIS."

        req_id = str(uuid.uuid4())
        payload = {
            "type": "make_call",
            "req_id": req_id,
            "number": number,
            "name": name
        }

        future = self._run_coroutine_threadsafe(self._send_request(req_id, payload, timeout))
        try:
            res = future.result(timeout=timeout + 1.0)
            if res and res.get("type") == "make_call_result":
                return bool(res.get("success", False)), res.get("message", "Call initiated")
        except Exception as e:
            print(f"[Companion] make_call timeout/error: {e}")
            return False, f"Timeout or error triggering phone call: {e}"
        return False, "No response from phone."

    async def _send_request(self, req_id: str, payload: dict, timeout: float):
        if not self._active_ws:
            raise ConnectionError("No active companion connection")

        fut = self._loop.create_future()
        self._pending_requests[req_id] = fut

        try:
            await self._active_ws.send(json.dumps(payload))
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._pending_requests.pop(req_id, None)

    def _run_coroutine_threadsafe(self, coro):
        if not self._loop or not self._loop.is_running():
            raise RuntimeError("Event loop is not running")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def stop(self):
        self._is_running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)


if __name__ == "__main__":
    mgr = CompanionManager()
    mgr.start()
    print("JARVIS Companion Server is listening on port 8765. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mgr.stop()
