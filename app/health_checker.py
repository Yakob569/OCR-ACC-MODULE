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
            logger.info(f"⏱️ [Cron] Pinging {REMOTE_GO_URL}...")
            response = await client.get(REMOTE_GO_URL, timeout=10.0)
            if response.status_code == 200:
                logger.info(f"✅ [Cron] Ping successful: {response.status_code}")
            else:
                logger.warning(f"⚠️ [Cron] Ping returned status: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ [Cron] Ping failed: {e}")

async def run_scheduler():
    cron = croniter("*/5 * * * *", datetime.now())
    logger.info("🚀 Health checker started.")
    while True:
        now = datetime.now()
        next_run = cron.get_next(datetime)
        logger.info(f"⏭️ [Cron] Next ping scheduled at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        
        sleep_time = (next_run - now).total_seconds()
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        await ping_service()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_scheduler())
