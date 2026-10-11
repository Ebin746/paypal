from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from paypal_client import PayPalClient
from escrow_manager import EscrowManager

app = FastAPI(title="GroundBounty Escrow Service")

paypal_client = PayPalClient()
escrow_manager = EscrowManager(paypal_client=paypal_client)


class LockBountyRequest(BaseModel):
    bounty_id: str
    reward_usd: float
    description: str


class ReleasePayoutRequest(BaseModel):
    worker_paypal_email: str


@app.post("/escrow/lock")
async def lock_bounty(req: LockBountyRequest):
    try:
        record = await escrow_manager.lock_bounty(
            bounty_id=req.bounty_id,
            reward_usd=req.reward_usd,
            description=req.description,
        )
        return {"success": True, "record": record}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/escrow/{bounty_id}/release")
async def release_bounty(bounty_id: str, req: ReleasePayoutRequest):
    try:
        record = await escrow_manager.release_bounty(
            bounty_id=bounty_id, worker_paypal_email=req.worker_paypal_email
        )
        return {"success": True, "record": record}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/escrow/{bounty_id}/void")
async def void_bounty(bounty_id: str):
    try:
        record = await escrow_manager.void_bounty(bounty_id=bounty_id)
        return {"success": True, "record": record}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/escrow/{bounty_id}")
async def get_bounty(bounty_id: str):
    record = escrow_manager.get_bounty(bounty_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bounty not found")
    return record