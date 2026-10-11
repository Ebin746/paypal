import asyncio
import httpx

API_BASE = "http://127.0.0.1:8000"
TEST_WORKER_EMAIL = "sb-ixtf453297237@personal.example.com"  # it is a personal account , in env business account 


async def run_isolated_test():
    async with httpx.AsyncClient() as client:
        print("\n--- 1. Locking $5.00 Escrow for Real Estate Plot Check ---")
        lock_res = await client.post(
            f"{API_BASE}/escrow/lock",
            json={
                "bounty_id": "plot-verif-101",
                "reward_usd": 5.0,
                "description": "Inspect vacant plot for unrecorded building construction",
            },
        )
        print("Lock Result:", lock_res.json())

        print("\n--- 2. Checking Ledger State ---")
        status_res = await client.get(f"{API_BASE}/escrow/plot-verif-101")
        print("Ledger State:", status_res.json())

        print("\n--- 3. Simulating Orchestrator Approval & Payout Release ---")
        release_res = await client.post(
            f"{API_BASE}/escrow/plot-verif-101/release",
            json={"worker_paypal_email": TEST_WORKER_EMAIL},
        )
        print("Release Result:", release_res.json())

        print("\n--- 4. Final Balance & Status ---")
        final_res = await client.get(f"{API_BASE}/escrow/plot-verif-101")
        print("Final State:", final_res.json())


if __name__ == "__main__":
    asyncio.run(run_isolated_test())