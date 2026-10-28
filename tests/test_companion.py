import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.companion_parser import CompanionCallParser
from core.brain import JarvisBrain

def run_tests():
    print("--- 1. Testing CompanionCallParser ---")
    queries = [
        "Jarvis, mummy ko call lagao",
        "mummy ko call lagao",
        "papa ko phone lagao",
        "call lagao mummy ko",
        "call mummy",
        "make a call to Aman room on my realme phone",
        "phone status kya hai",
        "Jarvis phone status"
    ]
    for q in queries:
        parsed = CompanionCallParser.parse(q)
        print(f"  '{q}' -> {parsed}")
        assert parsed is not None, f"Failed to parse query: {q}"

    # Verify recipient extraction
    assert CompanionCallParser.parse("make a call to Aman room on my realme phone")["recipient"] == "aman room"
    assert CompanionCallParser.parse("Jarvis, mummy ko call lagao")["recipient"] == "mummy"

    print("\n--- 2. Testing JarvisBrain Phone Calling Workflow ---")
    brain = JarvisBrain()

    # Case A: Disconnected Phone
    resp_disc = brain.process_command("Jarvis, mummy ko call lagao")
    print(f"  [Disconnected state] -> {resp_disc}")
    assert "Realme 10 Pro" in resp_disc or "connected nahi hai" in resp_disc

    # Case B: Connected Phone
    class MockWebSocket:
        def __init__(self):
            self.remote_address = ("10.96.127.200", 50000)

    brain.companion_mgr.status = "CONNECTED"
    brain.companion_mgr._active_ws = MockWebSocket()
    brain.companion_mgr.connected_device_info = {"device": "Realme 10 Pro"}

    # Mock contact search returning Mummy's number
    def mock_search(query, timeout=5.0):
        if "mummy" in query.lower():
            return [{"name": "Mummy", "number": "+91 98765 43210"}]
        if "aman" in query.lower():
            return [{"name": "Aman Room", "number": "+91 91234 56789"}]
        return []

    brain.companion_mgr.search_contact = mock_search

    call_executed = []
    def mock_make_call(number, name, timeout=6.0):
        call_executed.append((number, name))
        return True, f"Dialing {name}"

    brain.companion_mgr.make_call = mock_make_call

    # Trigger call command - Direct 1-Shot Calling
    call_resp = brain.process_command("Jarvis, mummy ko call lagao")
    print(f"  [1-Shot Command Response] -> {call_resp}")
    assert "Calling Mummy (+91 98765 43210) on your Realme phone now, boss!" in call_resp
    assert len(call_executed) == 1
    assert call_executed[0] == ("+91 98765 43210", "Mummy")

    # Direct 1-Shot Calling for "make a call to Aman room on my realme phone"
    call_resp_2 = brain.process_command("make a call to Aman room on my realme phone")
    print(f"  [1-Shot Command Response 2] -> {call_resp_2}")
    assert "Calling Aman Room (+91 91234 56789) on your Realme phone now, boss!" in call_resp_2
    assert len(call_executed) == 2
    assert call_executed[1] == ("+91 91234 56789", "Aman Room")

    print("\nALL COMPANION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
