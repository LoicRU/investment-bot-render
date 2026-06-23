"""
Investment Bot — 100% gratuit
Groq API (Llama 3.3 70B) + yfinance + Telegram + Render
"""
import asyncio
import logging
import os
from src.scheduler import InvestmentScheduler
from src.telegram_bot import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log"),
    ],
)
logger = logging.getLogger("main")


async def main():
    logger.info("=== Investment Bot démarré (Groq + Render) ===")

    notifier = TelegramNotifier(
        token=os.environ["TELEGRAM_TOKEN"],
        chat_id=os.environ["TELEGRAM_CHAT_ID"],
    )

    scheduler = InvestmentScheduler(notifier=notifier)

    await asyncio.gather(
        scheduler.run(),
        notifier.run_polling(),
    )


if __name__ == "__main__":
    asyncio.run(main())
