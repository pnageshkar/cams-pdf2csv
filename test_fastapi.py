import requests
import sys
import json


def test_api():
    url = "http://localhost:8000/parse-pdf"
    pdf_path = "CAS_0226.pdf"
    password = sys.argv[1] if len(sys.argv) > 1 else ""

    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path, f, "application/pdf")}
        data = {"password": password}

        try:
            print("Sending request to FastAPI...")
            response = requests.post(url, files=files, data=data)

            if response.status_code == 200:
                result = response.json()
                print(f"Success! Message: {result['message']}")
                print(f"Extracted {len(result['transactions'])} transactions.")
                # Print the first transaction nicely to verify JSON serialization
                print("\nFirst transaction JSON:")
                print(json.dumps(result["transactions"][0], indent=2))
            else:
                print(f"Failed with status {response.status_code}")
                print(response.text)
        except requests.exceptions.ConnectionError:
            print(
                "Error: Could not connect to API. Make sure uvicorn is running on port 8000."
            )


if __name__ == "__main__":
    test_api()
