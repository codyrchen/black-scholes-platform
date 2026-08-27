#!/usr/bin/env python3
"""
Quick test script to verify the Flask backend is running and accessible
"""
import requests
import sys
import os

def test_backend():
    base = os.getenv("BACKEND_URL", "http://localhost:5001")
    url = f"{base}/api/health"
    print(f"Testing backend connection at {url}...")
    print("-" * 50)
    
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            print("✅ SUCCESS: Backend is running and accessible!")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ ERROR: Backend responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to backend")
        print("   The Flask server is not running or not accessible.")
        print("\n   To start the server, run:")
        print("   python3 app.py")
        return False
    except requests.exceptions.Timeout:
        print("❌ ERROR: Connection timeout")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_backend()
    sys.exit(0 if success else 1)
