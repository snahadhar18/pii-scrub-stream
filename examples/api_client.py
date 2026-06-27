"""
API Client Example.
Demonstrates how to send requests to the RedactAI Gateway API.
Ensure the API is running first: `redactai-gateway serve --port 8000`
"""
import urllib.request
import urllib.error
import json

def main() -> None:
    url = "http://localhost:8000/scan"
    payload = {
        "text": "My phone number is 555-0199 and my email is test@example.com.",
        "detectors": ["email", "phone"],
        "redact": True,
        "mask": False
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print("Successfully connected to RedactAI API:")
            print(json.dumps(result, indent=2))
    except urllib.error.URLError as e:
        print(f"Failed to connect to the API: {e}")
        print("Did you start it using 'redactai-gateway serve'?")

if __name__ == "__main__":
    main()
