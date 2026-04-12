import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.action_executor import execute_action

def test_actions():
    print("--- Testing Action Executor Enhancement ---")
    
    # 1. Test direct open_url
    print("\n[1] Testing open_url (Google)...")
    res1 = execute_action({"action": "open_url", "target": "google.com"})
    print(f"Result: {json.dumps(res1, indent=2)}")
    
    # 2. Test smart open_app (YouTube redirect)
    print("\n[2] Testing smart open_app (YouTube)...")
    res2 = execute_action({"action": "open_app", "target": "youtube"})
    print(f"Result: {json.dumps(res2, indent=2)}")
    
    # 3. Test open_app for Notepad
    print("\n[3] Testing open_app (Notepad)...")
    res3 = execute_action({"action": "open_app", "target": "notepad"})
    print(f"Result: {json.dumps(res3, indent=2)}")

if __name__ == "__main__":
    test_actions()
