from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel
from paypal_client import PayPalClient

class EscrowRecord(BaseModel):
    bounty_id: str
    reward_usd: float
    description: str
    paypal_order_id: Optional[str] = None
    status: str  # "LOCKED" | "DISBURSED" | "VOIDED"
    worker_paypal_email: Optional[str] = None
    payout_batch_id: Optional[str] = None
    created_at: str
    updated_at: str


class EscrowManager:
    """Manages bounty escrow lifecycle and state transitions."""

    def __init__(self, paypal_client: PayPalClient):
        self.paypal = paypal_client
        # In-memory store; replace with SQLModel/SQLite session for persistence
        self._ledger: Dict[str, EscrowRecord] = {}

    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    async def lock_bounty(
        self, bounty_id: str, reward_usd: float, description: str
    ) -> EscrowRecord:
        """Pre-authorizes funds via PayPal and records the locked bounty."""
        if bounty_id in self._ledger:
            raise ValueError(f"Bounty {bounty_id} already exists.")

        # 1. Call PayPal Sandbox API to lock/authorize funds
        order = await self.paypal.create_authorization_order(amount=reward_usd)
        order_id = order.get("id")

        # 2. Store escrow record in state
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
        """Disburses instant PayPal Payout to the worker upon verification pass."""
        record = self._ledger.get(bounty_id)
        if not record:
            raise KeyError(f"Bounty {bounty_id} not found.")

        if record.status != "LOCKED":
            raise ValueError(
                f"Cannot release bounty. Current status is '{record.status}', expected 'LOCKED'."
            )

        # 1. Trigger instant micro-payout to worker email via PayPal Payouts API
        payout = await self.paypal.disburse_payout(
            worker_email=worker_paypal_email,
            amount=record.reward_usd,
            note=f"Reward for completed task {bounty_id}",
        )

        batch_id = payout.get("batch_header", {}).get("payout_batch_id")

        # 2. Update state to DISBURSED
        record.status = "DISBURSED"
        record.worker_paypal_email = worker_paypal_email
        record.payout_batch_id = batch_id
        record.updated_at = self._now()

        return record

    async def void_bounty(self, bounty_id: str, reason: str = "") -> EscrowRecord:
        """Voids the escrow hold if verification fails or task expires."""
        record = self._ledger.get(bounty_id)
        if not record:
            raise KeyError(f"Bounty {bounty_id} not found.")

        if record.status != "LOCKED":
            raise ValueError(
                f"Cannot void bounty. Current status is '{record.status}'."
            )

        record.status = "VOIDED"
        record.updated_at = self._now()
        return record

    def get_bounty(self, bounty_id: str) -> Optional[EscrowRecord]:
        """Retrieves current escrow record by ID."""
        return self._ledger.get(bounty_id)