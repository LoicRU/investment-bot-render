"""
Investment Bot — Mode GitHub Actions
Lance un scan unique, envoie les alertes Telegram, puis termine.
Pas de serveur permanent nécessaire.
"""
import asyncio
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


async def main():
    logger.info("=== Investment Bot démarré (GitHub Actions) ===")

    from src.screener import Screener, WATCHLIST
    from src.scorer   import AIScorer
    from src.notifier import TelegramNotifier

    threshold = int(os.environ.get("ALERT_THRESHOLD", "75"))

    notifier = TelegramNotifier(
        token=os.environ["TELEGRAM_TOKEN"],
        chat_id=os.environ["TELEGRAM_CHAT_ID"],
    )

    screener = Screener()
    scorer   = AIScorer()

    # 1. Filtre initial sans IA
    candidates = screener.scan(WATCHLIST)
    logger.info(f"{len(candidates)} candidats après filtre")

    # 2. Scoring IA (Groq, gratuit)
    results = scorer.score_batch(candidates, max_batch=30)
    logger.info(f"{len(results)} résultats ≥ 70/100")

    # 3. Alertes Telegram
    alerted = []
    for r in results:
        if r.total_score >= threshold:
            sent = await notifier.send_alert(r)
            if sent:
                alerted.append(r)
                await asyncio.sleep(1)

    # 4. Résumé final
    await notifier.send_summary(alerted, total=len(WATCHLIST))
    logger.info(f"=== Terminé : {len(alerted)} alertes envoyées ===")


if __name__ == "__main__":
    asyncio.run(main())
