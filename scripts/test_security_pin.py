import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.security import (
    get_power_password,
    verify_power_password,
    set_power_password,
    extract_pin_from_text,
    set_pending_power_action,
    get_pending_power_action,
    clear_pending_power_action
)
from tools.system_tools import shutdown_system, restart_system, sleep_system, hibernate_system, change_power_pin
from core.brain import brain

def test_security_pin_flow():
    print("==================================================")
    print("       TESTING POWER PIN & SECURITY AUTHENTICATION ")
    print("==================================================")

    # 1. Test default PIN retrieval
    pin = get_power_password()
    print(f"1. Current Power PIN: '{pin}'")
    assert pin in ("2206",), f"Expected default PIN 2206, got '{pin}'"
    print(">> [PASS] Default PIN verified!")

    # 2. Test PIN Verification
    assert verify_power_password("2206") is True, "Expected '2206' to be valid!"
    assert verify_power_password("9999") is False, "Expected '9999' to be invalid!"
    print(">> [PASS] PIN validation logic verified!")

    # 3. Test Direct Tools without PIN (must be blocked)
    res_shutdown = shutdown_system(delay_seconds=5)
    print(f"3a. Direct shutdown response: {res_shutdown}")
    assert "Authentication required" in res_shutdown or "PIN" in res_shutdown

    res_sleep = sleep_system()
    print(f"3b. Direct sleep response: {res_sleep}")
    assert "Authentication required" in res_sleep or "PIN" in res_sleep
    print(">> [PASS] Direct unauthenticated tool calls safely blocked!")

    # 4. Test Multi-Turn Brain Query Flow
    print("\n--- Testing Multi-Turn Authentication in Brain ---")
    session_id = "test_auth_session"
    clear_pending_power_action(session_id)

    # Turn 1: User asks to put laptop to sleep
    t1_reply = brain.query("Wednesday, put my laptop to sleep", session_id=session_id)
    print(f"User: 'Wednesday, put my laptop to sleep'")
    print(f"Wednesday: '{t1_reply}'")
    assert "PIN" in t1_reply or "security" in t1_reply or "Authentication" in t1_reply
    assert get_pending_power_action(session_id) is not None
    print(">> [PASS] Turn 1 prompted for PIN and stored pending action!")

    # Turn 2: User provides wrong PIN
    t2_wrong_reply = brain.query("0000", session_id=session_id)
    print(f"User (wrong PIN): '0000'")
    print(f"Wednesday: '{t2_wrong_reply}'")
    assert "failed" in t2_wrong_reply.lower() or "incorrect" in t2_wrong_reply.lower()

    # Turn 3: User asks to shutdown, then provides correct PIN 2206
    t3_reply = brain.query("Wednesday, shutdown my computer", session_id=session_id)
    print(f"\nUser: 'Wednesday, shutdown my computer'")
    print(f"Wednesday: '{t3_reply}'")
    assert "PIN" in t3_reply or "security" in t3_reply

    t4_correct_reply = brain.query("2206", session_id=session_id)
    print(f"User: '2206'")
    print(f"Wednesday: '{t4_correct_reply}'")
    assert "PIN verified" in t4_correct_reply or "Shutting down" in t4_correct_reply
    print(">> [PASS] Turn 2 verified correct PIN and executed pending action!")

    # 5. Test Inline Authenticated Command
    print("\n--- Testing Inline Authenticated Command ---")
    inline_reply = brain.query("shutdown PC with password 2206", session_id="test_inline")
    print(f"User: 'shutdown PC with password 2206'")
    print(f"Wednesday: '{inline_reply}'")
    assert "PIN verified" in inline_reply
    print(">> [PASS] Inline authenticated command passed!")

    # 6. Test PIN Update
    print("\n--- Testing PIN Change Feature ---")
    ok, msg = set_power_password("2206", "9876")
    print(f"Change PIN response: {msg}")
    assert ok is True
    assert get_power_password() == "9876"
    assert verify_power_password("9876") is True
    assert verify_power_password("2206") is False

    # Test conversational PIN change
    conv_change = brain.query("change power pin from 9876 to 2206", session_id="test_change")
    print(f"Conversational change response: {conv_change}")
    assert "successfully updated" in conv_change.lower()
    assert get_power_password() == "2206"
    print(">> [PASS] PIN update feature fully verified!")

    # Cancel any scheduled shutdown test calls
    from tools.system_tools import cancel_shutdown
    cancel_shutdown()

    print("\n==================================================")
    print("   ALL SECURITY PIN & POWER AUTH TESTS PASSED!    ")
    print("==================================================")

if __name__ == "__main__":
    test_security_pin_flow()
