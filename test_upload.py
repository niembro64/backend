#!/usr/bin/env python3
"""
Test script to verify upload size limits are working properly
"""

import requests
import os
import tempfile

def test_upload_limits():
    # Create a test file of specific size
    test_file_size = 1024 * 1024  # 1MB for testing
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
        # Write 1MB of data
        temp_file.write(b'A' * test_file_size)
        temp_file_path = temp_file.name
    
    try:
        # Test the upload
        with open(temp_file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post('http://localhost:8000/api/media/analyze/', files=files)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Upload successful!")
        elif response.status_code == 413:
            print("❌ File too large (413 error)")
        else:
            print(f"❌ Unexpected error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    finally:
        # Clean up
        os.unlink(temp_file_path)

if __name__ == "__main__":
    print("Testing upload limits...")
    test_upload_limits()