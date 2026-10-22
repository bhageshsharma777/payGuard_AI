
import os
import requests
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("PAYPAL_CLIENT_ID")
client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
base_url = os.getenv("PAYPAL_BASE_URL")

if not client_id or not client_secret:
    raise ValueError("Missing PayPal credentials in .env")

response = requests.post(
    f"{base_url}/v1/oauth2/token",
    auth=(client_id, client_secret),
    headers={"Accept": "application/json"},
    data={"grant_type": "client_credentials"},
    timeout=30,
)

if response.ok:
    data = response.json()
    print("PayPal Sandbox connected successfully!")
    print("Token type:", data.get("token_type"))
    print("Expires in:", data.get("expires_in"), "seconds")
else:
    print("PayPal authentication failed.")
    print("Status:", response.status_code)
    print("Response:", response.text)
