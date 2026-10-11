from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel
from paypal_client import PayPalClient


class EscrowRecord(BaseModel):
    bounty_id: str
    reward_usd: float
    description: str
    paypal_order_id: Optional[str] = None
    status: str
    worker_paypal_email: Optional[str] = None
    payout_batch_id: Optional[str] = None
    created_at: str
    updated_at: str


class EscrowManager:
    def __init__(self, paypal_client: PayPalClient):
        self.paypal = paypal_client
        self._ledger: Dict[str, EscrowRecord] = {}

    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    async def lock_bounty(
        self, bounty_id: str, reward_usd: float, description: str
    ) -> EscrowRecord:
        if bounty_id in self._ledger:
            raise ValueError(f"Bounty {bounty_id} already exists.")

        # MUST HAVE await HERE
        order = await self.paypal.create_authorization_order(amount=reward_usd)
        order_id = order.get("id")

        record = EscrowRecord(
            bounty_id=bounty_id,
            reward_usd=reward_usd,
            description=description,
            paypal_order_id=order_id,
            status="LOCKED",
            created_at=self._now(),
            updated_at=self._now(),
        )
        self._ledger[bounty_id] = record
        return record

    async def release_bounty(
        self, bounty_id: str, worker_paypal_email: str
    ) -> EscrowRecord:
        record = self._ledger.get(bounty_id)
        if not record:
            raise KeyError(f"Bounty {bounty_id} not found.")

        if record.status != "LOCKED":
            raise ValueError(
                f"Cannot release bounty. Current status is '{record.status}', expected 'LOCKED'."
            )

        # MUST HAVE await HERE
        payout = await self.paypal.disburse_payout(
            worker_email=worker_paypal_email,
            amount=record.reward_usd,
            note=f"Reward for completed task {bounty_id}",
        )

        batch_id = payout.get("batch_header", {}).get("payout_batch_id")

        record.status = "DISBURSED"
        record.worker_paypal_email = worker_paypal_email
        record.payout_batch_id = batch_id
        record.updated_at = self._now()
        return record

    async def void_bounty(self, bounty_id: str) -> EscrowRecord:
        record = self._ledger.get(bounty_id)
        if not record:
            raise KeyError(f"Bounty {bounty_id} not found.")

        if record.status != "LOCKED":
            raise ValueError(f"Cannot void bounty. Current status is '{record.status}'.")

        record.status = "VOIDED"
        record.updated_at = self._now()
        return record

    def get_bounty(self, bounty_id: str) -> Optional[EscrowRecord]:
        return self._ledger.get(bounty_id)