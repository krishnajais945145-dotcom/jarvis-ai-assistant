import os
import sys
import time
import json
import logging
import threading
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Callable

import requests
import websockets

logger = logging.getLogger("JarvisWhatsApp")

STATUS_DISCONNECTED = "DISCONNECTED"
STATUS_CONNECTING = "CONNECTING"
STATUS_AWAITING_QR = "AWAITING_QR"
STATUS_CONNECTED = "CONNECTED"
STATUS_SEARCHING_CONTACT = "SEARCHING_CONTACT"
STATUS_PREPARING_ATTACHMENT = "PREPARING_ATTACHMENT"
STATUS_AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
STATUS_SENDING = "SENDING"
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"

class WhatsAppAutomation:
    """
    Robust WhatsApp Web automation using native Chrome/Edge DevTools Protocol (CDP).
    Safely reuses existing authenticated browser sessions without storing passwords or tokens.
    """
    def __init__(self, port: int = 9222, profile_dir: Optional[str] = None):
        self.port = port
        if profile_dir:
            self.profile_dir = Path(profile_dir)
        else:
            self.profile_dir = Path.home() / ".jarvis_whatsapp_profile"
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        self.browser_proc: Optional[subprocess.Popen] = None
        self.status = STATUS_DISCONNECTED
        self.status_message = "WhatsApp Web is not running."
        self.on_status_change: Optional[Callable[[str, str], None]] = None
        self._lock = threading.Lock()
        self._ws_url: Optional[str] = None
        self._pending_action: Optional[Dict[str, Any]] = None

    def set_status(self, new_status: str, message: str = ""):
        self.status = new_status
        self.status_message = message
        logger.info(f"[WhatsApp] Status: {new_status} - {message}")
        if self.on_status_change:
            try:
                self.on_status_change(new_status, message)
            except Exception as e:
                logger.error(f"[WhatsApp] Callback error: {e}")

    def _find_browser_executable(self) -> Optional[str]:
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
        ]
        for p in candidates:
            if Path(p).exists():
                return p
        return None

    def is_browser_cdp_available(self) -> bool:
        try:
            r = requests.get(f"http://127.0.0.1:{self.port}/json/version", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def launch_browser(self) -> Tuple[bool, str]:
        """Launches Chrome/Edge with CDP remote debugging and dedicated persistent profile."""
        if self.is_browser_cdp_available():
            logger.info("[WhatsApp] CDP port 9222 already active. Reusing running browser session.")
            return True, "Reusing running browser session."

        exe = self._find_browser_executable()
        if not exe:
            return False, "Google Chrome or Microsoft Edge could not be found on this computer."

        cmd = [
            exe,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1200,850",
            "https://web.whatsapp.com"
        ]

        try:
            self.browser_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Wait for CDP to become active
            for _ in range(15):
                time.sleep(1.0)
                if self.is_browser_cdp_available():
                    return True, "Browser launched with persistent profile."
            return False, "Browser launched but debugging port did not respond in time."
        except Exception as e:
            return False, f"Failed to launch browser: {e}"

    def _get_whatsapp_tab_ws_url(self) -> Optional[str]:
        """Finds or creates the WhatsApp Web tab and returns its WebSocket debugger URL."""
        try:
            r = requests.get(f"http://127.0.0.1:{self.port}/json", timeout=2.5)
            tabs = r.json()
            # 1. Look for existing WhatsApp tab
            for tab in tabs:
                url = tab.get("url", "")
                if "web.whatsapp.com" in url:
                    return tab.get("webSocketDebuggerUrl")

            # 2. Look for an about:blank or normal page tab to navigate
            for tab in tabs:
                if tab.get("type") == "page":
                    ws = tab.get("webSocketDebuggerUrl")
                    if ws:
                        # Navigate this tab to WhatsApp Web
                        self._send_cdp_command_sync(ws, "Page.navigate", {"url": "https://web.whatsapp.com"})
                        time.sleep(2)
                        return ws

            # 3. Create a new tab via CDP
            r_new = requests.put(f"http://127.0.0.1:{self.port}/json/new?https://web.whatsapp.com", timeout=3.0)
            if r_new.status_code == 200:
                tab_data = r_new.json()
                return tab_data.get("webSocketDebuggerUrl")
        except Exception as e:
            logger.error(f"[WhatsApp] Failed to query CDP tabs: {e}")
        return None

    def _send_cdp_command_sync(self, ws_url: str, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Any:
        """Sends a single CDP JSON-RPC command synchronously over WebSocket."""
        async def _async_call():
            async with websockets.connect(ws_url, ping_interval=None) as ws:
                msg_id = int(time.time() * 1000) % 1000000
                payload = {"id": msg_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    resp_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    resp = json.loads(resp_raw)
                    if resp.get("id") == msg_id:
                        if "error" in resp:
                            raise RuntimeError(resp["error"].get("message", "Unknown CDP error"))
                        return resp.get("result", {})

        return asyncio.run(_async_call())

    def eval_js(self, js_expr: str, timeout: float = 10.0) -> Any:
        """Evaluates JavaScript expression in WhatsApp Web tab and returns value."""
        ws_url = self._get_whatsapp_tab_ws_url()
        if not ws_url:
            raise RuntimeError("WhatsApp Web tab is not available.")
        
        result = self._send_cdp_command_sync(
            ws_url,
            "Runtime.evaluate",
            {
                "expression": js_expr,
                "returnByValue": True,
                "awaitPromise": True
            },
            timeout=timeout
        )
        val_obj = result.get("result", {})
        return val_obj.get("value")

    def check_status(self) -> Tuple[str, str]:
        """
        Inspects WhatsApp Web DOM to determine whether:
        - Browser is not running
        - Loading chats
        - Awaiting QR code scan
        - Logged in & ready
        """
        if not self.is_browser_cdp_available():
            self.set_status(STATUS_DISCONNECTED, "WhatsApp Web is not running.")
            return STATUS_DISCONNECTED, "WhatsApp Web browser is not running."

        ws_url = self._get_whatsapp_tab_ws_url()
        if not ws_url:
            self.set_status(STATUS_DISCONNECTED, "WhatsApp Web tab not found.")
            return STATUS_DISCONNECTED, "WhatsApp Web tab not found."

        # JavaScript query to inspect current WhatsApp Web state
        js_probe = """
        (() => {
            // Check for logged in elements (chat list pane)
            const chatList = document.querySelector('div#pane-side') || 
                             document.querySelector('[aria-label="Chat list"]') ||
                             document.querySelector('[data-testid="chat-list"]');
            if (chatList) {
                return { state: "LOGGED_IN" };
            }

            // Check for QR code canvas or container
            const qrCanvas = document.querySelector('canvas[aria-label*="Scan"]') ||
                             document.querySelector('div[data-testid="qrcode"]') ||
                             document.querySelector('div[data-ref]') ||
                             document.querySelector('canvas');
            const qrHeader = document.querySelector('h1') || document.querySelector('div');
            const hasQrText = document.body.innerText.includes("To use WhatsApp on your computer") ||
                              document.body.innerText.includes("Link with phone number") ||
                              document.body.innerText.includes("Scan this code");
            if (qrCanvas || hasQrText) {
                return { state: "QR_REQUIRED" };
            }

            // Check for loading / starting screen
            const hasLoading = document.querySelector('progress') ||
                               document.querySelector('[data-testid="startup-progress"]') ||
                               document.body.innerText.includes("Loading your chats") ||
                               document.body.innerText.includes("Starting chat");
            if (hasLoading) {
                return { state: "LOADING" };
            }

            return { state: "UNKNOWN" };
        })()
        """
        try:
            res = self.eval_js(js_probe, timeout=5.0)
            state = res.get("state") if isinstance(res, dict) else "UNKNOWN"
            if state == "LOGGED_IN":
                self.set_status(STATUS_CONNECTED, "WhatsApp Web is logged in and ready.")
                return STATUS_CONNECTED, "WhatsApp Web is logged in and ready."
            elif state == "QR_REQUIRED":
                self.set_status(STATUS_AWAITING_QR, "Please scan the QR code on your phone to link WhatsApp Web.")
                return STATUS_AWAITING_QR, "Scan QR code manually on your phone to continue."
            elif state == "LOADING":
                self.set_status(STATUS_CONNECTING, "WhatsApp Web is loading chats...")
                return STATUS_CONNECTING, "Loading chats, please wait a moment."
            else:
                self.set_status(STATUS_CONNECTING, "WhatsApp Web is loading...")
                return STATUS_CONNECTING, "WhatsApp Web page is loading."
        except Exception as e:
            self.set_status(STATUS_FAILED, f"Error inspecting status: {e}")
            return STATUS_FAILED, str(e)

    def open_whatsapp_web(self) -> Tuple[bool, str]:
        """Opens WhatsApp Web in default browser and reports login status."""
        self.set_status(STATUS_CONNECTING, "Opening WhatsApp Web...")
        ok, msg = self.launch_browser()
        if not ok:
            self.set_status(STATUS_FAILED, msg)
            return False, msg

        # Wait up to 15 seconds for initial state to settle
        for _ in range(15):
            time.sleep(1.0)
            status, desc = self.check_status()
            if status == STATUS_CONNECTED:
                return True, "WhatsApp Web is connected and ready boss!"
            elif status == STATUS_AWAITING_QR:
                return True, "WhatsApp Web open ho gaya hai boss. Please apne phone se QR code scan kar lijiye!"
        
        status, desc = self.check_status()
        if status in [STATUS_CONNECTED, STATUS_AWAITING_QR]:
            return True, desc
        return True, "WhatsApp Web open kar diya hai boss. Check status on screen."

    def search_and_select_contact(self, contact_name_or_number: str) -> Tuple[bool, str, List[str]]:
        """
        Searches for contact in WhatsApp Web.
        If a pure phone number is provided, navigates directly via https://web.whatsapp.com/send?phone=...
        If a name is provided, uses WhatsApp search bar.
        Returns (success, message, matched_contacts_list).
        """
        status, _ = self.check_status()
        if status != STATUS_CONNECTED:
            return False, "WhatsApp Web is not logged in. Please scan QR code first.", []

        query = contact_name_or_number.strip()
        # Check if query is a phone number (e.g. +919876543210 or 9876543210)
        digits_only = re_digits = "".join(filter(str.isdigit, query))
        if len(digits_only) >= 10 and (query.startswith("+") or len(digits_only) in [10, 11, 12]):
            phone_num = digits_only if digits_only.startswith("91") or len(digits_only) > 10 else f"91{digits_only}"
            ws_url = self._get_whatsapp_tab_ws_url()
            url = f"https://web.whatsapp.com/send?phone={phone_num}"
            self._send_cdp_command_sync(ws_url, "Page.navigate", {"url": url})
            self.set_status(STATUS_SEARCHING_CONTACT, f"Opening chat with phone: +{phone_num}")
            
            # Wait for chat pane or message box to load
            time.sleep(3)
            for _ in range(8):
                js_chk = """
                (() => {
                    const msgBox = document.querySelector('footer div[contenteditable="true"]') ||
                                   document.querySelector('div[contenteditable="true"][data-tab="10"]');
                    const invalidPhone = document.body.innerText.includes("Phone number shared via url is invalid");
                    if (invalidPhone) return "INVALID_PHONE";
                    if (msgBox) return "READY";
                    return "WAIT";
                })()
                """
                res = self.eval_js(js_chk)
                if res == "READY":
                    return True, f"Chat opened for +{phone_num}", [f"+{phone_num}"]
                elif res == "INVALID_PHONE":
                    return False, f"Phone number +{phone_num} is not registered on WhatsApp.", []
                time.sleep(1)
            return True, f"Navigated to chat with +{phone_num}", [f"+{phone_num}"]

        # Otherwise search contact by name in the search bar
        self.set_status(STATUS_SEARCHING_CONTACT, f"Searching for '{query}' in WhatsApp contacts...")
        js_search = f"""
        (async () => {{
            // 1. Locate search box
            const searchBox = document.querySelector('div[contenteditable="true"][data-tab="3"]') ||
                              document.querySelector('div[role="textbox"][title*="Search"]') ||
                              document.querySelector('div[role="textbox"]');
            if (!searchBox) {{
                return {{ error: "Search box not found in WhatsApp Web." }};
            }}

            searchBox.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            document.execCommand('insertText', false, {json.dumps(query)});
            searchBox.dispatchEvent(new InputEvent('input', {{ bubbles: true }}));

            await new Promise(r => setTimeout(r, 1200));

            // Extract matching contact titles from search results
            const matches = [];
            const chatList = document.querySelector('div#pane-side') || document.body;
            const items = chatList.querySelectorAll('div[role="listitem"] span[title], div[role="listitem"] span[dir="auto"]');
            const seen = new Set();
            for (const el of items) {{
                const title = el.getAttribute('title') || el.innerText;
                if (title && title.trim().length > 0 && !seen.has(title.trim())) {{
                    const t = title.trim();
                    // Exclude generic UI labels
                    if (!['Chats', 'Search', 'New chat', 'Status'].includes(t)) {{
                        seen.add(t);
                        matches.push(t);
                    }}
                }}
            }}
            return {{ matches: matches.slice(0, 8) }};
        }})()
        """
        try:
            res = self.eval_js(js_search, timeout=8.0)
            if not isinstance(res, dict):
                return False, "Failed to execute contact search.", []
            if "error" in res:
                return False, res["error"], []
            
            matches = res.get("matches", [])
            # Filter matches containing search token
            filtered = [m for m in matches if query.lower() in m.lower()]
            final_matches = filtered if filtered else matches

            if not final_matches:
                return False, f"WhatsApp contacts mein '{query}' nahi mila boss.", []
            
            if len(final_matches) > 1:
                # If exact case-insensitive match exists among them, select it
                exact = [m for m in final_matches if m.lower() == query.lower()]
                if len(exact) == 1:
                    self._click_contact_item(exact[0])
                    return True, f"Contact '{exact[0]}' selected.", [exact[0]]
                # Otherwise return multiple matches for user disambiguation
                return False, f"Multiple contacts match '{query}'", final_matches
            
            # Single match found! Click it to open chat
            chosen = final_matches[0]
            self._click_contact_item(chosen)
            return True, f"Contact '{chosen}' selected.", [chosen]
        except Exception as e:
            return False, f"Contact search failed: {e}", []

    def _click_contact_item(self, contact_name: str):
        """Clicks on the contact in the search list to open conversation."""
        js_click = f"""
        (() => {{
            const items = document.querySelectorAll('div[role="listitem"]');
            for (const item of items) {{
                if (item.innerText.toLowerCase().includes({json.dumps(contact_name.lower())})) {{
                    item.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
        self.eval_js(js_click)
        time.sleep(1.2)

    def prepare_text_message(self, recipient: str, message_text: str) -> Tuple[bool, str]:
        """
        Navigates to the recipient's chat and types the text message into the input field.
        Awaits explicit confirmation before sending.
        """
        ok, res_msg, matches = self.search_and_select_contact(recipient)
        if not ok:
            return False, res_msg

        resolved_recipient = matches[0] if matches else recipient
        self.set_status(STATUS_AWAITING_CONFIRMATION, f"Ready to send to {resolved_recipient}: '{message_text}'")

        # Draft message text into WhatsApp message box
        js_type = f"""
        (() => {{
            const msgBox = document.querySelector('footer div[contenteditable="true"]') ||
                           document.querySelector('div[contenteditable="true"][data-tab="10"]');
            if (!msgBox) return false;
            msgBox.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            document.execCommand('insertText', false, {json.dumps(message_text)});
            msgBox.dispatchEvent(new InputEvent('input', {{ bubbles: true }}));
            return true;
        }})()
        """
        self.eval_js(js_type)

        self._pending_action = {
            "type": "text",
            "recipient": resolved_recipient,
            "message": message_text
        }
        return True, f"Message prepared for {resolved_recipient}. Awaiting confirmation."

    def prepare_file_attachment(self, recipient: str, file_path: str, attachment_type: str = "document") -> Tuple[bool, str]:
        """
        Locates the verified file, selects contact, and uploads file via WhatsApp attachment input.
        Awaits explicit confirmation before sending.
        """
        target = Path(file_path).resolve()
        if not target.exists():
            return False, f"File does not exist: {file_path}"
        if not os.access(str(target), os.R_OK):
            return False, f"File is not readable: {file_path}"

        ok, res_msg, matches = self.search_and_select_contact(recipient)
        if not ok:
            return False, res_msg

        resolved_recipient = matches[0] if matches else recipient
        self.set_status(STATUS_PREPARING_ATTACHMENT, f"Attaching {target.name} for {resolved_recipient}...")

        ws_url = self._get_whatsapp_tab_ws_url()
        if not ws_url:
            return False, "WhatsApp Web tab not accessible."

        # Click the attachment '+' icon to expose file inputs
        js_open_attach = """
        (() => {
            const plusBtn = document.querySelector('button[data-testid="attach-menu-plus"]') ||
                            document.querySelector('span[data-icon="plus"]') ||
                            document.querySelector('span[data-icon="attach-menu-plus"]') ||
                            document.querySelector('button[title="Attach"]');
            if (plusBtn) {
                plusBtn.click();
                return true;
            }
            return false;
        })()
        """
        self.eval_js(js_open_attach)
        time.sleep(1.0)

        # Upload file directly using CDP DOM.setFileInputFiles
        try:
            # Query the file input element in WhatsApp Web DOM
            accept_filter = "image" if attachment_type == "image" else "*"
            node_query_js = f"""
            (() => {{
                const inputs = Array.from(document.querySelectorAll('input[type="file"]'));
                if (inputs.length === 0) return null;
                // Find matching input by accept attribute
                for (let i = inputs.length - 1; i >= 0; i--) {{
                    const acc = inputs[i].getAttribute('accept') || '';
                    if ('{accept_filter}' === 'image' && acc.includes('image')) return inputs[i];
                    if ('{accept_filter}' !== 'image' && (acc.includes('*') || acc.includes('pdf') || acc === '')) return inputs[i];
                }}
                return inputs[inputs.length - 1];
            }})()
            """
            # Obtain root document node
            doc_res = self._send_cdp_command_sync(ws_url, "DOM.getDocument")
            root_node_id = doc_res["root"]["nodeId"]

            # Query input selector
            selector = 'input[type="file"][accept*="image"]' if attachment_type == "image" else 'input[type="file"]'
            q_res = self._send_cdp_command_sync(ws_url, "DOM.querySelector", {
                "nodeId": root_node_id,
                "selector": selector
            })
            input_node_id = q_res.get("nodeId")

            if not input_node_id or input_node_id == 0:
                # Fallback to any input[type="file"]
                q_res = self._send_cdp_command_sync(ws_url, "DOM.querySelector", {
                    "nodeId": root_node_id,
                    "selector": 'input[type="file"]'
                })
                input_node_id = q_res.get("nodeId")

            if not input_node_id or input_node_id == 0:
                return False, "WhatsApp Web file upload input could not be accessed."

            # Set file input
            self._send_cdp_command_sync(ws_url, "DOM.setFileInputFiles", {
                "files": [str(target)],
                "nodeId": input_node_id
            })

            # Wait 2 seconds for preview modal to display
            time.sleep(2.0)

            self.set_status(STATUS_AWAITING_CONFIRMATION, f"Ready to send {target.name} to {resolved_recipient}")
            self._pending_action = {
                "type": "file",
                "recipient": resolved_recipient,
                "file_path": str(target),
                "filename": target.name,
                "attachment_type": attachment_type
            }
            return True, f"Attached {target.name} for {resolved_recipient}. Awaiting confirmation."
        except Exception as e:
            self.set_status(STATUS_FAILED, f"Failed to attach file: {e}")
            return False, f"Failed to attach file: {e}"

    def send_confirmed_action(self) -> Tuple[bool, str]:
        """
        Executes the pending send action after explicit user confirmation.
        Verifies that send succeeded by inspecting DOM state.
        """
        if not self._pending_action:
            return False, "Boss, koi pending WhatsApp message ya file bhejane ke liye nahi hai!"

        action = self._pending_action
        action_type = action.get("type")
        recipient = action.get("recipient", "contact")
        self.set_status(STATUS_SENDING, f"Sending to {recipient}...")

        js_send = """
        (() => {
            // Check for media preview send button first (large green circular send button)
            const mediaSendBtn = document.querySelector('div[aria-label="Send"]') ||
                                 document.querySelector('span[data-icon="send"]') ||
                                 document.querySelector('[data-testid="send"]');
            if (mediaSendBtn) {
                // Click parent button if clickable
                const btn = mediaSendBtn.closest('button') || mediaSendBtn.closest('div[role="button"]') || mediaSendBtn;
                btn.click();
                return { success: true, method: "media_button" };
            }

            // Normal text send button
            const sendBtn = document.querySelector('button[data-testid="compose-btn-send"]') ||
                            document.querySelector('button[aria-label="Send"]');
            if (sendBtn) {
                sendBtn.click();
                return { success: true, method: "text_button" };
            }

            // Fallback: press Enter on message box
            const msgBox = document.querySelector('footer div[contenteditable="true"]') ||
                           document.querySelector('div[contenteditable="true"][data-tab="10"]');
            if (msgBox) {
                msgBox.focus();
                const enterEvent = new KeyboardEvent('keydown', {
                    bubbles: true,
                    cancelable: true,
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13
                });
                msgBox.dispatchEvent(enterEvent);
                return { success: true, method: "enter_key" };
            }

            return { success: false, error: "Send button not found." };
        })()
        """
        try:
            res = self.eval_js(js_send, timeout=5.0)
            if not isinstance(res, dict) or not res.get("success"):
                err = res.get("error", "Unknown error") if isinstance(res, dict) else "Execution failed"
                self.set_status(STATUS_FAILED, f"Send action failed: {err}")
                return False, f"Message send button nahi mila: {err}"

            # Verification step: Wait and check that input box is emptied or modal closed
            time.sleep(2.0)
            verify_js = """
            (() => {
                // Media preview modal should be gone
                const previewModal = document.querySelector('div[aria-label="Send"]') ||
                                     document.querySelector('[data-testid="media-caption-input"]');
                if (previewModal) return "PREVIEW_STILL_OPEN";

                // Message box should be cleared
                const msgBox = document.querySelector('footer div[contenteditable="true"]');
                if (msgBox && msgBox.innerText.trim().length === 0) {
                    return "VERIFIED_SENT";
                }
                return "DISPATCHED";
            })()
            """
            v_status = self.eval_js(verify_js, timeout=4.0)
            self._pending_action = None

            if v_status in ["VERIFIED_SENT", "DISPATCHED"]:
                success_msg = (
                    f"Message '{action.get('message')}' successfully sent to {recipient}!"
                    if action_type == "text"
                    else f"File '{action.get('filename')}' successfully sent to {recipient}!"
                )
                self.set_status(STATUS_SUCCESS, success_msg)
                return True, success_msg
            else:
                warn_msg = f"Send command executed, but outcome verification is uncertain for {recipient}. Please check WhatsApp Web window."
                self.set_status(STATUS_FAILED, warn_msg)
                return False, warn_msg
        except Exception as e:
            self._pending_action = None
            self.set_status(STATUS_FAILED, f"Error sending: {e}")
            return False, f"Send action error: {e}"

    def cancel_pending(self) -> Tuple[bool, str]:
        """Cancels any pending unconfirmed message or attachment and clears UI state."""
        if not self._pending_action:
            self.set_status(STATUS_CONNECTED, "No pending message to cancel.")
            return True, "Koi pending WhatsApp task nahi tha boss!"

        action = self._pending_action
        self._pending_action = None

        # Clean draft from WhatsApp Web UI
        js_clear = """
        (() => {
            // If media modal open, click cancel / close (X button)
            const closeBtn = document.querySelector('span[data-icon="x"]') ||
                             document.querySelector('button[aria-label="Close"]');
            if (closeBtn) closeBtn.click();

            // Clear text box
            const msgBox = document.querySelector('footer div[contenteditable="true"]');
            if (msgBox) {
                msgBox.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);
            }
        })()
        """
        try:
            self.eval_js(js_clear, timeout=2.0)
        except Exception:
            pass

        self.set_status(STATUS_CONNECTED, "Pending WhatsApp send cancelled.")
        target_name = action.get("recipient", "contact")
        return True, f"Theek hai boss! {target_name} ko bhejane wala task cancel kar diya hai."

    def get_pending_details(self) -> Optional[Dict[str, Any]]:
        return self._pending_action
