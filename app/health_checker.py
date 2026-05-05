import asyncio
import logging
import httpx
import time
from croniter import croniter
from datetime import datetime

logger = logging.getLogger("health-checker")

REMOTE_GO_URL = "https://ocr-acc-user-module.onrender.com/health"

async def ping_service():
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Pinging {REMOTE_GO_URL}...")
            response = await client.get(REMOTE_GO_URL, timeout=10.0)
            logger.info(f"Ping result: {response.status_code}")
        except Exception as e:
            logger.error(f"Ping failed: {e}")

async def run_scheduler():
    cron = croniter("*/5 * * * *", datetime.now())
    while True:
        now = datetime.now()
        next_run = cron.get_next(datetime)
        sleep_time = (next_run - now).total_seconds()
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        await ping_service()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_scheduler())
