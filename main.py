"""
Investment Bot - Point d'entrée principal
Lance le scheduler et le bot Telegram simultanément
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
    logger.info("=== Investment Bot démarré ===")

    notifier = TelegramNotifier(
        token=os.environ["TELEGRAM_TOKEN"],
        chat_id=os.environ["TELEGRAM_CHAT_ID"],
    )

    scheduler = InvestmentScheduler(notifier=notifier)

    # Démarrer le scheduler en arrière-plan
    await asyncio.gather(
        scheduler.run(),
        notifier.run_polling(),
    )


if __name__ == "__main__":
    asyncio.run(main())
