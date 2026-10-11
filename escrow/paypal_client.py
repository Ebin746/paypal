import os
import uuid
import httpx
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
BASE_URL = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")


class PayPalClient:
    def __init__(self):
        self.access_token = None

    async def get_access_token(self) -> str:
        """Fetch OAuth2 token using client credentials."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{BASE_URL}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(CLIENT_ID, CLIENT_SECRET),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if res.status_code != 200:
                raise RuntimeError(f"PayPal Auth Failed ({res.status_code}): {res.text}")
            data = res.json()
            self.access_token = data["access_token"]
            return self.access_token

    async def create_authorization_order(self, amount: float, currency="USD") -> dict:
        """Pre-authorizes / locks agent reward funds."""
        token = await self.get_access_token()
        payload = {
            "intent": "AUTHORIZE",
            "purchase_units": [
                {
                    "reference_id": str(uuid.uuid4()),
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}",
                    },
                }
            ],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{BASE_URL}/v2/checkout/orders",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            if res.status_code not in (200, 201):
                raise RuntimeError(f"PayPal Order Failed ({res.status_code}): {res.text}")
            return res.json()

    async def disburse_payout(
        self, worker_email: str, amount: float, note: str = "GroundBounty reward"
    ) -> dict:
        """Instant micro-payout to human worker via PayPal Payouts API."""
        token = await self.get_access_token()
        batch_id = f"GB-{uuid.uuid4().hex[:10]}"
        payload = {
            "sender_batch_header": {
                "sender_batch_id": batch_id,
                "email_subject": "You received a GroundBounty Payout!",
                "recipient_type": "EMAIL",
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {"value": f"{amount:.2f}", "currency": "USD"},
                    "receiver": worker_email,
                    "note": note,
                    "sender_item_id": f"item-{uuid.uuid4().hex[:6]}",
                }
            ],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{BASE_URL}/v1/payments/payouts",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            if res.status_code not in (200, 201):
                raise RuntimeError(f"PayPal Payout Failed ({res.status_code}): {res.text}")
            return res.json()