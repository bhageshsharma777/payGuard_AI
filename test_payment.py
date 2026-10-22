
import os
import requests
import webbrowser
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
BASE_URL = os.getenv(
    "PAYPAL_BASE_URL",
    "https://api-m.sandbox.paypal.com"
)


def get_access_token():
    response = requests.post(
        f"{BASE_URL}/v1/oauth2/token",
        auth=(CLIENT_ID, CLIENT_SECRET),
        headers={"Accept": "application/json"},
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: PayPal credentials missing from .env")
        return

    try:
        token = get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # 1. Create a $10 USD Sandbox order
        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "description": "PayGuard AI Sandbox Test",
                    "amount": {
                        "currency_code": "USD",
                        "value": "10.00",
                    },
                }
            ],
            "application_context": {
                "brand_name": "PayGuard AI",
                "user_action": "PAY_NOW",
                "return_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            },
        }

        response = requests.post(
            f"{BASE_URL}/v2/checkout/orders",
            headers=headers,
            json=order_data,
            timeout=30,
        )
        response.raise_for_status()
        order = response.json()

        order_id = order["id"]
        for unit in order.get("purchase_units", []):
            payee = unit.get("payee", {})
            print("Seller merchant ID:", payee.get("merchant_id"))
            print("Seller email:", payee.get("email_address"))
        approve_url = next(
            (
                link["href"]
                for link in order.get("links", [])
                if link.get("rel") in ("approve", "payer-action")
            ),
            None,
        )

        print("\nOrder created successfully!")
        print("Order ID:", order_id)
        print("Amount: $10.00 USD")

        if not approve_url:
            print("No approval URL returned by PayPal.")
            print(order)
            return

        print("\nOpening PayPal Sandbox checkout...")
        print("Approval URL:", approve_url)
        webbrowser.open(approve_url)

        input(
            "\nLog in with your Sandbox PERSONAL buyer account, "
            "approve the $10 test payment, and then return here. "
            "Press Enter to capture the order..."
        )

        # 2. Capture after buyer approval
        capture_response = requests.post(
            f"{BASE_URL}/v2/checkout/orders/"
            f"{order_id}/capture",
            headers=headers,
            json={},
            timeout=30,
        )

        if not capture_response.ok:
            print("\nCapture failed.")
            print("Status:", capture_response.status_code)
            print(capture_response.text)
            print("Check that the buyer approved this order.")
            return

        result = capture_response.json()

        print("\nCapture response status:", result.get("status"))
        print("Order ID:", result.get("id"))

        if result.get("status") == "COMPLETED":
            print("SUCCESS: Sandbox payment captured!")

            for unit in result.get("purchase_units", []):
                for capture in unit.get(
                    "payments", {}
                ).get("captures", []):
                    print("Capture ID:", capture.get("id"))
                    print("Capture status:", capture.get("status"))
                    print(
                        "Captured amount:",
                        capture.get("amount", {}).get("value"),
                        capture.get("amount", {}).get("currency_code"),
                    )
        else:
            print("Payment is not completed. Check the response above.")

    except requests.RequestException as error:
        print("\nPayPal API request failed:", error)
        if getattr(error, "response", None) is not None:
            print(error.response.text)
    except (KeyError, StopIteration) as error:
        print("\nUnexpected PayPal response:", error)


if __name__ == "__main__":
    main()
