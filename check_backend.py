#!/usr/bin/env python3
"""
Check if the backend server is running and accessible.
"""

import requests
import sys

def check_backend():
    """Check if backend is running"""
    try:
        # Try to connect to the backend
        response = requests.get("http://10.31.167.254:5000/api/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ Backend is running and accessible!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Backend responded with status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server")
        print("   Make sure the backend is running on http://10.31.167.254:5000")
        print("   Start it with: python app.py")
        return False
    except requests.exceptions.Timeout:
        print("❌ Backend connection timed out")
        return False
    except Exception as e:
        print(f"❌ Error checking backend: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Checking Backend Server...")
    print("=" * 40)
    
    if check_backend():
        print("\n✅ Backend is ready for the mobile app!")
    else:
        print("\n❌ Backend is not accessible. Please start it first.")
        sys.exit(1)

